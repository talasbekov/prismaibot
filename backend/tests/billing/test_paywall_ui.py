import pytest
from sqlmodel import Session
from app.billing.service import build_paywall_response, is_free_eligible
from app.billing.models import UserAccessState
from app.billing.prompts import PAYWALL_MESSAGE
from app.conversation.session_bootstrap import IncomingMessage, _handle_message, TelegramSession
from unittest.mock import MagicMock, patch

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

def test_paywall_message_content():
    """Verify that paywall message contains required keywords."""
    # AC1: Contains 'безлимит'
    assert "безлимит" in PAYWALL_MESSAGE.lower()
    # AC3: Structured Warmth (no aggressive selling, partnership tone)
    assert "продолжить начатое" in PAYWALL_MESSAGE
    assert "опираясь на уже достигнутое" in PAYWALL_MESSAGE

def test_build_paywall_response_ui():
    """Verify that build_paywall_response returns text and button."""
    state = UserAccessState(telegram_user_id=123, first_session_completed=True)
    text, keyboard = build_paywall_response(state)
    
    # AC5: Returns tuple (text, keyboard)
    assert isinstance(text, str)
    assert isinstance(keyboard, list)
    
    # AC2: Contains 'Оформить premium' button with 'pay:stars'
    found_button = False
    for row in keyboard:
        for button in row:
            if "Оформить Premium" in button.text and button.callback_data == "pay:stars":
                found_button = True
    assert found_button, "Paywall must contain payment button"

@pytest.mark.anyio
async def test_paywall_gate_ui_integration(db: Session):
    """Verify that the gate in _handle_message returns the UI components."""
    user_id = 12345
    db.add(UserAccessState(telegram_user_id=user_id, first_session_completed=True, access_tier="free"))
    db.commit()
    
    msg = IncomingMessage(telegram_user_id=user_id, chat_id=user_id, text="Hello, I want to start a session.")
    
    assessment = SafetyAssessment(
        classification="safe",
        trigger_category="none",
        confidence="high",
        blocks_normal_flow=False
    )
    
    # We mock evaluate_incoming_message_safety to ensure it returns valid data
    with patch("app.conversation.session_bootstrap.evaluate_incoming_message_safety", return_value=assessment) as mock_safety:
        resp = await _handle_message(db, msg)
        
        assert resp.action == "paywall_gate"
        assert "paywall_shown" in resp.signals
        assert resp.inline_keyboard is not None
        assert any("pay:stars" == btn.callback_data for row in resp.inline_keyboard for btn in row)
        # Note: In the actual code, the billing gate is BEFORE safety assessment.
        # But we mock it anyway to be safe and avoid adaptation errors if it were called.

from app.safety.service import SafetyAssessment

@pytest.mark.anyio
async def test_crisis_bypasses_paywall_ui(db: Session):
    """Verify that crisis session does NOT show paywall UI even if threshold reached."""
    user_id = 54321
    db.add(UserAccessState(telegram_user_id=user_id, first_session_completed=True, access_tier="free"))
    # Create active crisis session
    session_record = TelegramSession(
        telegram_user_id=user_id,
        chat_id=user_id,
        crisis_state="crisis_active"
    )
    db.add(session_record)
    db.commit()
    
    msg = IncomingMessage(telegram_user_id=user_id, chat_id=user_id, text="Help me")
    
    assessment = SafetyAssessment(
        classification="crisis",
        trigger_category="self_harm",
        confidence="high",
        blocks_normal_flow=True
    )
    
    with (
        patch("app.conversation.session_bootstrap.evaluate_incoming_message_safety", return_value=assessment),
        patch("app.conversation.session_bootstrap._compose_crisis_routing_response") as mock_crisis,
        patch("app.conversation.session_bootstrap.create_and_deliver_operator_alert")
    ):
        mock_crisis.return_value.messages = ["Crisis Help"]
        mock_crisis.return_value.action = "crisis_response"
        
        resp = await _handle_message(db, msg)
        
        # AC4: Paywall MUST NOT be displayed in crisis
        assert resp.action != "paywall_gate"
        assert "paywall_shown" not in resp.signals
