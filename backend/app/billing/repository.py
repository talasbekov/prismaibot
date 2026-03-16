from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.billing.models import FreeSessionEvent, PurchaseIntent, UserAccessState


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
    telegram_user_id: int,
    invoice_payload: str,
    amount: int,
    currency: str = "XTR",
) -> PurchaseIntent:
    intent = PurchaseIntent(
        telegram_user_id=telegram_user_id,
        invoice_payload=invoice_payload,
        amount=amount,
        currency=currency,
        status="pending",
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
