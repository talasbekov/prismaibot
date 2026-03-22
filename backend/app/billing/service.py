from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from sqlmodel import Session

from app.billing import repository
from app.billing.models import Subscription, UserAccessState
from app.billing.prompts import (
    CANCEL_NO_ACTIVE_SUBSCRIPTION_MESSAGE,
    CANCEL_PREMIUM_SUCCESS_MESSAGE,
    PAYMENT_RETRY_MESSAGE,
    PAYWALL_MESSAGE,
    STATUS_FREE_ACTIVE_MESSAGE,
    STATUS_FREE_THRESHOLD_REACHED_MESSAGE,
    STATUS_PREMIUM_MESSAGE,
    STATUS_SUBSCRIPTION_ACTIVE_MESSAGE,
    STATUS_SUBSCRIPTION_PAST_DUE_MESSAGE,
    STATUS_SUBSCRIPTION_SUSPENDED_MESSAGE,
)
from app.billing.apipay_client import ApiPayClient
from app.billing.utils import normalize_phone_number
from app.bot.utils import send_telegram_message
from app.core.config import settings

logger = logging.getLogger(__name__)


async def process_apipay_webhook(
    session: Session,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Process incoming ApiPay webhook.
    Returns processing result for the API response.
    """
    event = payload.get("event")
    invoice_data = payload.get("invoice", {})
    subscription_data = payload.get("subscription", {})
    
    if event == "invoice.status_changed":
        provider_invoice_id = str(invoice_data.get("id"))
        status = invoice_data.get("status")

        if status == "paid":
            # 1. Find intent
            intent = repository.get_purchase_intent_by_provider_invoice_id(session, provider_invoice_id)
            if not intent:
                logger.warning("PurchaseIntent not found for provider_invoice_id=%s", provider_invoice_id)
                return {"status": "error", "message": "intent_not_found"}

            if intent.status == "completed":
                return {"status": "ok", "message": "already_processed"}

            # 2. Complete intent
            repository.complete_purchase_intent(session, intent, f"apipay_{provider_invoice_id}")

            # 3. Upgrade user access
            state = repository.get_or_create_user_access_state(session, intent.telegram_user_id)
            repository.upgrade_access_tier(session, state, "premium")

            # 4. Create/Update subscription
            from datetime import timedelta
            current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
            repository.create_or_update_subscription(
                session,
                telegram_user_id=intent.telegram_user_id,
                status="active",
                current_period_end=current_period_end,
                provider_type="apipay",
            )
            session.commit()

            # 5. Notify user
            from app.billing.prompts import PAYMENT_SUCCESS_MESSAGE
            await send_telegram_message(intent.telegram_user_id, PAYMENT_SUCCESS_MESSAGE)

            return {"status": "ok", "message": "payment_confirmed"}

    if event == "invoice.refunded":
        refund_data = payload.get("refund", {})
        invoice_data_refund = payload.get("invoice", {})
        logger.info(
            "invoice.refunded received: refund_id=%s invoice_id=%s amount=%s — no action taken",
            refund_data.get("id"),
            invoice_data_refund.get("id"),
            refund_data.get("amount"),
        )
        return {"status": "ok", "message": "refund_logged"}

    if event == "subscription.payment_succeeded":
        provider_sub_id = str(subscription_data.get("id"))
        sub = repository.get_subscription_by_provider_id(session, provider_sub_id)
        if not sub:
            logger.warning("Subscription not found for provider_sub_id=%s", provider_sub_id)
            return {"status": "error", "message": "subscription_not_found"}
            
        # Extend by 30 days from now
        from datetime import timedelta
        sub.status = "active"
        sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
        sub.updated_at = datetime.now(timezone.utc)
        
        # Ensure access_tier is premium
        state = repository.get_or_create_user_access_state(session, sub.telegram_user_id)
        repository.upgrade_access_tier(session, state, "premium")
        
        session.add(sub)
        session.commit()
        return {"status": "ok", "message": "subscription_extended"}

    if event == "subscription.payment_failed":
        provider_sub_id = str(subscription_data.get("id"))
        sub = repository.get_subscription_by_provider_id(session, provider_sub_id)
        if not sub:
            logger.warning("Subscription not found for provider_sub_id=%s", provider_sub_id)
            return {"status": "error", "message": "subscription_not_found"}

        logger.info("Payment failed for subscription provider_sub_id=%s, ApiPay will retry", provider_sub_id)
        await send_telegram_message(sub.telegram_user_id, PAYMENT_RETRY_MESSAGE)
        return {"status": "ok", "message": "payment_failed_notified"}

    if event == "subscription.expired":
        provider_sub_id = str(subscription_data.get("id"))
        sub = repository.get_subscription_by_provider_id(session, provider_sub_id)
        if sub:
            sub.status = "suspended"
            sub.updated_at = datetime.now(timezone.utc)
            session.add(sub)
            
            state = repository.get_or_create_user_access_state(session, sub.telegram_user_id)
            repository.upgrade_access_tier(session, state, "free")
            
            session.commit()
            
            from app.billing.prompts import STATUS_SUBSCRIPTION_SUSPENDED_MESSAGE
            await send_telegram_message(sub.telegram_user_id, STATUS_SUBSCRIPTION_SUSPENDED_MESSAGE)
            
        return {"status": "ok", "message": "subscription_suspended"}

    return {"status": "ignored", "message": "unhandled_event"}


async def create_apipay_subscription(
    session: Session,
    *,
    telegram_user_id: int,
    phone_number: str,
) -> str:
    """Create a recurring subscription in ApiPay."""
    normalized_phone = normalize_phone_number(phone_number)
    client = ApiPayClient()
    amount_kzt = settings.PREMIUM_KZT_PRICE
    
    try:
        response = await client.create_subscription(
            amount=float(amount_kzt),
            phone_number=normalized_phone,
            description=f"Premium monthly subscription for {telegram_user_id}",
            external_subscriber_id=str(telegram_user_id),
        )
        
        repository.create_or_update_subscription(
            session,
            telegram_user_id=telegram_user_id,
            status="active", # or pending until first payment? ApiPay docs might clarify. 
            # Usually active after creation if immediate billing.
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            provider_type="apipay",
            provider_subscription_id=str(response.id),
        )
        session.commit()
        return f"Подписка на {amount_kzt} ₸ оформлена в Kaspi.kz."
    except Exception:
        logger.exception("Failed to create ApiPay subscription")
        return "Не удалось оформить подписку. Попробуйте позже."


async def cancel_apipay_subscription(
    session: Session,
    *,
    telegram_user_id: int,
) -> bool:
    """Cancel automated subscription in ApiPay."""
    sub = repository.get_subscription(session, telegram_user_id)
    if not sub or sub.provider_type != "apipay" or not sub.provider_subscription_id:
        return False
        
    client = ApiPayClient()
    try:
        success = await client.cancel_subscription(int(sub.provider_subscription_id))
        if success:
            sub.cancel_at_period_end = True
            sub.updated_at = datetime.now(timezone.utc)
            session.add(sub)
            session.commit()
        return success
    except Exception:
        logger.exception("Failed to cancel ApiPay subscription")
        return False

...
async def initiate_kaspi_payment(
    session: Session,
    *,
    telegram_user_id: int,
    phone_number: str,
) -> str:
    """
    Initiate a Kaspi payment via ApiPay.
    Returns the message to be sent to the user.
    """
    normalized_phone = normalize_phone_number(phone_number)
    
    # 1. Create client
    client = ApiPayClient()
    
    # 2. Generate local intent first
    intent_id = uuid.uuid4()
    amount_kzt = settings.PREMIUM_KZT_PRICE
    
    # 3. Create invoice in ApiPay
    try:
        invoice = await client.create_invoice(
            amount=float(amount_kzt),
            phone_number=normalized_phone,
            external_order_id=str(intent_id),
            description=f"Premium access for {telegram_user_id}",
        )
        
        # 4. Save to DB
        repository.create_purchase_intent(
            session,
            id=intent_id,
            telegram_user_id=telegram_user_id,
            invoice_payload=f"apipay_{invoice.id}",
            amount=amount_kzt,
            currency="KZT",
            provider_type="apipay",
            provider_invoice_id=str(invoice.id),
            phone_number=normalized_phone,
        )
        session.commit()
        
        return f"Счет на {amount_kzt} ₸ отправлен в ваше приложение Kaspi.kz. Пожалуйста, подтвердите его."
        
    except Exception as e:
        logger.exception("Failed to initiate ApiPay invoice for user_id=%s", telegram_user_id)
        from app.billing.prompts import PAYMENT_INITIATION_ERROR_MESSAGE
        return PAYMENT_INITIATION_ERROR_MESSAGE

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
    repository.mark_first_session_completed(session, state)
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
    return not user_access_state.first_session_completed


def build_paywall_response(
    user_access_state: UserAccessState,  # noqa: ARG001
) -> tuple[str, list[list[InlineButton]]]:
    """Return the paywall message for a user who hit the threshold."""
    from app.conversation.session_bootstrap import InlineButton

    buttons = [
        [InlineButton(text="Оплатить через Kaspi 🇰🇿", callback_data="pay:kaspi")],
    ]
    return PAYWALL_MESSAGE, buttons


@dataclass
class CancellationResult:
    was_premium: bool
    message: str
    action: str


async def process_cancellation_request(
    session: Session,
    *,
    telegram_user_id: int,
) -> CancellationResult:
    """Process a user's request to cancel their premium access.

    Access remains active until current_period_end.
    """
    subscription = repository.get_subscription(session, telegram_user_id)
    state = repository.get_or_create_user_access_state(session, telegram_user_id)

    if (subscription and subscription.status in ("active", "past_due")) or (state.access_tier == "premium"):
        if subscription:
            if subscription.provider_type == "apipay":
                # For ApiPay, we need to notify the provider to stop recurring billing
                await cancel_apipay_subscription(session, telegram_user_id=telegram_user_id)
            else:
                subscription.cancel_at_period_end = True
                session.add(subscription)
        else:
            # Fallback for legacy premium without subscription record
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


def build_status_response(
    session: Session,
    telegram_user_id: int,
) -> tuple[str, list[list[InlineButton]]]:
    from app.conversation.session_bootstrap import InlineButton

    subscription = check_and_update_subscription_status(session, telegram_user_id)
    user_access_state = repository.get_or_create_user_access_state(session, telegram_user_id)

    if subscription:
        if subscription.status == "active":
            date_str = subscription.current_period_end.strftime("%d.%m.%Y")
            return STATUS_SUBSCRIPTION_ACTIVE_MESSAGE.format(date=date_str), []

        if subscription.status == "past_due":
            from datetime import timedelta

            grace_end = subscription.current_period_end + timedelta(hours=24)
            remaining_hours = int(
                (grace_end - datetime.now(timezone.utc)).total_seconds() // 3600
            )
            remaining_hours = max(0, remaining_hours)
            return STATUS_SUBSCRIPTION_PAST_DUE_MESSAGE.format(hours=remaining_hours), [
                [InlineButton(text="Оплатить через Kaspi 🇰🇿", callback_data="pay:kaspi")]
            ]

        if subscription.status == "suspended":
            return STATUS_SUBSCRIPTION_SUSPENDED_MESSAGE, [
                [InlineButton(text="Оплатить через Kaspi 🇰🇿", callback_data="pay:kaspi")]
            ]

    if user_access_state.access_tier == "premium":
        return STATUS_PREMIUM_MESSAGE, []

    if is_free_eligible(user_access_state):
        return STATUS_FREE_ACTIVE_MESSAGE, []

    # Free tier, threshold reached
    return (
        STATUS_FREE_THRESHOLD_REACHED_MESSAGE,
        [[InlineButton(text="Оплатить через Kaspi 🇰🇿", callback_data="pay:kaspi")]],
    )


def check_and_update_subscription_status(
    session: Session, telegram_user_id: int
) -> Subscription | None:
    """Return current subscription. Read-only — status transitions happen via ApiPay webhooks."""
    return repository.get_subscription(session, telegram_user_id)


def has_premium_access(session: Session, telegram_user_id: int) -> bool:
    """Return True if the user has active or past_due subscription access."""
    subscription = check_and_update_subscription_status(session, telegram_user_id)
    if not subscription:
        # Fallback to access_tier check for legacy or manual cases
        state = repository.get_or_create_user_access_state(session, telegram_user_id)
        return state.access_tier == "premium"

    return subscription.status in ("active", "past_due")
