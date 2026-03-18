from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.billing.models import (
    FreeSessionEvent,
    PurchaseIntent,
    Subscription,
    UserAccessState,
)
from app.models import TelegramSession


@dataclass
class BillingIssue:
    telegram_user_id: int
    issue_category: str  # "payment_failed" | "payment_stale_pending" | "payment_completed_no_access" | "premium_access_no_payment"
    intent_id: uuid.UUID | None
    intent_status: str | None
    intent_created_at: datetime | None
    intent_updated_at: datetime | None
    provider_payment_charge_id: str | None
    access_tier: str | None
    access_updated_at: datetime | None


@dataclass
class UserBillingContext:
    telegram_user_id: int
    access_tier: str
    free_sessions_used: int
    first_session_completed: bool
    threshold_reached_at: datetime | None
    subscription: dict[str, Any] | None = None
    purchase_intents: list[dict] = field(default_factory=list)


_STALE_PENDING_THRESHOLD_HOURS = 24


def list_billing_issues(
    session: Session, limit: int = 100, offset: int = 0
) -> list[BillingIssue]:
    issues: list[BillingIssue] = []
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=_STALE_PENDING_THRESHOLD_HOURS)

    # 1. Failed intents
    for intent in session.exec(
        select(PurchaseIntent).where(PurchaseIntent.status == "failed")
    ).all():
        access = session.exec(
            select(UserAccessState).where(UserAccessState.telegram_user_id == intent.telegram_user_id)
        ).first()
        issues.append(BillingIssue(
            telegram_user_id=intent.telegram_user_id,
            issue_category="payment_failed",
            intent_id=intent.id,
            intent_status=intent.status,
            intent_created_at=intent.created_at,
            intent_updated_at=intent.updated_at,
            provider_payment_charge_id=intent.provider_payment_charge_id,
            access_tier=access.access_tier if access else None,
            access_updated_at=access.updated_at if access else None,
        ))

    # 2. Stale pending intents (> 24h)
    for intent in session.exec(
        select(PurchaseIntent).where(
            PurchaseIntent.status == "pending",
            PurchaseIntent.created_at < stale_cutoff,
        )
    ).all():
        access = session.exec(
            select(UserAccessState).where(UserAccessState.telegram_user_id == intent.telegram_user_id)
        ).first()
        issues.append(BillingIssue(
            telegram_user_id=intent.telegram_user_id,
            issue_category="payment_stale_pending",
            intent_id=intent.id,
            intent_status=intent.status,
            intent_created_at=intent.created_at,
            intent_updated_at=intent.updated_at,
            provider_payment_charge_id=intent.provider_payment_charge_id,
            access_tier=access.access_tier if access else None,
            access_updated_at=access.updated_at if access else None,
        ))

    # 3. Completed intent but access_tier != "premium"
    for intent in session.exec(
        select(PurchaseIntent).where(PurchaseIntent.status == "completed")
    ).all():
        access = session.exec(
            select(UserAccessState).where(UserAccessState.telegram_user_id == intent.telegram_user_id)
        ).first()
        if access is None or access.access_tier != "premium":
            issues.append(BillingIssue(
                telegram_user_id=intent.telegram_user_id,
                issue_category="payment_completed_no_access",
                intent_id=intent.id,
                intent_status=intent.status,
                intent_created_at=intent.created_at,
                intent_updated_at=intent.updated_at,
                provider_payment_charge_id=intent.provider_payment_charge_id,
                access_tier=access.access_tier if access else None,
                access_updated_at=access.updated_at if access else None,
            ))

    # 4. Premium access but no completed intent
    for state in session.exec(
        select(UserAccessState).where(UserAccessState.access_tier == "premium")
    ).all():
        completed = session.exec(
            select(PurchaseIntent).where(
                PurchaseIntent.telegram_user_id == state.telegram_user_id,
                PurchaseIntent.status == "completed",
            )
        ).first()
        if completed is None:
            issues.append(BillingIssue(
                telegram_user_id=state.telegram_user_id,
                issue_category="premium_access_no_payment",
                intent_id=None,
                intent_status=None,
                intent_created_at=None,
                intent_updated_at=None,
                provider_payment_charge_id=None,
                access_tier=state.access_tier,
                access_updated_at=state.updated_at,
            ))

    # Apply pagination on the aggregated list
    return issues[offset : offset + limit]


def get_user_billing_context(
    session: Session, telegram_user_id: int
) -> UserBillingContext | None:
    access = session.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == telegram_user_id)
    ).first()
    intents = session.exec(
        select(PurchaseIntent).where(PurchaseIntent.telegram_user_id == telegram_user_id)
    ).all()
    sub = session.exec(
        select(Subscription).where(Subscription.telegram_user_id == telegram_user_id)
    ).first()

    if access is None and not intents and not sub:
        return None

    return UserBillingContext(
        telegram_user_id=telegram_user_id,
        access_tier=access.access_tier if access else "unknown",
        free_sessions_used=access.free_sessions_used if access else 0,
        first_session_completed=access.first_session_completed if access else False,
        threshold_reached_at=access.threshold_reached_at if access else None,
        subscription={
            "status": sub.status,
            "provider_type": sub.provider_type,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancel_at_period_end": sub.cancel_at_period_end,
        } if sub else None,
        purchase_intents=[
            {
                "id": str(i.id),
                "invoice_payload": i.invoice_payload,
                "amount": i.amount,
                "currency": i.currency,
                "status": i.status,
                "provider_payment_charge_id": i.provider_payment_charge_id,
                "created_at": i.created_at.isoformat() if i.created_at else None,
                "updated_at": i.updated_at.isoformat() if i.updated_at else None,
            }
            for i in intents
        ],
    )


def get_system_stats(session: Session) -> dict[str, Any]:
    """Retrieve aggregate system metrics for operators."""
    from sqlalchemy import func

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)

    stats = {
        "total_users": session.exec(select(func.count(UserAccessState.id))).one(),
        "total_sessions": session.exec(select(func.count(TelegramSession.id))).one(),
        "active_subscriptions": session.exec(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        ).one(),
        "past_due_subscriptions": session.exec(
            select(func.count(Subscription.id)).where(Subscription.status == "past_due")
        ).one(),
        "recent_sessions_24h": session.exec(
            select(func.count(TelegramSession.id)).where(
                TelegramSession.created_at > day_ago
            )
        ).one(),
        "completed_intents_24h": session.exec(
            select(func.count(PurchaseIntent.id)).where(
                PurchaseIntent.status == "completed",
                PurchaseIntent.updated_at > day_ago,
            )
        ).one(),
    }
    return stats
