import pytest
from unittest.mock import patch

from sqlmodel import Session, select

from app.billing.prompts import (
    STATUS_ERROR_MESSAGE,
    STATUS_FREE_ACTIVE_MESSAGE,
    STATUS_FREE_THRESHOLD_REACHED_MESSAGE,
    STATUS_PREMIUM_MESSAGE,
    STATUS_SUBSCRIPTION_ACTIVE_MESSAGE,
    STATUS_SUBSCRIPTION_PAST_DUE_MESSAGE,
    STATUS_SUBSCRIPTION_SUSPENDED_MESSAGE,
)
...
@pytest.mark.anyio
async def test_status_command_subscription_active(db: Session) -> None:
    from datetime import datetime, timedelta, timezone
    from app.billing.repository import create_or_update_subscription
    user_id = 9910
    end_date = datetime.now(timezone.utc) + timedelta(days=10)
    create_or_update_subscription(db, telegram_user_id=user_id, status="active", current_period_end=end_date)
    db.commit()

    update = {"message": {"from": {"id": user_id}, "chat": {"id": user_id}, "text": "/status"}}
    resp = await handle_session_entry(db, update)
    
    expected = STATUS_SUBSCRIPTION_ACTIVE_MESSAGE.format(date=end_date.strftime("%d.%m.%Y"))
    assert resp.messages[0].text == expected

@pytest.mark.anyio
async def test_status_command_subscription_past_due(db: Session) -> None:
    from datetime import datetime, timedelta, timezone
    from app.billing.repository import create_or_update_subscription
    user_id = 9911
    # Simulate what grace_period_started webhook would set:
    # current_period_end = grace period end (23 hours from now)
    grace_end = datetime.now(timezone.utc) + timedelta(hours=23)
    create_or_update_subscription(db, telegram_user_id=user_id, status="past_due", current_period_end=grace_end)
    db.commit()

    update = {"message": {"from": {"id": user_id}, "chat": {"id": user_id}, "text": "/status"}}
    resp = await handle_session_entry(db, update)

    assert "Льготный период" in resp.messages[0].text
    import re
    assert re.search(r"\d+ ч\.", resp.messages[0].text)
    assert resp.inline_keyboard[0][0].callback_data == "pay:kaspi"

@pytest.mark.anyio
async def test_status_command_subscription_suspended(db: Session) -> None:
    from datetime import datetime, timedelta, timezone
    from app.billing.repository import create_or_update_subscription
    user_id = 9912
    create_or_update_subscription(db, telegram_user_id=user_id, status="suspended",
        current_period_end=datetime.now(timezone.utc) - timedelta(days=1))
    db.commit()

    update = {"message": {"from": {"id": user_id}, "chat": {"id": user_id}, "text": "/status"}}
    resp = await handle_session_entry(db, update)

    assert resp.messages[0].text == STATUS_SUBSCRIPTION_SUSPENDED_MESSAGE
    assert resp.inline_keyboard[0][0].callback_data == "pay:kaspi"


from app.billing.repository import get_or_create_user_access_state
from app.conversation.session_bootstrap import handle_session_entry
from app.models import SummaryGenerationSignal
from sqlalchemy import text

@pytest.fixture(autouse=True)
def clear_tables(db: Session):
    db.rollback()
    db.exec(text("DELETE FROM subscriptions"))
    db.exec(text("DELETE FROM user_access_states"))
    db.exec(text("DELETE FROM operator_alert"))
    db.exec(text("DELETE FROM summary_generation_signal"))
    db.exec(text("DELETE FROM telegram_session"))
    db.commit()


@pytest.mark.anyio
async def test_status_command_new_user(db: Session) -> None:
    user_id = 9901
    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": "/status",
        }
    }

    resp = await handle_session_entry(db, update)
    assert resp.action == "status_shown"
    assert resp.messages[0].text == STATUS_FREE_ACTIVE_MESSAGE
    assert resp.inline_keyboard == []


@pytest.mark.anyio
async def test_status_command_free_eligible(db: Session) -> None:
    user_id = 9902
    state = get_or_create_user_access_state(db, user_id)
    state.access_tier = "free"
    state.first_session_completed = False
    db.add(state)
    db.commit()

    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": "/status",
        }
    }

    resp = await handle_session_entry(db, update)
    assert resp.action == "status_shown"
    assert resp.messages[0].text == STATUS_FREE_ACTIVE_MESSAGE
    assert resp.inline_keyboard == []


@pytest.mark.anyio
async def test_status_command_free_threshold_reached(db: Session) -> None:
    import datetime
    user_id = 9903
    state = get_or_create_user_access_state(db, user_id)
    state.access_tier = "free"
    state.first_session_completed = True
    db.add(state)
    db.commit()

    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": "/status",
        }
    }

    resp = await handle_session_entry(db, update)
    assert resp.action == "status_shown"
    assert resp.messages[0].text == STATUS_FREE_THRESHOLD_REACHED_MESSAGE
    assert len(resp.inline_keyboard) == 1
    assert resp.inline_keyboard[0][0].callback_data == "pay:kaspi"
    assert "Kaspi" in resp.inline_keyboard[0][0].text


@pytest.mark.anyio
async def test_status_command_premium(db: Session) -> None:
    user_id = 9904
    state = get_or_create_user_access_state(db, user_id)
    state.access_tier = "premium"
    db.add(state)
    db.commit()

    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": "/status",
        }
    }

    resp = await handle_session_entry(db, update)
    assert resp.action == "status_shown"
    assert resp.messages[0].text == STATUS_PREMIUM_MESSAGE
    assert resp.inline_keyboard == []


@pytest.mark.anyio
async def test_status_command_db_error(db: Session) -> None:
    user_id = 9905
    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": "/status",
        }
    }

    with patch("app.conversation.session_bootstrap.build_status_response", side_effect=Exception("DB Error")):
        resp = await handle_session_entry(db, update)

    assert resp.action == "status_error"
    assert resp.messages[0].text == STATUS_ERROR_MESSAGE

    signal = db.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.telegram_user_id == user_id,
            SummaryGenerationSignal.signal_type == "billing_status_check_failed",
        )
    ).first()
    assert signal is not None
