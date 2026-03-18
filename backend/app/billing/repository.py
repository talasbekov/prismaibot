from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.billing.models import (
    FreeSessionEvent,
    PurchaseIntent,
    Subscription,
    UserAccessState,
)


def get_or_create_user_access_state(
    session: Session,
    telegram_user_id: int,
) -> UserAccessState:
    state = get_user_access_state_by_telegram_id(session, telegram_user_id)
    if state is not None:
        return state
    state = UserAccessState(
        telegram_user_id=telegram_user_id,
        access_tier="free",
        free_sessions_used=0,
    )
    session.add(state)
    return state


def get_user_access_state_by_telegram_id(
    session: Session,
    telegram_user_id: int,
) -> UserAccessState | None:
    return session.exec(
        select(UserAccessState).where(
            UserAccessState.telegram_user_id == telegram_user_id
        )
    ).first()


def session_event_exists(
    session: Session,
    session_id: uuid.UUID,
) -> bool:
    event = session.exec(
        select(FreeSessionEvent).where(FreeSessionEvent.session_id == session_id)
    ).first()
    return event is not None


def record_free_session_event(
    session: Session,
    *,
    telegram_user_id: int,
    session_id: uuid.UUID,
) -> None:
    event = FreeSessionEvent(
        telegram_user_id=telegram_user_id,
        session_id=session_id,
    )
    session.add(event)


def increment_free_sessions_used(
    session: Session,
    user_access_state: UserAccessState,
) -> None:
    user_access_state.free_sessions_used += 1
    user_access_state.updated_at = datetime.now(timezone.utc)
    session.add(user_access_state)


def mark_threshold_reached(
    session: Session,
    user_access_state: UserAccessState,
) -> None:
    user_access_state.threshold_reached_at = datetime.now(timezone.utc)
    user_access_state.updated_at = datetime.now(timezone.utc)
    session.add(user_access_state)


def mark_first_session_completed(
    session: Session,
    user_access_state: UserAccessState,
) -> None:
    user_access_state.first_session_completed = True
    user_access_state.updated_at = datetime.now(timezone.utc)
    session.add(user_access_state)


def get_pending_purchase_intent(
    session: Session,
    telegram_user_id: int,
) -> PurchaseIntent | None:
    return session.exec(
        select(PurchaseIntent).where(
            PurchaseIntent.telegram_user_id == telegram_user_id,
            PurchaseIntent.status == "pending",
        )
    ).first()


def create_purchase_intent(
    session: Session,
    *,
    id: uuid.UUID | None = None,
    telegram_user_id: int,
    invoice_payload: str,
    amount: int,
    currency: str = "XTR",
    provider_type: str = "telegram_stars",
    provider_invoice_id: str | None = None,
    phone_number: str | None = None,
) -> PurchaseIntent:
    intent = PurchaseIntent(
        id=id or uuid.uuid4(),
        telegram_user_id=telegram_user_id,
        invoice_payload=invoice_payload,
        amount=amount,
        currency=currency,
        status="pending",
        provider_type=provider_type,
        provider_invoice_id=provider_invoice_id,
        phone_number=phone_number,
    )
    session.add(intent)
    return intent


def get_purchase_intent_by_payload(
    session: Session,
    invoice_payload: str,
) -> PurchaseIntent | None:
    return session.exec(
        select(PurchaseIntent).where(PurchaseIntent.invoice_payload == invoice_payload)
    ).first()


def get_purchase_intent_by_provider_invoice_id(
    session: Session,
    provider_invoice_id: str,
) -> PurchaseIntent | None:
    return session.exec(
        select(PurchaseIntent).where(
            PurchaseIntent.provider_invoice_id == provider_invoice_id
        )
    ).first()


def complete_purchase_intent(
    session: Session,
    intent: PurchaseIntent,
    provider_payment_charge_id: str,
) -> None:
    intent.status = "completed"
    intent.provider_payment_charge_id = provider_payment_charge_id
    intent.updated_at = datetime.now(timezone.utc)
    session.add(intent)


def upgrade_access_tier(
    session: Session,
    user_access_state: UserAccessState,
    tier: str = "premium",
) -> None:
    user_access_state.access_tier = tier
    user_access_state.updated_at = datetime.now(timezone.utc)
    session.add(user_access_state)


def get_subscription(session: Session, telegram_user_id: int) -> Subscription | None:
    return session.exec(
        select(Subscription).where(Subscription.telegram_user_id == telegram_user_id)
    ).first()


def get_subscription_by_provider_id(
    session: Session, provider_subscription_id: str
) -> Subscription | None:
    return session.exec(
        select(Subscription).where(
            Subscription.provider_subscription_id == provider_subscription_id
        )
    ).first()


def create_or_update_subscription(
    session: Session,
    *,
    telegram_user_id: int,
    status: str,
    current_period_end: datetime,
    cancel_at_period_end: bool = False,
    provider_type: str = "telegram_stars",
    provider_subscription_id: str | None = None,
) -> Subscription:
    subscription = get_subscription(session, telegram_user_id)
    if not subscription:
        subscription = Subscription(
            telegram_user_id=telegram_user_id,
            status=status,
            current_period_end=current_period_end,
            cancel_at_period_end=cancel_at_period_end,
            provider_type=provider_type,
            provider_subscription_id=provider_subscription_id,
        )
    else:
        subscription.status = status
        subscription.current_period_end = current_period_end
        subscription.cancel_at_period_end = cancel_at_period_end
        subscription.provider_type = provider_type
        if provider_subscription_id:
            subscription.provider_subscription_id = provider_subscription_id
        subscription.updated_at = datetime.now(timezone.utc)

    session.add(subscription)
    return subscription
