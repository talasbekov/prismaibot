"""Tests for payment initiation flow (Story 4.3)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

from app.billing.models import PurchaseIntent
from app.billing.prompts import PAYMENT_INITIATION_ERROR_MESSAGE
from app.billing.service import get_or_create_purchase_intent
from app.conversation.session_bootstrap import handle_session_entry
from app.core.config import settings
from app.models import SummaryGenerationSignal, TelegramSession


@pytest.fixture(autouse=True)
def clear_billing_tables(db: Session) -> None:
    db.execute(delete(PurchaseIntent))
    db.execute(delete(SummaryGenerationSignal))
    db.execute(delete(TelegramSession))
    db.commit()


def test_get_or_create_purchase_intent_new_intent(db: Session) -> None:
    """It creates a new intent when none exists."""
    user_id = 12345
    intent = get_or_create_purchase_intent(db, user_id)
    db.commit()

    assert intent.telegram_user_id == user_id
    assert intent.invoice_payload == f"premium_{user_id}"
    assert intent.amount == settings.PREMIUM_STARS_PRICE
    assert intent.currency == "XTR"
    assert intent.status == "pending"

    # Verify DB persistence
    db_intent = db.exec(
        select(PurchaseIntent).where(PurchaseIntent.telegram_user_id == user_id)
    ).first()
    assert db_intent is not None
    assert db_intent.id == intent.id


def test_get_or_create_purchase_intent_idempotent(db: Session) -> None:
    """It returns the existing pending intent."""
    user_id = 54321
    intent1 = get_or_create_purchase_intent(db, user_id)
    db.commit()

    intent2 = get_or_create_purchase_intent(db, user_id)
    db.commit()

    assert intent1.id == intent2.id

    intents = db.exec(
        select(PurchaseIntent).where(PurchaseIntent.telegram_user_id == user_id)
    ).all()
    assert len(intents) == 1


def test_purchase_intent_duplicate_invoice_payload_raises(db: Session) -> None:
    """Duplicate invoice_payload should trigger unique constraint."""
    db.add(PurchaseIntent(
        telegram_user_id=111,
        invoice_payload="premium_test",
        amount=1,
    ))
    db.commit()

    db.add(PurchaseIntent(
        telegram_user_id=222,
        invoice_payload="premium_test",
        amount=1,
    ))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_pay_stars_callback_triggers_payment_invoice(db: Session) -> None:
    """pay:stars callback data should initiate a payment."""
    user_id = 777
    chat_id = 888

    update = {
        "callback_query": {
            "from": {"id": user_id},
            "message": {"chat": {"id": chat_id}},
            "data": "pay:stars",
        }
    }

    result = handle_session_entry(db, update)

    assert result.action == "payment_invoice"
    assert "send_invoice" in result.signals
    assert result.invoice is not None
    assert result.invoice.payload == f"premium_{user_id}"
    assert result.invoice.chat_id == chat_id
    assert result.invoice.currency == "XTR"
    assert len(result.invoice.prices) == 1
    assert result.invoice.prices[0]["amount"] == settings.PREMIUM_STARS_PRICE


def test_pay_stars_callback_handles_failure(db: Session) -> None:
    """If creation fails, it returns a fail-visible message open access state and drops signal."""
    user_id = 999
    chat_id = 111

    update = {
        "callback_query": {
            "from": {"id": user_id},
            "message": {"chat": {"id": chat_id}},
            "data": "pay:stars",
        }
    }

    with patch("app.conversation.session_bootstrap.get_or_create_purchase_intent", side_effect=Exception("DB Error")):
        result = handle_session_entry(db, update)

    assert result.action == "payment_invoice_error"
    assert result.messages[0].text == PAYMENT_INITIATION_ERROR_MESSAGE

    signal = db.exec(
        select(SummaryGenerationSignal).where(SummaryGenerationSignal.telegram_user_id == user_id)
    ).first()
    assert signal is not None
    assert signal.signal_type == "billing_invoice_creation_failed"


def test_pre_checkout_query_returns_ok(db: Session) -> None:
    """pre_checkout_query should return pre_checkout_ok action."""
    query_id = "test_query_123"
    update = {
        "pre_checkout_query": {
            "id": query_id,
            "from": {"id": 123},
            "currency": "XTR",
            "total_amount": 1,
            "invoice_payload": "premium_123",
        }
    }

    result = handle_session_entry(db, update)

    assert result.action == "pre_checkout_ok"
    assert "answer_pre_checkout" in result.signals
    assert result.pre_checkout_query_id == query_id


def test_paywall_gate_includes_inline_keyboard(db: Session) -> None:
    """Paywall response should include inline keyboard."""
    from app.billing.models import UserAccessState
    from app.conversation.session_bootstrap import IncomingMessage, _handle_message
    user_id = 10001
    chat_id = 30001

    db.add(UserAccessState(
        telegram_user_id=user_id,
        access_tier="free",
        free_sessions_used=3,
        threshold_reached_at=datetime.now(timezone.utc),
    ))
    db.commit()

    message = IncomingMessage(
        telegram_user_id=user_id,
        chat_id=chat_id,
        text="Начну сессию.",
    )

    with patch(
        "app.conversation.session_bootstrap.evaluate_incoming_message_safety"
    ):
        result = _handle_message(db, message, background_tasks=MagicMock())

    assert result.action == "paywall_gate"
    assert result.inline_keyboard is not None
    assert len(result.inline_keyboard) == 1
    assert result.inline_keyboard[0][0].callback_data == "pay:stars"


def test_access_tier_remains_free_after_payment_initiation(db: Session) -> None:
    """After pay:stars callback, UserAccessState.access_tier must still be 'free'.
    No premature access upgrade should occur at initiation time."""
    from app.billing.models import UserAccessState

    user_id = 10099
    chat_id = 30099

    # Set up a user who has hit the threshold (paywall eligible)
    db.add(UserAccessState(
        telegram_user_id=user_id,
        access_tier="free",
        free_sessions_used=3,
        threshold_reached_at=datetime(2026, 3, 14, tzinfo=timezone.utc),
    ))
    db.commit()

    update = {
        "callback_query": {
            "from": {"id": user_id},
            "message": {"chat": {"id": chat_id}},
            "data": "pay:stars",
        }
    }

    result = handle_session_entry(db, update)
    assert result.action == "payment_invoice"

    # Verify access_tier is still "free" — no premature upgrade
    state = db.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)
    ).first()
    assert state is not None
    assert state.access_tier == "free"
