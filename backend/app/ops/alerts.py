from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import OperatorAlert, TelegramSession
from app.ops.signals import record_retryable_signal
from app.safety.service import SafetyAssessment

OPS_ALERT_CHANNEL = "ops_inbox"


class AlertDeliveryError(RuntimeError):
    """Raised when the bounded operator-alert delivery step fails."""


def create_and_deliver_operator_alert(
    session: Session,
    *,
    session_record: TelegramSession,
    assessment: SafetyAssessment,
    newly_activated: bool,
) -> OperatorAlert:
    now = datetime.now(timezone.utc)
    payload = _build_alert_payload(
        session_record=session_record,
        assessment=assessment,
        newly_activated=newly_activated,
    )

    alert = session.exec(
        select(OperatorAlert).where(OperatorAlert.session_id == session_record.id)
    ).first()
    if alert is None:
        alert = OperatorAlert(
            session_id=session_record.id,
            telegram_user_id=session_record.telegram_user_id,
            classification=assessment.classification,
            trigger_category=assessment.trigger_category,
            confidence=assessment.confidence,
            delivery_channel=OPS_ALERT_CHANNEL,
            status="created",
            payload=payload,
            delivery_attempt_count=0,
            dedupe_key=f"crisis-session:{session_record.id}",
            first_routed_at=session_record.crisis_activated_at or now,
            created_at=now,
            updated_at=now,
        )
    else:
        alert.classification = assessment.classification
        alert.trigger_category = assessment.trigger_category
        alert.confidence = assessment.confidence
        alert.payload = payload
        alert.updated_at = now
        alert.status = "created"
        alert.last_delivery_error = None

    try:
        session.add(alert)
        session.commit()
    except IntegrityError:
        # Concurrent request created the alert between our select and insert.
        session.rollback()
        alert = session.exec(
            select(OperatorAlert).where(OperatorAlert.session_id == session_record.id)
        ).one()
        alert.classification = assessment.classification
        alert.trigger_category = assessment.trigger_category
        alert.confidence = assessment.confidence
        alert.payload = payload
        alert.updated_at = now
        alert.status = "created"
        alert.last_delivery_error = None
        session.add(alert)
        session.commit()
    session.refresh(alert)

    try:
        _deliver_to_ops_inbox(alert)
    except Exception as exc:
        alert.status = "delivery_failed"
        alert.delivery_attempt_count += 1
        alert.last_delivery_attempt_at = now
        alert.last_delivery_error = str(exc)[:500]
        alert.updated_at = datetime.now(timezone.utc)
        session.add(alert)
        record_retryable_signal(
            session,
            session_id=session_record.id,
            telegram_user_id=session_record.telegram_user_id,
            signal_type="operator_alert_delivery_failed",
            error_type="OperatorAlertDeliveryError",
            error_message=str(exc),
            suggested_action="review_operator_alert_delivery_failure",
            retry_payload={
                "operator_alert_id": str(alert.id),
                "delivery_channel": alert.delivery_channel,
                "classification": alert.classification,
            },
            failure_stage="ops_delivery",
        )
        session.commit()
        session.refresh(alert)
        return alert

    delivered_now = datetime.now(timezone.utc)
    alert.status = "delivered"
    alert.delivery_attempt_count += 1
    alert.last_delivery_attempt_at = delivered_now
    alert.delivered_at = delivered_now
    alert.last_delivery_error = None
    alert.updated_at = delivered_now
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return alert


def list_operator_alerts(session: Session) -> list[OperatorAlert]:
    return list(
        session.exec(
            select(OperatorAlert).order_by(cast(Any, OperatorAlert.created_at).desc())
        ).all()
    )


def _build_alert_payload(
    *,
    session_record: TelegramSession,
    assessment: SafetyAssessment,
    newly_activated: bool,
) -> dict[str, str]:
    return {
        "session_id": str(session_record.id),
        "telegram_user_id": str(session_record.telegram_user_id),
        "classification": assessment.classification,
        "trigger_category": assessment.trigger_category,
        "confidence": assessment.confidence,
        "crisis_state": session_record.crisis_state,
        "newly_activated": "true" if newly_activated else "false",
        "crisis_activated_at": (
            session_record.crisis_activated_at.isoformat()
            if session_record.crisis_activated_at is not None
            else ""
        ),
        "crisis_last_routed_at": (
            session_record.crisis_last_routed_at.isoformat()
            if session_record.crisis_last_routed_at is not None
            else ""
        ),
    }


def _deliver_to_ops_inbox(_alert: OperatorAlert) -> None:
    """MVP delivery seam: durable ops inbox is the operational channel."""
    return None
