from __future__ import annotations

from dataclasses import dataclass, field

from sqlmodel import Session, func, select

from app.billing.models import PurchaseIntent
from app.models import (
    DeletionRequest,
    OperatorAlert,
    SummaryGenerationSignal,
    TelegramSession,
)


@dataclass
class SessionActivityCounts:
    total_active: int = 0
    total_crisis_active: int = 0


@dataclass
class PaymentSignalCounts:
    pending: int = 0
    confirmed: int = 0
    failed: int = 0


@dataclass
class OperationalStatusResult:
    session_activity: SessionActivityCounts = field(default_factory=SessionActivityCounts)
    open_summary_failure_signals: int = 0
    undelivered_operator_alerts: int = 0
    pending_deletion_requests: int = 0
    payment_signals: PaymentSignalCounts = field(default_factory=PaymentSignalCounts)
    degraded_fields: list[str] = field(default_factory=list)


def get_operational_status(session: Session) -> OperationalStatusResult:
    result = OperationalStatusResult()

    try:
        # Using func.count() with select_from to satisfy mypy
        result.session_activity.total_active = session.exec(
            select(func.count()).select_from(TelegramSession).where(TelegramSession.status == "active")
        ).one()
        result.session_activity.total_crisis_active = session.exec(
            select(func.count()).select_from(TelegramSession).where(
                TelegramSession.crisis_state == "crisis_active"
            )
        ).one()
    except Exception:
        result.degraded_fields.append("session_activity")

    try:
        result.open_summary_failure_signals = session.exec(
            select(func.count()).select_from(SummaryGenerationSignal).where(
                SummaryGenerationSignal.status == "open"
            )
        ).one()
    except Exception:
        result.degraded_fields.append("open_summary_failure_signals")

    try:
        result.undelivered_operator_alerts = session.exec(
            select(func.count()).select_from(OperatorAlert).where(OperatorAlert.status != "delivered")
        ).one()
    except Exception:
        result.degraded_fields.append("undelivered_operator_alerts")

    try:
        result.pending_deletion_requests = session.exec(
            select(func.count()).select_from(DeletionRequest).where(DeletionRequest.status == "pending")
        ).one()
    except Exception:
        result.degraded_fields.append("pending_deletion_requests")

    for status_val in ("pending", "confirmed", "failed"):
        try:
            count = session.exec(
                select(func.count()).select_from(PurchaseIntent).where(PurchaseIntent.status == status_val)
            ).one()
            setattr(result.payment_signals, status_val, count)
        except Exception:
            if "payment_signals" not in result.degraded_fields:
                result.degraded_fields.append("payment_signals")

    return result
