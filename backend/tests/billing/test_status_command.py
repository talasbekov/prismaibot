from unittest.mock import patch

from sqlmodel import Session, select

from app.billing.prompts import (
    STATUS_ERROR_MESSAGE,
    STATUS_FREE_ACTIVE_MESSAGE,
    STATUS_FREE_THRESHOLD_REACHED_MESSAGE,
    STATUS_PREMIUM_MESSAGE,
)
from app.billing.repository import get_or_create_user_access_state
from app.conversation.session_bootstrap import handle_session_entry
from app.models import SummaryGenerationSignal


def test_status_command_new_user(db: Session) -> None:
    user_id = 9901
    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": "/status",
        }
    }

    resp = handle_session_entry(db, update)
    assert resp.action == "status_shown"
    assert resp.messages[0].text == STATUS_FREE_ACTIVE_MESSAGE
    assert resp.inline_keyboard == []


def test_status_command_free_eligible(db: Session) -> None:
    user_id = 9902
    state = get_or_create_user_access_state(db, user_id)
    state.access_tier = "free"
    state.threshold_reached_at = None
    db.add(state)
    db.commit()

    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": "/status",
        }
    }

    resp = handle_session_entry(db, update)
    assert resp.action == "status_shown"
    assert resp.messages[0].text == STATUS_FREE_ACTIVE_MESSAGE
    assert resp.inline_keyboard == []


def test_status_command_free_threshold_reached(db: Session) -> None:
    import datetime
    user_id = 9903
    state = get_or_create_user_access_state(db, user_id)
    state.access_tier = "free"
    state.threshold_reached_at = datetime.datetime.now(datetime.timezone.utc)
    db.add(state)
    db.commit()

    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": "/status",
        }
    }

    resp = handle_session_entry(db, update)
    assert resp.action == "status_shown"
    assert resp.messages[0].text == STATUS_FREE_THRESHOLD_REACHED_MESSAGE
    assert len(resp.inline_keyboard) == 1
    assert resp.inline_keyboard[0][0].callback_data == "pay:stars"


def test_status_command_premium(db: Session) -> None:
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

    resp = handle_session_entry(db, update)
    assert resp.action == "status_shown"
    assert resp.messages[0].text == STATUS_PREMIUM_MESSAGE
    assert resp.inline_keyboard == []


def test_status_command_db_error(db: Session) -> None:
    user_id = 9905
    update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": "/status",
        }
    }

    with patch("app.conversation.session_bootstrap.get_user_access_state", side_effect=Exception("DB Error")):
        resp = handle_session_entry(db, update)

    assert resp.action == "status_error"
    assert resp.messages[0].text == STATUS_ERROR_MESSAGE

    signal = db.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.telegram_user_id == user_id,
            SummaryGenerationSignal.signal_type == "billing_status_check_failed",
        )
    ).first()
    assert signal is not None
