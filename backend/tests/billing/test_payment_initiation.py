"""Tests for payment initiation flow."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete

from app.billing.models import PurchaseIntent
from app.billing.prompts import PAYWALL_MESSAGE
from app.billing.models import UserAccessState
from app.conversation.session_bootstrap import IncomingMessage, _handle_message
from app.models import SummaryGenerationSignal, TelegramSession


@pytest.fixture(autouse=True)
def clear_billing_tables(db: Session) -> None:
    db.execute(delete(PurchaseIntent))
    db.execute(delete(SummaryGenerationSignal))
    db.execute(delete(TelegramSession))
    db.commit()


def test_purchase_intent_duplicate_invoice_payload_raises(db: Session) -> None:
    """Duplicate invoice_payload should trigger unique constraint."""
    db.add(PurchaseIntent(
        telegram_user_id=111,
        invoice_payload="apipay_test",
        amount=3000,
    ))
    db.commit()

    db.add(PurchaseIntent(
        telegram_user_id=222,
        invoice_payload="apipay_test",
        amount=3000,
    ))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.anyio
async def test_paywall_gate_includes_inline_keyboard(db: Session) -> None:
    """Paywall response should include inline keyboard with Kaspi button."""
    user_id = 10001
    chat_id = 30001

    db.add(UserAccessState(
        telegram_user_id=user_id,
        access_tier="free",
        first_session_completed=True,
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
        result = await _handle_message(db, message, background_tasks=MagicMock())

    assert result.action == "paywall_gate"
    assert result.inline_keyboard is not None
    assert len(result.inline_keyboard) == 1
    assert result.inline_keyboard[0][0].callback_data == "pay:kaspi"
