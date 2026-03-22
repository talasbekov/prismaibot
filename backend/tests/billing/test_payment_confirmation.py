import pytest
from sqlmodel import Session

from app.billing.repository import get_or_create_user_access_state
from app.conversation.session_bootstrap import (
    IncomingMessage,
    _handle_message,
)


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
