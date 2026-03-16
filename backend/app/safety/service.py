from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Literal

from sqlmodel import Session, select

from app.core.config import settings
from app.models import SafetySignal, TelegramSession

logger = logging.getLogger(__name__)

SafetyClassification = Literal["safe", "borderline", "crisis"]
SafetyCategory = Literal["none", "self_harm", "dangerous_abuse"]
SafetyConfidence = Literal["low", "medium", "high"]

_CRISIS_SELF_HARM_PATTERNS = (
    "покончить с собой",
    "покончу с собой",       # conjugated future form, missed by infinitive-only coverage
    "хочу умереть",
    "не хочу жить",
    "убью себя",
    "убить себя",            # alternative infinitive phrase
    "суицид",
    "суиц",                  # prefix covers "суицидальный", "суицидальные" etc.
    "причинить себе вред",
    "самоуб",                # prefix covers "самоубийство", "самоубийца"
    "самоповреж",            # prefix covers "самоповреждение"
    "селфхарм",
)
_BORDERLINE_SELF_HARM_PATTERNS = (
    "лучше бы исчезнуть",
    "исчезнуть",
    "всем без меня лучше",
    "не хочу просыпаться",
)
# Direct abuse patterns — crisis-level without additional personal context.
# These terms unambiguously indicate dangerous abuse or sexual violence and
# are specific enough that any mention in a reflective context warrants escalation.
_CRISIS_ABUSE_DIRECT_PATTERNS = (
    "насили",     # covers "насилие", "насилуют", "насиловали", "насиловать"
    "насилова",   # covers explicit verb forms like "насиловали"
    "изнасил",    # covers "изнасилование", "изнасиловал", "изнасилован"
)
# Context-dependent abuse patterns — crisis only when combined with personal risk markers.
# Removing "убьет" as a standalone pattern prevents idiom false positives ("это убьет меня");
# it is caught by the contextual path only when combined with an identity marker.
_DANGEROUS_ABUSE_PATTERNS = (
    "ударил",
    "бьет",
    "бьёт",
    "убьет",
    "убьёт",
    "убью",
    "запер",
    "не выпускает",
    "угрожает",
    "абьюз",     # covers "абьюзит", "абьюзер"
    "избил",
)
# Identity/relationship markers indicating the user is personally at risk.
# "сейчас" (now) was removed — it is too generic and caused false positives when
# combined with metaphorical violence language (e.g., "он ударил по столу сейчас").
_PERSONAL_RISK_MARKERS = (
    "меня",
    "мне",
    "если я",
    "дома",
    "расскажу",
)
_FALSE_POSITIVE_RECOVERY_PATTERNS = (
    "не собираюсь причинять себе вред",
    "не собираюсь убивать себя",
    "не собираюсь с собой ничего делать",
    "не хочу причинять себе вред",
    "не хочу убивать себя",
    "не покончу с собой",
    "я не в опасности",
    "мне не угрожают",
    "он не бьет меня",
    "он не бьёт меня",
    "это не про насилие",
)


@dataclass(frozen=True)
class SafetyAssessment:
    classification: SafetyClassification
    trigger_category: SafetyCategory
    confidence: SafetyConfidence
    blocks_normal_flow: bool


def assess_message_safety(message_text: str) -> SafetyAssessment:
    normalized = _normalize(message_text)

    if any(pattern in normalized for pattern in _CRISIS_SELF_HARM_PATTERNS):
        return SafetyAssessment(
            classification="crisis",
            trigger_category="self_harm",
            confidence="high",
            blocks_normal_flow=True,
        )

    if _contains_dangerous_abuse(normalized):
        return SafetyAssessment(
            classification="crisis",
            trigger_category="dangerous_abuse",
            confidence="high",
            blocks_normal_flow=True,
        )

    if any(pattern in normalized for pattern in _BORDERLINE_SELF_HARM_PATTERNS):
        return SafetyAssessment(
            classification="borderline",
            trigger_category="self_harm",
            confidence="medium",
            blocks_normal_flow=False,
        )

    return SafetyAssessment(
        classification="safe",
        trigger_category="none",
        confidence="low",
        blocks_normal_flow=False,
    )


def evaluate_incoming_message_safety(
    session: Session,
    *,
    session_record: TelegramSession,
    message_text: str,
    turn_index: int,
) -> SafetyAssessment:
    if not settings.SAFETY_ENABLED:
        logger.info(
            "Safety check bypassed for session %s, turn %d (SAFETY_ENABLED=False)",
            session_record.id,
            turn_index,
        )
        assessment = SafetyAssessment(
            classification="safe",
            trigger_category="none",
            confidence="low",
            blocks_normal_flow=False,
        )
    else:
        assessment = assess_message_safety(message_text)

    now = datetime.now(timezone.utc)

    # New sessions may exist only in the current unit of work.
    # Flush once so any bounded safety signal can safely reference the session row.
    session.add(session_record)
    session.flush()

    session_record.safety_classification = assessment.classification
    session_record.safety_trigger_category = assessment.trigger_category
    session_record.safety_confidence = assessment.confidence
    session_record.safety_last_evaluated_at = now

    if assessment.classification != "safe":
        # Upsert: avoid duplicate signals on Telegram retry or double-delivery of the
        # same turn. The unique constraint on (session_id, turn_index) enforces this
        # at the DB layer; the read-before-write here keeps the logic explicit.
        existing_signal = session.exec(
            select(SafetySignal)
            .where(SafetySignal.session_id == session_record.id)
            .where(SafetySignal.turn_index == turn_index)
        ).first()
        if existing_signal is None:
            session.add(
                SafetySignal(
                    session_id=session_record.id,
                    telegram_user_id=session_record.telegram_user_id,
                    turn_index=turn_index,
                    classification=assessment.classification,
                    trigger_category=assessment.trigger_category,
                    confidence=assessment.confidence,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            existing_signal.classification = assessment.classification
            existing_signal.trigger_category = assessment.trigger_category
            existing_signal.confidence = assessment.confidence
            existing_signal.updated_at = now
            session.add(existing_signal)

    return assessment


def should_step_down_from_crisis(
    *,
    message_text: str,
    assessment: SafetyAssessment,
) -> bool:
    if assessment.classification != "safe" or assessment.blocks_normal_flow:
        return False
    normalized = _normalize(message_text)
    return any(pattern in normalized for pattern in _FALSE_POSITIVE_RECOVERY_PATTERNS)


def _normalize(message_text: str) -> str:
    return " ".join(message_text.casefold().split())


def _contains_dangerous_abuse(normalized: str) -> bool:
    # Direct patterns indicate crisis-level abuse without needing personal context.
    if any(pattern in normalized for pattern in _CRISIS_ABUSE_DIRECT_PATTERNS):
        return True
    # Context-dependent patterns require personal risk markers to reduce false
    # positives from impersonal or metaphorical statements.
    has_violence = any(pattern in normalized for pattern in _DANGEROUS_ABUSE_PATTERNS)
    has_personal_risk = any(marker in normalized for marker in _PERSONAL_RISK_MARKERS)
    return has_violence and has_personal_risk
