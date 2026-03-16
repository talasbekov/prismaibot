from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlmodel import Session

from app.billing import repository
from app.billing.models import PurchaseIntent, UserAccessState
from app.billing.prompts import (
    CANCEL_NO_ACTIVE_SUBSCRIPTION_MESSAGE,
    CANCEL_PREMIUM_SUCCESS_MESSAGE,
    PAYWALL_MESSAGE,
    STATUS_FREE_ACTIVE_MESSAGE,
    STATUS_FREE_THRESHOLD_REACHED_MESSAGE,
    STATUS_PREMIUM_MESSAGE,
)
from app.core.config import settings

if TYPE_CHECKING:
    from app.conversation.session_bootstrap import InlineButton


def record_eligible_session_completion(
    session: Session,
    *,
    telegram_user_id: int,
    session_id: uuid.UUID,
) -> None:
    """Record one completed reflective session against the user's free-usage counter.

    Idempotent: calling this twice with the same session_id has no additional effect.
    If the threshold is reached after incrementing, marks threshold_reached_at.
    Callers must commit the session after this call.
    """
    if repository.session_event_exists(session, session_id):
        return
    state = repository.get_or_create_user_access_state(session, telegram_user_id)
    repository.record_free_session_event(
        session,
        telegram_user_id=telegram_user_id,
        session_id=session_id,
    )
    repository.increment_free_sessions_used(session, state)
    if state.free_sessions_used >= settings.FREE_SESSION_THRESHOLD:
        repository.mark_threshold_reached(session, state)


def get_user_access_state(
    session: Session,
    telegram_user_id: int,
) -> UserAccessState:
    """Return the current UserAccessState for the user (creating a default if none exists)."""
    return repository.get_or_create_user_access_state(session, telegram_user_id)


def is_free_eligible(user_access_state: UserAccessState) -> bool:
    """Return True if the user has not yet crossed the free-session threshold."""
    return user_access_state.threshold_reached_at is None


def build_paywall_response(
    user_access_state: UserAccessState,  # noqa: ARG001
) -> tuple[str, list[list[InlineButton]]]:
    """Return the paywall message for a user who hit the threshold."""
    from app.conversation.session_bootstrap import InlineButton

    buttons = [[InlineButton(text="Оформить premium ✦", callback_data="pay:stars")]]
    return PAYWALL_MESSAGE, buttons


def get_or_create_purchase_intent(
    session: Session,
    telegram_user_id: int,
) -> PurchaseIntent:
    intent = repository.get_pending_purchase_intent(session, telegram_user_id)
    if intent is not None:
        return intent

    return repository.create_purchase_intent(
        session,
        telegram_user_id=telegram_user_id,
        invoice_payload=f"premium_{telegram_user_id}",
        amount=settings.PREMIUM_STARS_PRICE,
        currency="XTR",
    )


@dataclass
class PaymentConfirmationResult:
    success: bool
    already_completed: bool
    signals: list[str]


@dataclass
class CancellationResult:
    was_premium: bool
    message: str
    action: str


def process_cancellation_request(
    session: Session,
    *,
    telegram_user_id: int,
) -> CancellationResult:
    """Process a user's request to cancel their premium access.

    If the user has premium access, it is immediately downgraded to free.
    Returns a CancellationResult describing the outcome.
    Callers must commit the session after a successful call.
    """
    state = repository.get_user_access_state_by_telegram_id(session, telegram_user_id)

    if state is not None and state.access_tier == "premium":
        repository.upgrade_access_tier(session, state, "free")
        return CancellationResult(
            was_premium=True,
            message=CANCEL_PREMIUM_SUCCESS_MESSAGE,
            action="cancellation_accepted",
        )

    return CancellationResult(
        was_premium=False,
        message=CANCEL_NO_ACTIVE_SUBSCRIPTION_MESSAGE,
        action="no_active_subscription",
    )


def confirm_payment_and_upgrade(
    session: Session,
    *,
    invoice_payload: str,
    telegram_payment_charge_id: str,
    telegram_user_id: int,
) -> PaymentConfirmationResult:
    state = repository.get_or_create_user_access_state(session, telegram_user_id)
    intent = repository.get_purchase_intent_by_payload(session, invoice_payload)

    if intent is not None:
        if intent.status == "pending":
            repository.complete_purchase_intent(session, intent, telegram_payment_charge_id)
            repository.upgrade_access_tier(session, state, "premium")
            return PaymentConfirmationResult(success=True, already_completed=False, signals=[])
        elif intent.status == "completed":
            if state.access_tier != "premium":
                repository.upgrade_access_tier(session, state, "premium")
            return PaymentConfirmationResult(success=True, already_completed=True, signals=[])
        elif intent.status == "failed":
            repository.upgrade_access_tier(session, state, "premium")
            return PaymentConfirmationResult(
                success=True,
                already_completed=False,
                signals=["billing_payment_intent_in_failed_status"],
            )

    repository.upgrade_access_tier(session, state, "premium")
    return PaymentConfirmationResult(
        success=True,
        already_completed=False,
        signals=["billing_payment_intent_not_found"],
    )


def build_status_response(
    user_access_state: UserAccessState,
) -> tuple[str, list[list[InlineButton]]]:
    from app.conversation.session_bootstrap import InlineButton

    if user_access_state.access_tier == "premium":
        return STATUS_PREMIUM_MESSAGE, []

    if is_free_eligible(user_access_state):
        return STATUS_FREE_ACTIVE_MESSAGE, []

    # Free tier, threshold reached
    return (
        STATUS_FREE_THRESHOLD_REACHED_MESSAGE,
        [[InlineButton(text="Оформить premium ✦", callback_data="pay:stars")]],
    )
