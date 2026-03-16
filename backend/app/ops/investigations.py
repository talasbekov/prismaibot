from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, cast

from sqlmodel import Session, col, select

from app.memory import get_continuity_overview
from app.models import (
    OperatorAlert,
    OperatorInvestigation,
    SafetySignal,
    TelegramSession,
)
from app.ops.signals import record_retryable_signal

_ALLOWED_REASON_CODES = frozenset(
    {
        "critical_safety_review",
        "false_positive_review",
        "operator_training_review",
    }
)
_ALLOWED_OUTCOMES = frozenset(
    {
        "confirmed_crisis",
        "false_positive",
        "needs_follow_up",
        "insufficient_context",
    }
)


class InvestigationContextError(RuntimeError):
    """Raised when bounded investigation context cannot be assembled."""


class InvestigationStateError(ValueError):
    """Raised when an investigation operation is invalid for the current status."""


class InvestigationConflictError(ValueError):
    """Raised when an open investigation already exists for the given alert."""


def request_and_open_operator_investigation(
    session: Session,
    *,
    operator_alert_id: uuid.UUID,
    reason_code: str,
    requested_by: str,
    approved_by: str,
    audit_notes: str | None = None,
) -> OperatorInvestigation:
    alert = session.get(OperatorAlert, operator_alert_id)
    if alert is None:
        raise LookupError("operator_alert_not_found")

    existing = session.exec(
        select(OperatorInvestigation).where(
            OperatorInvestigation.operator_alert_id == operator_alert_id,
            col(OperatorInvestigation.status).in_(["requested", "opened"]),
        )
    ).first()
    if existing is not None:
        raise InvestigationConflictError(
            f"investigation_already_open:{existing.id}"
        )

    session_record = session.get(TelegramSession, alert.session_id)
    if session_record is None:
        raise LookupError("telegram_session_not_found")

    normalized_reason_code = _normalize_reason_code(reason_code)
    now = datetime.now(timezone.utc)
    investigation = OperatorInvestigation(
        operator_alert_id=alert.id,
        session_id=alert.session_id,
        telegram_user_id=alert.telegram_user_id,
        reason_code=normalized_reason_code,
        status="requested",
        requested_by=_normalize_actor(requested_by),
        source_classification=alert.classification,
        source_trigger_category=alert.trigger_category,
        source_confidence=alert.confidence,
        audit_notes=_sanitize_audit_notes(audit_notes),
        context_payload={},
        requested_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(investigation)
    session.commit()
    session.refresh(investigation)

    approved_actor = _normalize_actor(approved_by)
    investigation.approved_by = approved_actor
    investigation.approved_at = now
    investigation.opened_at = now

    try:
        investigation.context_payload = _build_investigation_context_payload(
            session,
            alert=alert,
            session_record=session_record,
        )
        investigation.status = "opened"
    except InvestigationContextError as exc:
        investigation.status = "failed"
        investigation.context_payload = {}
        investigation.audit_notes = _merge_audit_notes(
            investigation.audit_notes,
            f"context_build_failed: {str(exc)[:200]}",
        )
        record_retryable_signal(
            session,
            session_id=alert.session_id,
            telegram_user_id=alert.telegram_user_id,
            signal_type="operator_investigation_context_failed",
            error_type="InvestigationContextError",
            error_message=str(exc),
            suggested_action="review_operator_investigation_context_failure",
            retry_payload={
                "operator_alert_id": str(alert.id),
                "operator_investigation_id": str(investigation.id),
                "reason_code": normalized_reason_code,
            },
            failure_stage="ops_investigation",
        )

    investigation.updated_at = datetime.now(timezone.utc)
    session.add(investigation)
    session.commit()
    session.refresh(investigation)
    return investigation


def get_operator_investigation(
    session: Session,
    *,
    investigation_id: uuid.UUID,
) -> OperatorInvestigation:
    investigation = session.get(OperatorInvestigation, investigation_id)
    if investigation is None:
        raise LookupError("operator_investigation_not_found")
    return investigation


def close_operator_investigation(
    session: Session,
    *,
    investigation_id: uuid.UUID,
    reviewed_by: str,
    reviewed_classification: str,
    outcome: str,
    audit_notes: str | None = None,
) -> OperatorInvestigation:
    investigation = get_operator_investigation(
        session, investigation_id=investigation_id
    )
    if investigation.status != "opened":
        raise InvestigationStateError(
            f"investigation_not_closeable:{investigation.status}"
        )
    investigation.reviewed_by = _normalize_actor(reviewed_by)
    investigation.reviewed_classification = reviewed_classification[:16]
    investigation.outcome = _normalize_outcome(outcome)
    investigation.audit_notes = _sanitize_audit_notes(audit_notes)
    investigation.status = "closed"
    investigation.closed_at = datetime.now(timezone.utc)
    investigation.updated_at = investigation.closed_at
    session.add(investigation)
    session.commit()
    session.refresh(investigation)
    return investigation


def deny_operator_investigation(
    session: Session,
    *,
    investigation_id: uuid.UUID,
    denied_by: str,
    audit_notes: str | None = None,
) -> OperatorInvestigation:
    investigation = get_operator_investigation(
        session, investigation_id=investigation_id
    )
    now = datetime.now(timezone.utc)
    denier_note = f"denied_by:{_normalize_actor(denied_by)}"
    investigation.audit_notes = _merge_audit_notes(
        denier_note, audit_notes or ""
    ) if audit_notes else _sanitize_audit_notes(denier_note)
    investigation.status = "denied"
    investigation.closed_at = now
    investigation.updated_at = now
    session.add(investigation)
    session.commit()
    session.refresh(investigation)
    return investigation


def list_operator_investigations(
    session: Session,
) -> list[OperatorInvestigation]:
    return list(
        session.exec(
            select(OperatorInvestigation).order_by(
                cast(Any, OperatorInvestigation.created_at).desc()
            )
        ).all()
    )


def _build_investigation_context_payload(
    session: Session,
    *,
    alert: OperatorAlert,
    session_record: TelegramSession,
) -> dict[str, Any]:
    try:
        continuity_overview = get_continuity_overview(
            session, telegram_user_id=alert.telegram_user_id
        )
    except Exception as exc:  # pragma: no cover - defensive branch
        raise InvestigationContextError("continuity overview unavailable") from exc

    try:
        safety_signals = session.exec(
            select(SafetySignal)
            .where(SafetySignal.session_id == session_record.id)
            .order_by(cast(Any, SafetySignal.turn_index))
        ).all()
    except Exception as exc:
        raise InvestigationContextError("safety signal query failed") from exc

    return {
        "alert": {
            "id": str(alert.id),
            "classification": alert.classification,
            "trigger_category": alert.trigger_category,
            "confidence": alert.confidence,
            "status": alert.status,
            "delivery_channel": alert.delivery_channel,
        },
        "session": {
            "id": str(session_record.id),
            "crisis_state": session_record.crisis_state,
            "crisis_activated_at": _isoformat(session_record.crisis_activated_at),
            "crisis_last_routed_at": _isoformat(session_record.crisis_last_routed_at),
            "crisis_step_down_at": _isoformat(session_record.crisis_step_down_at),
            "transcript_purged_at": _isoformat(session_record.transcript_purged_at),
        },
        "current_turn": {
            "last_user_message": session_record.last_user_message,
            "last_bot_prompt": session_record.last_bot_prompt,
        },
        "safety_signals": [
            {
                "turn_index": signal.turn_index,
                "classification": signal.classification,
                "trigger_category": signal.trigger_category,
                "confidence": signal.confidence,
                "created_at": _isoformat(signal.created_at),
            }
            for signal in safety_signals
        ],
        "continuity_overview": continuity_overview.model_dump(mode="json"),
    }


def _normalize_reason_code(reason_code: str) -> str:
    normalized = reason_code.strip().lower()[:64]
    if normalized in _ALLOWED_REASON_CODES:
        return normalized
    return "critical_safety_review"


def _normalize_outcome(outcome: str) -> str:
    normalized = outcome.strip().lower()[:64]
    if normalized in _ALLOWED_OUTCOMES:
        return normalized
    return "needs_follow_up"


def _normalize_actor(actor: str) -> str:
    cleaned = actor.strip()[:64]
    return cleaned or "ops:token"


def _sanitize_audit_notes(audit_notes: str | None) -> str | None:
    if audit_notes is None:
        return None
    cleaned = audit_notes.strip()[:1000]
    return cleaned or None


def _merge_audit_notes(existing: str | None, addition: str) -> str:
    prefix = f"{existing}\n" if existing else ""
    return f"{prefix}{addition}"[:1000]


def _isoformat(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()
