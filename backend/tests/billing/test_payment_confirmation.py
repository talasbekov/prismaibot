import datetime
import uuid
from unittest.mock import patch

import pytest
from sqlmodel import Session

from app.billing.repository import (
    create_purchase_intent,
    get_or_create_user_access_state,
)
from app.billing.service import confirm_payment_and_upgrade
from app.conversation.session_bootstrap import (
    IncomingMessage,
    _handle_message,
    handle_session_entry,
)


def test_confirm_payment_pending_intent(db: Session) -> None:
    test_uuid = str(uuid.uuid4())
    user_id = 1111
    state = get_or_create_user_access_state(db, user_id)
    db.commit()

    intent = create_purchase_intent(
        db,
        telegram_user_id=user_id,
        invoice_payload=f"val_{test_uuid}",
        amount=100,
    )
    db.commit()

    res = confirm_payment_and_upgrade(
        db,
        invoice_payload=f"val_{test_uuid}",
        telegram_payment_charge_id="charge_1",
        telegram_user_id=user_id,
    )
    db.commit()

    assert res.success is True
    assert res.already_completed is False
    assert res.signals == []

    db.refresh(intent)
    db.refresh(state)

    assert intent.status == "completed"
    assert intent.provider_payment_charge_id == "charge_1"
    assert state.access_tier == "premium"


def test_confirm_payment_already_completed(db: Session) -> None:
    test_uuid = str(uuid.uuid4())
    user_id = 2222
    state = get_or_create_user_access_state(db, user_id)
    db.commit()

    create_purchase_intent(
        db,
        telegram_user_id=user_id,
        invoice_payload=f"val_{test_uuid}",
        amount=100,
    )
    db.commit()

    # First call completes it
    confirm_payment_and_upgrade(
        db,
        invoice_payload=f"val_{test_uuid}",
        telegram_payment_charge_id="charge_1",
        telegram_user_id=user_id,
    )
    db.commit()

    # Second call is idempotent
    res = confirm_payment_and_upgrade(
        db,
        invoice_payload=f"val_{test_uuid}",
        telegram_payment_charge_id="charge_1",
        telegram_user_id=user_id,
    )
    db.commit()

    assert res.success is True
    assert res.already_completed is True
    assert res.signals == []

    db.refresh(state)
    assert state.access_tier == "premium"


def test_confirm_payment_orphan(db: Session) -> None:
    test_uuid = str(uuid.uuid4())
    user_id = 3333
    state = get_or_create_user_access_state(db, user_id)
    db.commit()

    # No intent was created

    res = confirm_payment_and_upgrade(
        db,
        invoice_payload=f"orphan_{test_uuid}",
        telegram_payment_charge_id="charge_2",
        telegram_user_id=user_id,
    )
    db.commit()

    assert res.success is True
    assert res.already_completed is False
    assert res.signals == ["billing_payment_intent_not_found"]

    db.refresh(state)
    assert state.access_tier == "premium"


@pytest.mark.anyio
async def test_handle_successful_payment(db: Session) -> None:
    test_uuid = str(uuid.uuid4())
    user_id = 4444
    create_purchase_intent(
        db,
        telegram_user_id=user_id,
        invoice_payload=f"val_{test_uuid}",
        amount=100,
    )
    db.commit()

    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": "whatever",
            "successful_payment": {
                "invoice_payload": f"val_{test_uuid}",
                "telegram_payment_charge_id": "charge_x",
                "total_amount": 100
            }
        }
    }

    resp = await handle_session_entry(db, update)
    assert resp.action == "payment_confirmed"
    assert resp.messages[0].text.startswith("Готово")

    # Db verify
    state = get_or_create_user_access_state(db, user_id)
    assert state.access_tier == "premium"

@pytest.mark.anyio
async def test_handle_successful_payment_duplicate(db: Session) -> None:
    test_uuid = str(uuid.uuid4())
    user_id = 5555
    create_purchase_intent(
        db, telegram_user_id=user_id, invoice_payload=f"val_{test_uuid}", amount=100
    )
    db.commit()

    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "successful_payment": {
                "invoice_payload": f"val_{test_uuid}",
                "telegram_payment_charge_id": "charge_x",
                "total_amount": 100
            }
        }
    }

    resp1 = await handle_session_entry(db, update)
    assert resp1.action == "payment_confirmed"

    resp2 = await handle_session_entry(db, update)
    assert resp2.action == "payment_confirmed"


@pytest.mark.anyio
async def test_handle_successful_payment_db_failure(db: Session) -> None:
    user_id = 6666
    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "successful_payment": {
                "invoice_payload": "some_payload",
                "telegram_payment_charge_id": "charge_y",
                "total_amount": 100
            }
        }
    }
    with patch("app.conversation.session_bootstrap.confirm_payment_and_upgrade", side_effect=Exception("DB Error")):
        resp = await handle_session_entry(db, update)

    assert resp.action == "payment_confirmation_error"
    assert resp.messages[0].text.startswith("Оплата")

@pytest.mark.anyio
async def test_paywall_gate_bypassed_for_premium(db: Session) -> None:
    user_id = 7777
    state = get_or_create_user_access_state(db, user_id)
    state.first_session_completed = True
    state.access_tier = "premium"
    db.add(state)
    db.commit()

    msg = IncomingMessage(telegram_user_id=user_id, chat_id=user_id, text="Hello")
    resp = await _handle_message(db, msg)
    assert resp.action != "paywall_gate"

@pytest.mark.anyio
async def test_paywall_gate_triggers_for_free(db: Session) -> None:
    user_id = 8888
    state = get_or_create_user_access_state(db, user_id)
    state.first_session_completed = True
    state.access_tier = "free"
    db.add(state)
    db.commit()

    msg = IncomingMessage(telegram_user_id=user_id, chat_id=user_id, text="Hello")
    resp = await _handle_message(db, msg)
    assert resp.action == "paywall_gate"
