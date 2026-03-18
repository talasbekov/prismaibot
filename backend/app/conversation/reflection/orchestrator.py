"""BMAD Reflection Orchestrator — state machine for the core conversation loop.

Phases (core loop from PRD):
    reflect_listen → reflect_clarify → reflect_analyze → reflect_versions
    → reflect_next_step → reflect_finish → done
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.conversation._openai import async_call_chat
from app.conversation._text_utils import normalize_spaces
from app.conversation.clarification import (
    _is_boundary_request,
    _is_memory_correction,
    _extract_signals,
)
from app.conversation.reflection.prompts import FALLBACKS, SYSTEM_PROMPTS

if TYPE_CHECKING:
    from app.conversation.closure import ClosureResponse
    from app.memory import SessionSummaryPayload
    from app.models import TelegramSession

logger = logging.getLogger(__name__)

# How many clarify turns before forcing analysis
_MAX_CLARIFY_TURNS = 2


@dataclass(frozen=True)
class ReflectionResult:
    messages: tuple[str, ...]
    action: str
    next_phase: str | None
    updated_data: dict
    summary_payload: "SessionSummaryPayload | None" = None
    inline_keyboard: list[list[dict]] = field(default_factory=list)


async def route(session_record: "TelegramSession", user_text: str) -> ReflectionResult:
    """Dispatch to the handler for the current reflect phase.

    Phases: open → reflect_listen → reflect_clarify → reflect_analyze
            → reflect_versions → reflect_next_step → reflect_finish → done
            close → done
    """
    phase = session_record.brainstorm_phase or "reflect_listen"
    data: dict = dict(session_record.brainstorm_data or {})

    handlers = {
        "open": _handle_open,
        "reflect_listen": _handle_listen,
        "reflect_clarify": _handle_clarify,
        "reflect_analyze": _handle_analyze,
        "reflect_versions": _handle_versions,
        "reflect_next_step": _handle_next_step,
        "reflect_finish": _handle_finish,
        "close": _handle_close,
    }

    handler = handlers.get(phase)
    if handler is None:
        logger.warning("Unknown reflect phase=%r, resetting to reflect_listen", phase)
        return ReflectionResult(
            messages=(FALLBACKS["reflect_listen"],),
            action="reflect_phase_reset",
            next_phase="reflect_listen",
            updated_data=data,
        )

    return await handler(user_text, data, session_record)


# ─────────────────────────────────────────────────────────────────────────────
# Phase handlers
# ─────────────────────────────────────────────────────────────────────────────


async def _ask_openai(phase: str, user_text: str, extra_context: str = "") -> str | None:
    system = SYSTEM_PROMPTS.get(phase, "")
    user_prompt = (
        f"{extra_context}\n\nПользователь: {user_text}".strip()
        if extra_context
        else user_text
    )
    return await async_call_chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=600,
        temperature=0.7,
    )


def _build_context(data: dict, user_text: str) -> str:
    parts = []
    if data.get("topic"):
        parts.append(f"Тема: {data['topic']}")
    if data.get("prior_context"):
        parts.append(f"Контекст: {data['prior_context']}")
    if parts:
        return "\n".join(parts) + f"\n\nПользователь сейчас: {user_text}"
    return user_text


async def _handle_open(
    user_text: str, data: dict, session_record: "TelegramSession"
) -> ReflectionResult:
    from app.conversation.first_response import compose_first_trust_response_with_memory

    prior_memory_context = data.get("prior_memory_context") or None
    result = compose_first_trust_response_with_memory(
        user_text,
        prior_memory_context=prior_memory_context,
    )
    return ReflectionResult(
        messages=result.messages,
        action=result.action,
        next_phase="reflect_listen",
        updated_data=data,
    )


def _build_closure_summary_payload(
    closure: "ClosureResponse", user_text: str, session_record: "TelegramSession"
) -> "SessionSummaryPayload | None":
    try:
        from app.memory import SessionSummaryPayload, derive_allowed_profile_facts

        return SessionSummaryPayload(
            session_id=session_record.id,
            telegram_user_id=session_record.telegram_user_id,
            reflective_mode=session_record.reflective_mode,
            source_turn_count=session_record.turn_count + 1,
            prior_context=session_record.working_context,
            latest_user_message=user_text,
            takeaway=closure.takeaway,
            next_steps=list(closure.next_steps),
            allowed_profile_facts=derive_allowed_profile_facts(
                prior_context=session_record.working_context,
                latest_user_message=user_text,
                takeaway=closure.takeaway,
            ),
        )
    except Exception:
        logger.exception("Failed to build closure summary payload")
        return None


async def _handle_close(
    user_text: str, data: dict, session_record: "TelegramSession"
) -> ReflectionResult:
    from app.conversation.closure import compose_session_closure

    closure = compose_session_closure(
        latest_user_message=user_text,
        prior_context=session_record.working_context,
        reflective_mode=session_record.reflective_mode,
    )
    data["takeaway"] = closure.takeaway
    summary_payload = _build_closure_summary_payload(closure, user_text, session_record)
    return ReflectionResult(
        messages=closure.messages,
        action=closure.action,
        next_phase="done",
        updated_data=data,
        summary_payload=summary_payload,
    )


async def _handle_listen(
    user_text: str, data: dict, session_record: "TelegramSession"
) -> ReflectionResult:
    normalized = normalize_spaces(user_text)
    lowered = normalized.lower()

    if _is_boundary_request(lowered):
        return ReflectionResult(
            messages=(
                "💬 Я здесь для того, чтобы помочь разобраться в ситуации, а не как общий помощник.",
                "🤔 Если хочешь, можем вернуться к тому, что сейчас самое напряжённое.",
            ),
            action="reflect_boundary",
            next_phase="reflect_listen",
            updated_data=data,
        )

    data["topic"] = normalized[:1500]
    # Carry over session context for continuity
    if session_record.working_context:
        data["prior_context"] = session_record.working_context[:1500]

    context = _build_context(data, normalized)
    reply = await _ask_openai("reflect_listen", normalized, context) or FALLBACKS["reflect_listen"]

    return ReflectionResult(
        messages=(reply,),
        action="reflect_listen",
        next_phase="reflect_clarify",
        updated_data=data,
    )


async def _handle_clarify(
    user_text: str, data: dict, session_record: "TelegramSession"
) -> ReflectionResult:
    normalized = normalize_spaces(user_text)

    # Accumulate clarification turns
    turns: int = int(data.get("clarify_turns", 0)) + 1
    data["clarify_turns"] = turns

    # Append to running context
    prior = data.get("topic", "")
    data["topic"] = (f"{prior} {normalized}").strip()[:2000]

    # Check for memory correction
    if _is_memory_correction(
        latest_text=normalized.lower(),
        prior_context=session_record.working_context,
    ):
        data["clarify_turns"] = _MAX_CLARIFY_TURNS  # force move to analyze
        return ReflectionResult(
            messages=(
                "💬 Понял, беру только то, что ты описываешь сейчас.",
                "🤔 Что в этой ситуации задевает тебя сильнее всего?",
            ),
            action="reflect_clarify",
            next_phase="reflect_analyze",
            updated_data=data,
        )

    context = _build_context(data, normalized)

    # After enough turns — move to analysis
    if turns >= _MAX_CLARIFY_TURNS:
        reply = (
            await _ask_openai("reflect_analyze", normalized, context)
            or FALLBACKS["reflect_analyze"]
        )
        return ReflectionResult(
            messages=(reply,),
            action="reflect_clarify_to_analyze",
            next_phase="reflect_analyze",
            updated_data=data,
        )

    reply = await _ask_openai("reflect_clarify", normalized, context) or FALLBACKS["reflect_clarify"]
    return ReflectionResult(
        messages=(reply,),
        action="reflect_clarify",
        next_phase="reflect_clarify",
        updated_data=data,
    )


async def _handle_analyze(
    user_text: str, data: dict, _sr: "TelegramSession"
) -> ReflectionResult:
    normalized = normalize_spaces(user_text)
    data["topic"] = (f"{data.get('topic', '')} {normalized}").strip()[:2000]

    context = _build_context(data, normalized)

    # Try to enrich with signal detection
    signals = _extract_signals(context.lower())
    signal_hint = ""
    if signals.fact_confident or signals.emotion_confident:
        parts = []
        if signals.fact_confident:
            parts.append(f"факт: {signals.fact}")
        if signals.emotion_confident:
            parts.append(f"эмоция: {signals.emotion}")
        if signals.interpretation_confident:
            parts.append(f"интерпретация: {signals.interpretation}")
        signal_hint = "Опорные сигналы из текста: " + "; ".join(parts)

    full_context = f"{context}\n\n{signal_hint}".strip() if signal_hint else context
    reply = (
        await _ask_openai("reflect_analyze", normalized, full_context)
        or FALLBACKS["reflect_analyze"]
    )

    data["analysis"] = reply
    return ReflectionResult(
        messages=(reply,),
        action="reflect_analyze",
        next_phase="reflect_versions",
        updated_data=data,
    )


async def _handle_versions(
    user_text: str, data: dict, _sr: "TelegramSession"
) -> ReflectionResult:
    normalized = normalize_spaces(user_text)
    context = (
        f"Тема: {data.get('topic', '')}\n"
        f"Разбор: {data.get('analysis', '')}\n"
        f"Пользователь: {normalized}"
    )
    reply = (
        await _ask_openai("reflect_versions", normalized, context)
        or FALLBACKS["reflect_versions"]
    )
    data["versions"] = reply
    return ReflectionResult(
        messages=(reply,),
        action="reflect_versions",
        next_phase="reflect_next_step",
        updated_data=data,
    )


async def _handle_next_step(
    user_text: str, data: dict, _sr: "TelegramSession"
) -> ReflectionResult:
    normalized = normalize_spaces(user_text)
    context = (
        f"Тема: {data.get('topic', '')}\n"
        f"Разбор: {data.get('analysis', '')}\n"
        f"Версии: {data.get('versions', '')}\n"
        f"Пользователь: {normalized}"
    )
    reply = (
        await _ask_openai("reflect_next_step", normalized, context)
        or FALLBACKS["reflect_next_step"]
    )
    data["next_step"] = reply
    return ReflectionResult(
        messages=(reply,),
        action="reflect_next_step",
        next_phase="reflect_finish",
        updated_data=data,
    )


async def _handle_finish(
    user_text: str, data: dict, session_record: "TelegramSession"
) -> ReflectionResult:
    normalized = normalize_spaces(user_text)
    context = (
        f"Тема: {data.get('topic', '')}\n"
        f"Разбор: {data.get('analysis', '')}\n"
        f"Версии: {data.get('versions', '')}\n"
        f"Следующий шаг: {data.get('next_step', '')}\n"
        f"Финальное сообщение: {normalized}"
    )
    reply = (
        await _ask_openai("reflect_finish", normalized, context)
        or FALLBACKS["reflect_finish"]
    )

    summary_payload = _build_summary_payload(data, session_record)
    return ReflectionResult(
        messages=(reply,),
        action="reflect_finish",
        next_phase="done",
        updated_data=data,
        summary_payload=summary_payload,
    )


def _build_summary_payload(
    data: dict, session_record: "TelegramSession"
) -> "SessionSummaryPayload | None":
    try:
        from app.memory import SessionSummaryPayload, derive_allowed_profile_facts

        topic = data.get("topic", "")
        analysis = data.get("analysis", "")
        next_step = data.get("next_step", "")

        return SessionSummaryPayload(
            session_id=session_record.id,
            telegram_user_id=session_record.telegram_user_id,
            reflective_mode=session_record.reflective_mode,
            source_turn_count=session_record.turn_count + 1,
            prior_context=session_record.working_context,
            latest_user_message=topic,
            takeaway=analysis or topic,
            next_steps=[next_step] if next_step else [],
            allowed_profile_facts=derive_allowed_profile_facts(
                prior_context=session_record.working_context,
                latest_user_message=topic,
                takeaway=analysis or topic,
            ),
        )
    except Exception:
        logger.exception("Failed to build reflection summary payload")
        return None
