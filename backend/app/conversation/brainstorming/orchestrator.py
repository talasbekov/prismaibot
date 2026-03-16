"""BMAD Brainstorming Orchestrator — state machine with 9 phases."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.conversation._openai import call_chat
from app.conversation.brainstorming.prompts import (
    APPROACH_PROMPTS,
    APPROACH_LABELS,
    FALLBACKS,
    SYSTEM_PROMPTS,
)

if TYPE_CHECKING:
    from app.memory import SessionSummaryPayload
    from app.models import TelegramSession

logger = logging.getLogger(__name__)

_MIN_WORDS_COLLECT = 5
_MAX_IDEAS = 50
_FACILITATION_CLUSTER_THRESHOLD = 3


@dataclass(frozen=True)
class BrainstormResult:
    messages: tuple[str, ...]
    action: str
    next_phase: str | None
    updated_data: dict
    summary_payload: "SessionSummaryPayload | None" = None
    inline_keyboard: list[list[dict]] = field(default_factory=list)


def route(session_record: "TelegramSession", user_text: str) -> BrainstormResult:
    """Dispatch to the handler for the current brainstorm_phase."""
    phase = session_record.brainstorm_phase
    data: dict = dict(session_record.brainstorm_data or {})

    handlers = {
        "collect_topic": _handle_collect_topic,
        "collect_goal": _handle_collect_goal,
        "collect_constraints": _handle_collect_constraints,
        "choose_approach": _handle_choose_approach,
        "facilitation_loop": _handle_facilitation_loop,
        "cluster_ideas": _handle_cluster_ideas,
        "prioritize": _handle_prioritize,
        "generate_action_plan": _handle_generate_action_plan,
        "finish": _handle_finish,
    }

    handler = handlers.get(phase or "")
    if handler is None:
        logger.warning("Unknown brainstorm_phase=%r, resetting", phase)
        return BrainstormResult(
            messages=(FALLBACKS["collect_topic"],),
            action="brainstorm_phase_reset",
            next_phase="collect_topic",
            updated_data=data,
        )

    return handler(user_text, data, session_record)


# ─────────────────────────────────────────────────────────────────────────────
# Phase handlers
# ─────────────────────────────────────────────────────────────────────────────


def _short_input(text: str) -> bool:
    return len(text.split()) < _MIN_WORDS_COLLECT


def _ask_openai(phase: str, user_text: str, extra_context: str = "") -> str | None:
    system = SYSTEM_PROMPTS.get(phase, "")
    user_prompt = f"{extra_context}\n\nПользователь: {user_text}".strip() if extra_context else user_text
    return call_chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=250,
        temperature=0.7,
    )


def _handle_collect_topic(user_text: str, data: dict, _sr: "TelegramSession") -> BrainstormResult:
    if _short_input(user_text):
        return BrainstormResult(
            messages=("Напиши чуть подробнее — хотя бы пару слов о том, что хочешь решить или придумать.",),
            action="brainstorm_collect_topic",
            next_phase="collect_topic",
            updated_data=data,
        )
    data["topic"] = user_text
    reply = _ask_openai("collect_goal", user_text, f"Тема: {user_text}") or FALLBACKS["collect_goal"]
    return BrainstormResult(
        messages=(reply,),
        action="brainstorm_collect_topic",
        next_phase="collect_goal",
        updated_data=data,
    )


def _handle_collect_goal(user_text: str, data: dict, _sr: "TelegramSession") -> BrainstormResult:
    if _short_input(user_text):
        return BrainstormResult(
            messages=("Расскажи чуть подробнее — какой результат ты хочешь получить?",),
            action="brainstorm_collect_goal",
            next_phase="collect_goal",
            updated_data=data,
        )
    data["goal"] = user_text
    context = f"Тема: {data.get('topic', '')}\nЦель: {user_text}"
    reply = _ask_openai("collect_constraints", user_text, context) or FALLBACKS["collect_constraints"]
    return BrainstormResult(
        messages=(reply,),
        action="brainstorm_collect_goal",
        next_phase="collect_constraints",
        updated_data=data,
    )


def _handle_collect_constraints(user_text: str, data: dict, _sr: "TelegramSession") -> BrainstormResult:
    if _short_input(user_text):
        return BrainstormResult(
            messages=("Расскажи подробнее — время, бюджет, что уже пробовал?",),
            action="brainstorm_collect_constraints",
            next_phase="collect_constraints",
            updated_data=data,
        )
    data["constraints"] = user_text
    # Return approach selection buttons
    keyboard = [[
        {"text": label, "callback_data": f"brainstorm:approach:{key}"}
        for key, label in APPROACH_LABELS.items()
    ]]
    prompt = (
        "Отлично! Теперь выбери подход, который поможет нам генерировать идеи:"
    )
    return BrainstormResult(
        messages=(prompt,),
        action="brainstorm_collect_constraints",
        next_phase="choose_approach",
        updated_data=data,
        inline_keyboard=keyboard,
    )


def _handle_choose_approach(user_text: str, data: dict, _sr: "TelegramSession") -> BrainstormResult:
    # Text message while waiting for approach button — repeat the buttons
    keyboard = [[
        {"text": label, "callback_data": f"brainstorm:approach:{key}"}
        for key, label in APPROACH_LABELS.items()
    ]]
    return BrainstormResult(
        messages=("Пожалуйста, выбери подход, нажав на одну из кнопок выше.",),
        action="brainstorm_choose_approach",
        next_phase="choose_approach",
        updated_data=data,
        inline_keyboard=keyboard,
    )


def _handle_facilitation_loop(user_text: str, data: dict, _sr: "TelegramSession") -> BrainstormResult:
    ideas: list[str] = list(data.get("ideas", []))
    ideas.append(user_text)
    if len(ideas) > _MAX_IDEAS:
        ideas = ideas[-_MAX_IDEAS:]  # keep the most recent
    data["ideas"] = ideas

    turns: int = int(data.get("facilitation_turns", 0)) + 1
    data["facilitation_turns"] = turns

    approach = data.get("approach", "ideas")
    system = APPROACH_PROMPTS.get(approach, SYSTEM_PROMPTS["facilitation_loop"])
    context = f"Тема: {data.get('topic', '')}\nУже назвал: {len(ideas)} идей"
    reply = call_chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": f"{context}\n\nПоследняя идея: {user_text}"},
        ],
        max_tokens=200,
    ) or FALLBACKS["facilitation_loop"]

    inline_keyboard: list[list[dict]] = []
    if turns >= _FACILITATION_CLUSTER_THRESHOLD:
        inline_keyboard = [[
            {"text": "Перейти к группировке идей", "callback_data": "brainstorm:phase:cluster_ideas"}
        ]]

    return BrainstormResult(
        messages=(reply,),
        action="brainstorm_facilitation_loop",
        next_phase="facilitation_loop",
        updated_data=data,
        inline_keyboard=inline_keyboard,
    )


def _handle_cluster_ideas(user_text: str, data: dict, _sr: "TelegramSession") -> BrainstormResult:
    ideas_text = "\n".join(f"- {idea}" for idea in data.get("ideas", []))
    context = f"Тема: {data.get('topic', '')}\nВсе идеи:\n{ideas_text}"
    reply = _ask_openai("cluster_ideas", user_text, context) or FALLBACKS["prioritize"]
    return BrainstormResult(
        messages=(reply,),
        action="brainstorm_cluster_ideas",
        next_phase="prioritize",
        updated_data=data,
    )


def _handle_prioritize(user_text: str, data: dict, _sr: "TelegramSession") -> BrainstormResult:
    ideas_text = "\n".join(f"- {idea}" for idea in data.get("ideas", []))
    context = f"Тема: {data.get('topic', '')}\nВсе идеи:\n{ideas_text}"
    reply = _ask_openai("prioritize", user_text, context) or FALLBACKS["generate_action_plan"]
    # Store raw OpenAI text — don't parse
    data["top3_text"] = reply
    return BrainstormResult(
        messages=(reply,),
        action="brainstorm_prioritize",
        next_phase="generate_action_plan",
        updated_data=data,
    )


def _handle_generate_action_plan(user_text: str, data: dict, _sr: "TelegramSession") -> BrainstormResult:
    context = (
        f"Тема: {data.get('topic', '')}\n"
        f"Топ-3 идеи: {data.get('top3_text', '')}\n"
        f"Ограничения: {data.get('constraints', '')}"
    )
    reply = _ask_openai("generate_action_plan", user_text, context) or FALLBACKS["finish"]
    data["action_plan"] = reply
    return BrainstormResult(
        messages=(reply,),
        action="brainstorm_generate_action_plan",
        next_phase="finish",
        updated_data=data,
    )


def _handle_finish(user_text: str, data: dict, session_record: "TelegramSession") -> BrainstormResult:
    ideas = data.get("ideas", [])
    top3 = data.get("top3_text", "")
    plan = data.get("action_plan", "")

    ideas_msg = "Идеи из нашей сессии:\n" + "\n".join(f"• {idea}" for idea in ideas)
    top3_msg = f"Топ-3 идеи:\n{top3}" if top3 else "Топ-3 идеи не определены."
    plan_msg = f"План на 7 дней:\n{plan}" if plan else "Начни с малого: один шаг сегодня."

    summary_payload = _build_summary_payload(data, session_record)

    return BrainstormResult(
        messages=(ideas_msg, top3_msg, plan_msg),
        action="brainstorm_finish",
        next_phase="done",
        updated_data=data,
        summary_payload=summary_payload,
    )


def _build_summary_payload(data: dict, session_record: "TelegramSession"):
    try:
        from app.memory import SessionSummaryPayload
        from app.memory import derive_allowed_profile_facts

        top3 = data.get("top3_text", "")
        plan = data.get("action_plan", "")
        topic = data.get("topic", "")
        approach = data.get("approach", "")

        return SessionSummaryPayload(
            session_id=session_record.id,
            telegram_user_id=session_record.telegram_user_id,
            reflective_mode=session_record.reflective_mode,
            source_turn_count=session_record.turn_count + 1,
            prior_context=session_record.working_context,
            latest_user_message=topic,
            takeaway=top3 or topic,
            next_steps=[plan] if plan else [],
            allowed_profile_facts=derive_allowed_profile_facts(
                prior_context=session_record.working_context,
                latest_user_message=topic,
                takeaway=top3 or topic,
            ),
        )
    except Exception:
        logger.exception("Failed to build brainstorm summary payload")
        return None
