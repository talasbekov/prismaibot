from unittest.mock import patch

import pytest
from sqlmodel import Session, select, text

from app.billing.models import UserAccessState, Subscription
from app.billing.prompts import (
    CANCEL_ERROR_MESSAGE,
    CANCEL_NO_ACTIVE_SUBSCRIPTION_MESSAGE,
    CANCEL_PREMIUM_SUCCESS_MESSAGE,
    STATUS_FREE_ACTIVE_MESSAGE,
)
from app.conversation.session_bootstrap import handle_session_entry
from app.models import SummaryGenerationSignal


@pytest.fixture
def clear_billing_tables(db: Session):
    db.rollback()
    db.exec(text("DELETE FROM user_access_states"))
    db.exec(text("DELETE FROM purchase_intents"))
    db.exec(text("DELETE FROM free_session_events"))
    db.exec(text("DELETE FROM summary_generation_signal"))
    db.exec(text("DELETE FROM operator_investigation"))
    db.exec(text("DELETE FROM operator_alert"))
    db.exec(text("DELETE FROM safety_signal"))
    db.exec(text("DELETE FROM profile_fact"))
    db.exec(text("DELETE FROM session_summary"))
    db.exec(text("DELETE FROM telegram_session"))
    db.commit()

@pytest.mark.anyio
async def test_cancel_command_premium_user(db: Session, clear_billing_tables):
    from datetime import datetime, timedelta, timezone
    from app.billing.repository import create_or_update_subscription
    # Setup premium user with subscription
    user_id = 12345
    chat_id = 67890
    
    end_date = datetime.now(timezone.utc) + timedelta(days=20)
    create_or_update_subscription(db, telegram_user_id=user_id, status="active", current_period_end=end_date)
    state = UserAccessState(telegram_user_id=user_id, access_tier="premium")
    db.add(state)
    db.commit()

    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": "/cancel"
        }
    }

    response = await handle_session_entry(db, update)

    assert response.status == "ok"
    assert response.action == "cancellation_accepted"
    assert response.messages[0].text == CANCEL_PREMIUM_SUCCESS_MESSAGE

    # Verify DB state - Access remains premium until period end
    db.expire_all()
    updated_state = db.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)
    ).one()
    assert updated_state.access_tier == "premium"
    
    sub = db.exec(select(Subscription).where(Subscription.telegram_user_id == user_id)).one()
    assert sub.cancel_at_period_end is True

@pytest.mark.anyio
async def test_cancel_command_with_subscription(db: Session, clear_billing_tables):
    from datetime import datetime, timedelta, timezone
    from app.billing.repository import create_or_update_subscription
    user_id = 5555
    chat_id = 6666
    
    # 1. Create active subscription
    end_date = datetime.now(timezone.utc) + timedelta(days=20)
    create_or_update_subscription(db, telegram_user_id=user_id, status="active", current_period_end=end_date)
    state = UserAccessState(telegram_user_id=user_id, access_tier="premium")
    db.add(state)
    db.commit()

    # 2. Cancel
    update = {"message": {"from": {"id": user_id}, "chat": {"id": chat_id}, "text": "/cancel"}}
    response = await handle_session_entry(db, update)

    assert response.action == "cancellation_accepted"
    
    # 3. Verify cancel_at_period_end is True
    db.expire_all()
    sub = db.exec(select(Subscription).where(Subscription.telegram_user_id == user_id)).one()
    assert sub.cancel_at_period_end is True
    
    # 4. Verify access_tier is STILL premium
    state = db.exec(select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)).one()
    assert state.access_tier == "premium"

    # Verify signal recorded
    signal = db.exec(
        select(SummaryGenerationSignal).where(SummaryGenerationSignal.signal_type == "billing_cancellation_request_received")
    ).first()
    assert signal is not None
    assert signal.telegram_user_id == user_id

@pytest.mark.anyio
async def test_cancel_command_free_user(db: Session, clear_billing_tables):
    # Setup free user
    user_id = 22345
    chat_id = 67890
    state = UserAccessState(telegram_user_id=user_id, access_tier="free")
    db.add(state)
    db.commit()

    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": "/cancel"
        }
    }

    response = await handle_session_entry(db, update)

    assert response.status == "ok"
    assert response.action == "no_active_subscription"
    assert response.messages[0].text == CANCEL_NO_ACTIVE_SUBSCRIPTION_MESSAGE

    # Verify DB state remains free
    db.expire_all()
    updated_state = db.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)
    ).one()
    assert updated_state.access_tier == "free"

@pytest.mark.anyio
async def test_cancel_command_new_user_no_db_record(db: Session, clear_billing_tables):
    # Setup: no existing UserAccessState for this user
    user_id = 99999
    chat_id = 88888

    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": "/cancel"
        }
    }

    response = await handle_session_entry(db, update)

    assert response.status == "ok"
    assert response.action == "no_active_subscription"

    # Verify DB record was created for UserAccessState (due to get_or_create) but it is "free"
    db.expire_all()
    state = db.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)
    ).first()
    assert state is not None
    assert state.access_tier == "free"

@pytest.mark.anyio
async def test_cancel_command_bypasses_safety_check(db: Session, clear_billing_tables):
    user_id = 32345
    chat_id = 67890

    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": "/cancel"
        }
    }

    # Patch evaluate_incoming_message_safety to raise if called
    with patch("app.conversation.session_bootstrap.evaluate_incoming_message_safety", side_effect=RuntimeError("Safety check should not be called")):
        response = await handle_session_entry(db, update)

    assert response.status == "ok"
    assert response.action == "no_active_subscription"

@pytest.mark.anyio
async def test_cancel_command_db_error(db: Session, clear_billing_tables):
    user_id = 42345
    chat_id = 67890

    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": "/cancel"
        }
    }

    with patch("app.conversation.session_bootstrap.process_cancellation_request", side_effect=Exception("DB Error")):
        response = await handle_session_entry(db, update)

    assert response.status == "error"
    assert response.action == "cancellation_error"
    assert response.messages[0].text == CANCEL_ERROR_MESSAGE

    # Verify failure signal recorded
    signal = db.exec(
        select(SummaryGenerationSignal).where(SummaryGenerationSignal.signal_type == "billing_cancellation_failed")
    ).first()
    assert signal is not None
    assert signal.telegram_user_id == user_id

@pytest.mark.anyio
async def test_cancel_consistency_with_status_command(db: Session, clear_billing_tables):
    from datetime import datetime, timedelta, timezone
    from app.billing.repository import create_or_update_subscription
    user_id = 12345
    chat_id = 67890
    
    # 1. Setup subscription
    end_date = datetime.now(timezone.utc) + timedelta(days=20)
    create_or_update_subscription(db, telegram_user_id=user_id, status="active", current_period_end=end_date)
    state = UserAccessState(telegram_user_id=user_id, access_tier="premium")
    db.add(state)
    db.commit()

    # 2. Cancel
    cancel_update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": "/cancel"
        }
    }
    await handle_session_entry(db, cancel_update)

    # 3. Check Status - Should still show active subscription (but cancelled auto-renewal)
    status_update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": "/status"
        }
    }
    response = await handle_session_entry(db, status_update)

    assert response.status == "ok"
    from app.billing.prompts import STATUS_SUBSCRIPTION_ACTIVE_MESSAGE
    expected = STATUS_SUBSCRIPTION_ACTIVE_MESSAGE.format(date=end_date.strftime("%d.%m.%Y"))
    assert response.messages[0].text == expected
