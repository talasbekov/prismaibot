from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, cast

from fastapi import BackgroundTasks
from sqlalchemy import desc
from sqlmodel import Session, select

from app.conversation._text_utils import normalize_spaces
from app.core.db import engine
from app.memory.schemas import (
    ContinuityOverview,
    ProfileFactInput,
    ProfileFactRecord,
    SessionRecallContext,
    SessionSummaryDraft,
    SessionSummaryPayload,
    SessionSummaryRecord,
)
from app.models import ProfileFact, SessionSummary, TelegramSession
from app.ops.signals import record_summary_failure_signal, resolve_summary_signal

logger = logging.getLogger(__name__)

# Keep in sync with app.conversation.clarification.LOW_CONFIDENCE_MARKERS
_LOW_CONFIDENCE_MARKERS = (
    "не знаю",
    "не увер",
    "не до конца",
    "не понимаю",
    "как будто",
    "наверное",
    "все сложно",
    "запут",
    "как-то",
    "что-то",
)
_EMOTION_MARKERS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("обид",), "В сессии заметно чувство обиды и уязвимости."),
    (("трев", "страш"), "На фоне ситуации звучит тревога за то, что будет дальше."),
    (("злю", "злит", "раздраж"), "Внутри ситуации накопилось раздражение или злость."),
    (("устал", "выгор", "сил нет"), "Ситуация ощущается изматывающей и забирающей силы."),
)
_FACT_MARKERS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("поссор", "конфликт", "напряж"), "В центре сессии был напряженный разговор или конфликтный эпизод."),
    (
        ("перебил", "не слыш", "игнор", "обесцен"),
        "Существенным фактом стал опыт перебивания, игнорирования или обесценивания.",
    ),
    (("снова", "опять", "повтор"), "Ситуация воспринимается не как единичный случай, а как повторяющийся паттерн."),
    (
        ("работ", "началь", "коллег", "проект", "команд", "деньг", "технолог"),
        "Рабочий или проектный контекст оказался частью личного напряжения, а не отдельной технической темой.",
    ),
)
_HIGH_RISK_MARKERS = (
    "суиц",
    "самоуб",
    "не хочу жить",
    "исчезнуть",
    "селфхарм",
    "самоповреж",
    "насили",
    "избил",
    "бьет",
    "абьюз",
    "изнасил",
)
_DURABLE_FACT_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}
_ALLOWED_PROFILE_RETENTION_SCOPES = frozenset(
    {"candidate", "durable_profile", "restricted_profile"}
)
_ALLOWED_PROFILE_FACT_KEYS = frozenset(
    {
        "communication_preference",
        "recurring_trigger",
        "relationship_context",
        "support_preference",
        "work_context",
    }
)


def schedule_session_summary_generation(
    background_tasks: BackgroundTasks,
    payload: SessionSummaryPayload,
) -> None:
    background_tasks.add_task(generate_and_persist_session_summary, payload)


def generate_and_persist_session_summary(payload: SessionSummaryPayload) -> None:
    draft: SessionSummaryDraft | None = None
    try:
        draft = build_session_summary(payload)
        persist_session_summary(payload, draft)
    except Exception as exc:
        logger.exception(
            "Failed to generate/persist session summary for session_id=%s",
            payload.session_id,
        )
        _record_failure(payload, exc, draft=draft)


def derive_allowed_profile_facts(
    *,
    prior_context: str | None,
    latest_user_message: str,
    takeaway: str,
) -> list[ProfileFactInput]:
    combined_context = normalize_spaces(
        " ".join(part for part in (prior_context, latest_user_message, takeaway) if part)
    ).lower()
    facts: list[ProfileFactInput] = []

    if any(marker in combined_context for marker in ("муж", "партнер", "отнош", "роман")):
        facts.append(
            ProfileFactInput(
                fact_key="relationship_context",
                fact_value="Повторяющееся напряжение связано с близкими отношениями пользователя.",
                confidence="high",
            )
        )
    if any(marker in combined_context for marker in ("работ", "началь", "коллег", "проект", "команд")):
        facts.append(
            ProfileFactInput(
                fact_key="work_context",
                fact_value="Заметная часть напряжения пользователя связана с рабочим контекстом.",
                confidence="high",
            )
        )
    if any(marker in combined_context for marker in ("снова", "опять", "повтор")):
        facts.append(
            ProfileFactInput(
                fact_key="recurring_trigger",
                fact_value="Пользователь описывает ситуацию как повторяющийся паттерн, а не единичный эпизод.",
                confidence=(
                    "low"
                    if any(marker in combined_context for marker in _LOW_CONFIDENCE_MARKERS)
                    else "medium"
                ),
            )
        )
    if any(marker in combined_context for marker in ("не слыш", "перебил", "перебива", "дослуш")):
        facts.append(
            ProfileFactInput(
                fact_key="communication_preference",
                fact_value="Пользователю особенно важно, чтобы в сложных разговорах его дослушивали и не перебивали.",
                confidence="high",
            )
        )
    if any(marker in combined_context for marker in ("спокой", "береж", "мягк", "уваж")):
        facts.append(
            ProfileFactInput(
                fact_key="support_preference",
                fact_value="Пользователю полезнее спокойный и уважительный тон обсуждения напряженных тем.",
                confidence="high",
            )
        )
    return _sanitize_profile_facts(facts)


def build_session_summary(payload: SessionSummaryPayload) -> SessionSummaryDraft:
    combined_context = normalize_spaces(
        " ".join(
            part
            for part in (payload.prior_context, payload.latest_user_message)
            if part
        )
    )
    lowered = combined_context.lower()
    if _is_high_risk_context(lowered):
        return SessionSummaryDraft(
            takeaway=(
                "Сессия касалась очень чувствительной и потенциально небезопасной ситуации, "
                "поэтому долговременная память сохраняет только общий контекст без подробностей."
            ),
            key_facts=[
                "Сессия касалась очень чувствительной ситуации, поэтому долговременная память хранит только общий безопасный контекст."
            ],
            emotional_tensions=[
                "В сессии звучало сильное эмоциональное напряжение, требующее особенно осторожного обращения с памятью."
            ],
            uncertainty_notes=[
                "Высокорисковый контекст не должен автоматически становиться обычной долговременной памятью."
            ],
            next_step_context=[],
            profile_facts=_sanitize_profile_facts(payload.allowed_profile_facts),
        )

    key_facts = _pick_lines(_FACT_MARKERS, lowered)
    if not key_facts:
        key_facts = [
            "В сессии разбиралась напряженная жизненная ситуация, для которой пользователю нужна большая ясность."
        ]

    emotional_tensions = _pick_lines(_EMOTION_MARKERS, lowered)
    if not emotional_tensions:
        emotional_tensions = [
            "В сессии слышно эмоциональное напряжение, которое пока не удалось полностью разложить по полочкам."
        ]

    uncertainty_notes: list[str] = []
    if any(marker in lowered for marker in _LOW_CONFIDENCE_MARKERS):
        uncertainty_notes.append(
            "Часть выводов в этой сессии носит условный характер и не должна закрепляться как устойчивый факт без следующей проверки."
        )

    takeaway = payload.takeaway[:1000]
    if uncertainty_notes and any(marker in lowered for marker in ("снова", "опять", "повтор", "паттерн")):
        key_facts = [
            fact
            for fact in key_facts
            if "повторя" not in fact.lower()
        ]

    return SessionSummaryDraft(
        takeaway=takeaway,
        key_facts=key_facts[:3],
        emotional_tensions=emotional_tensions[:3],
        uncertainty_notes=uncertainty_notes[:2],
        next_step_context=_sanitize_next_steps(payload.next_steps),
        profile_facts=_sanitize_profile_facts(payload.allowed_profile_facts),
    )


def persist_session_summary(
    payload: SessionSummaryPayload,
    draft: SessionSummaryDraft,
) -> None:
    try:
        promoted_profile_facts = _promote_profile_facts(
            payload=payload,
            draft=draft,
            profile_facts=draft.profile_facts,
        )
    except Exception:
        logger.exception(
            "Failed to evaluate memory promotion rules for session_id=%s; defaulting to conservative persistence",
            payload.session_id,
        )
        promoted_profile_facts = []

    with Session(engine) as session:
        existing = session.exec(
            select(SessionSummary).where(SessionSummary.session_id == payload.session_id)
        ).first()
        now = datetime.now(timezone.utc)
        if existing is None:
            summary = SessionSummary(
                session_id=payload.session_id,
                telegram_user_id=payload.telegram_user_id,
                reflective_mode=payload.reflective_mode,
                source_turn_count=payload.source_turn_count,
                takeaway=draft.takeaway,
                key_facts=draft.key_facts,
                emotional_tensions=draft.emotional_tensions,
                uncertainty_notes=draft.uncertainty_notes,
                next_step_context=draft.next_step_context,
                created_at=now,
                updated_at=now,
                retention_scope="durable_summary",
                deletion_eligible=True,
            )
        else:
            summary = existing
            summary.reflective_mode = payload.reflective_mode
            summary.source_turn_count = payload.source_turn_count
            summary.takeaway = draft.takeaway
            summary.key_facts = draft.key_facts
            summary.emotional_tensions = draft.emotional_tensions
            summary.uncertainty_notes = draft.uncertainty_notes
            summary.next_step_context = draft.next_step_context
            summary.updated_at = now
            summary.retention_scope = "durable_summary"
            summary.deletion_eligible = True

        session.add(summary)
        _upsert_profile_facts(
            session,
            telegram_user_id=payload.telegram_user_id,
            source_session_id=payload.session_id,
            profile_facts=promoted_profile_facts,
            now=now,
        )
        _purge_session_transcript(session, session_id=payload.session_id, now=now)
        resolve_summary_signal(session, session_id=payload.session_id)
        _commit_memory_transaction(session)


def get_continuity_overview(
    session: Session,
    *,
    telegram_user_id: int,
) -> ContinuityOverview:
    summaries = session.exec(
        select(SessionSummary)
        .where(SessionSummary.telegram_user_id == telegram_user_id)
        .order_by(desc(cast(Any, SessionSummary.updated_at)))
    ).all()
    stored_profile_facts = session.exec(
        select(ProfileFact)
        .where(ProfileFact.telegram_user_id == telegram_user_id)
        .order_by(ProfileFact.fact_key)
    ).all()
    profile_facts = [
        fact
        for fact in stored_profile_facts
        if fact.deleted_at is None
        and fact.superseded_at is None
        and fact.retention_scope == "durable_profile"
    ]
    return ContinuityOverview(
        telegram_user_id=telegram_user_id,
        summaries=[
            SessionSummaryRecord(
                session_id=summary.session_id,
                takeaway=summary.takeaway,
                reflective_mode=summary.reflective_mode,
                source_turn_count=summary.source_turn_count,
                retention_scope=summary.retention_scope,
                deletion_eligible=summary.deletion_eligible,
            )
            for summary in summaries
        ],
        profile_facts=[
            ProfileFactRecord(
                fact_key=fact.fact_key,
                fact_value=fact.fact_value,
                confidence=fact.confidence,
                retention_scope=fact.retention_scope,
                deletion_eligible=fact.deletion_eligible,
                source_session_id=fact.source_session_id,
            )
            for fact in profile_facts
        ],
    )


def get_session_recall_context(
    session: Session,
    *,
    telegram_user_id: int,
) -> SessionRecallContext | None:
    summaries = session.exec(
        select(SessionSummary)
        .where(SessionSummary.telegram_user_id == telegram_user_id)
        .order_by(
            desc(cast(Any, SessionSummary.updated_at)),
            desc(cast(Any, SessionSummary.created_at)),
        )
    ).all()
    if not summaries:
        return None

    recent_summaries = summaries[:2]
    stored_profile_facts = session.exec(
        select(ProfileFact)
        .where(ProfileFact.telegram_user_id == telegram_user_id)
        .where(ProfileFact.deleted_at == None)  # noqa: E711
        .where(ProfileFact.superseded_at == None)  # noqa: E711
        .where(ProfileFact.retention_scope == "durable_profile")
        .order_by(
            desc(cast(Any, ProfileFact.updated_at)),
            desc(cast(Any, ProfileFact.created_at)),
        )
        .limit(3)
    ).all()
    recall_facts = [
        ProfileFactRecord(
            fact_key=fact.fact_key,
            fact_value=fact.fact_value,
            confidence=fact.confidence,
            retention_scope=fact.retention_scope,
            deletion_eligible=fact.deletion_eligible,
            source_session_id=fact.source_session_id,
        )
        for fact in stored_profile_facts
    ]
    continuity_lines: list[str] = [_summary_takeaway_for_recall(recent_summaries[0])]
    continuity_lines.extend(
        key_fact for summary in recent_summaries for key_fact in summary.key_facts[:1]
    )
    continuity_lines.extend(fact.fact_value for fact in recall_facts)
    continuity_context = normalize_spaces(" ".join(continuity_lines))[:600]
    if not continuity_context:
        return None

    return SessionRecallContext(
        telegram_user_id=telegram_user_id,
        last_session_takeaway=recent_summaries[0].takeaway,
        continuity_context=continuity_context,
        profile_facts=recall_facts,
    )


def _pick_lines(
    rules: tuple[tuple[tuple[str, ...], str], ...],
    lowered_text: str,
) -> list[str]:
    lines: list[str] = []
    for markers, line in rules:
        if any(marker in lowered_text for marker in markers):
            lines.append(line)
    return lines


def _sanitize_next_steps(steps: list[str]) -> list[str]:
    sanitized: list[str] = []
    for step in steps:
        cleaned = normalize_spaces(step)
        if ". " in cleaned[:4]:
            cleaned = cleaned.split(". ", 1)[1]
        if cleaned:
            sanitized.append(cleaned[:300])
    return sanitized[:3]


def _sanitize_profile_facts(facts: list[ProfileFactInput]) -> list[ProfileFactInput]:
    sanitized: list[ProfileFactInput] = []
    seen_keys: set[str] = set()
    for fact in facts:
        fact_key = normalize_spaces(fact.fact_key).lower().replace(" ", "_")[:64]
        fact_value = normalize_spaces(fact.fact_value)[:500]
        confidence = normalize_spaces(fact.confidence).lower()[:16] or "medium"
        retention_scope = normalize_spaces(fact.retention_scope).lower()[:32] or "candidate"
        if (
            not fact_key
            or fact_key not in _ALLOWED_PROFILE_FACT_KEYS
            or fact_key in seen_keys
            or not fact_value
            or retention_scope not in _ALLOWED_PROFILE_RETENTION_SCOPES
        ):
            continue
        sanitized.append(
            ProfileFactInput(
                fact_key=fact_key,
                fact_value=fact_value,
                confidence=confidence,
                retention_scope=retention_scope,
            )
        )
        seen_keys.add(fact_key)
    return sanitized


def _promote_profile_facts(
    *,
    payload: SessionSummaryPayload,
    draft: SessionSummaryDraft,
    profile_facts: list[ProfileFactInput],
) -> list[ProfileFactInput]:
    combined_context = normalize_spaces(
        " ".join(
            part
            for part in (
                payload.prior_context,
                payload.latest_user_message,
                payload.takeaway,
                " ".join(fact.fact_value for fact in profile_facts),
            )
            if part
        )
    ).lower()
    has_high_risk = _is_high_risk_context(combined_context)
    has_uncertainty = bool(draft.uncertainty_notes)

    promoted: list[ProfileFactInput] = []
    for fact in profile_facts:
        retention_scope = "durable_profile"
        confidence_rank = _DURABLE_FACT_CONFIDENCE_ORDER.get(fact.confidence, 0)
        if (
            has_high_risk
            or _is_high_risk_context(fact.fact_value.lower())
            or confidence_rank < _DURABLE_FACT_CONFIDENCE_ORDER["medium"]
            or (has_uncertainty and confidence_rank < _DURABLE_FACT_CONFIDENCE_ORDER["high"])
        ):
            retention_scope = "restricted_profile"
        promoted.append(
            ProfileFactInput(
                fact_key=fact.fact_key,
                fact_value=fact.fact_value,
                confidence=fact.confidence,
                retention_scope=retention_scope,
            )
        )
    return promoted


def _upsert_profile_facts(
    session: Session,
    *,
    telegram_user_id: int,
    source_session_id: uuid.UUID,
    profile_facts: list[ProfileFactInput],
    now: datetime,
) -> None:
    for fact in profile_facts:
        existing = session.exec(
            select(ProfileFact)
            .where(ProfileFact.telegram_user_id == telegram_user_id)
            .where(ProfileFact.fact_key == fact.fact_key)
        ).first()
        if existing is None:
            existing = ProfileFact(
                telegram_user_id=telegram_user_id,
                source_session_id=source_session_id,
                fact_key=fact.fact_key,
                fact_value=fact.fact_value,
                confidence=fact.confidence,
                retention_scope=fact.retention_scope,
                deletion_eligible=True,
                created_at=now,
                updated_at=now,
            )
        else:
            existing.source_session_id = source_session_id
            existing.fact_value = fact.fact_value
            existing.confidence = fact.confidence
            # Never upgrade a restricted_profile fact to durable_profile in a later session.
            # Once a fact is classified as restricted it must remain restricted regardless of
            # what the newer session's promotion policy would assign.
            if existing.retention_scope != "restricted_profile":
                existing.retention_scope = fact.retention_scope
                existing.superseded_at = None
            existing.deletion_eligible = True
            existing.deleted_at = None
            existing.updated_at = now
        session.add(existing)


def _purge_session_transcript(
    session: Session,
    *,
    session_id: uuid.UUID,
    now: datetime,
) -> None:
    session_record = session.exec(
        select(TelegramSession).where(TelegramSession.id == session_id)
    ).first()
    if session_record is None:
        return
    session_record.working_context = None
    session_record.last_user_message = None
    session_record.last_bot_prompt = None
    session_record.transcript_purged_at = now
    session_record.updated_at = now
    session.add(session_record)


def _serialize_retry_payload(
    payload: SessionSummaryPayload,
    draft: SessionSummaryDraft | None,
) -> dict[str, Any]:
    safe_draft = draft or _build_fallback_summary_draft(payload)
    serialized: dict[str, Any] = {
        "session_id": str(payload.session_id),
        "telegram_user_id": payload.telegram_user_id,
        "reflective_mode": payload.reflective_mode,
        "source_turn_count": payload.source_turn_count,
    }
    serialized["summary_draft"] = safe_draft.model_dump(mode="json")
    return serialized


def _record_failure(
    payload: SessionSummaryPayload,
    exc: Exception,
    *,
    draft: SessionSummaryDraft | None,
) -> None:
    try:
        with Session(engine) as session:
            now = datetime.now(timezone.utc)
            record_summary_failure_signal(
                session,
                session_id=payload.session_id,
                telegram_user_id=payload.telegram_user_id,
                error_type=type(exc).__name__,
                error_message=str(exc),
                retry_payload=_serialize_retry_payload(payload, draft),
            )
            _purge_session_transcript(session, session_id=payload.session_id, now=now)
            _commit_signal_transaction(session)
    except Exception:
        logger.exception(
            "Failed to record summary failure signal for session_id=%s",
            payload.session_id,
        )


def record_memory_failure(
    payload: SessionSummaryPayload,
    *,
    error_type: str,
    error_message: str,
    failure_stage: str = "persistence",
) -> None:
    try:
        with Session(engine) as session:
            now = datetime.now(timezone.utc)
            record_summary_failure_signal(
                session,
                session_id=payload.session_id,
                telegram_user_id=payload.telegram_user_id,
                error_type=error_type,
                error_message=error_message,
                retry_payload=_serialize_retry_payload(payload, None),
                failure_stage=failure_stage,
            )
            _purge_session_transcript(session, session_id=payload.session_id, now=now)
            _commit_signal_transaction(session)
    except Exception:
        logger.exception(
            "Failed to record explicit memory failure for session_id=%s",
            payload.session_id,
        )


def _commit_memory_transaction(session: Session) -> None:
    session.commit()


def _commit_signal_transaction(session: Session) -> None:
    session.commit()


def _build_fallback_summary_draft(payload: SessionSummaryPayload) -> SessionSummaryDraft:
    return SessionSummaryDraft(
        takeaway=payload.takeaway[:1000],
        key_facts=[],
        emotional_tensions=[],
        uncertainty_notes=[
            "Summary generation did not complete fully; retry should reuse this bounded continuity draft instead of raw transcript retention."
        ],
        next_step_context=_sanitize_next_steps(payload.next_steps),
        profile_facts=_sanitize_profile_facts(payload.allowed_profile_facts),
    )


def _is_high_risk_context(lowered_text: str) -> bool:
    return any(marker in lowered_text for marker in _HIGH_RISK_MARKERS)


def _summary_takeaway_for_recall(summary: SessionSummary) -> str:
    takeaway = summary.takeaway
    lowered = takeaway.lower()
    if summary.uncertainty_notes and any(
        marker in lowered for marker in ("снова", "опять", "повтор", "паттерн")
    ):
        return (
            "В прошлой сессии уже был заметный узел напряжения, "
            "но без закрепления спорной интерпретации как устойчивого факта."
        )
    return takeaway
