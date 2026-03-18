"""Tests for billing paywall gate (Story 4.2)."""

import re
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, delete, select

from app.billing.models import UserAccessState
from app.billing.prompts import PAYWALL_MESSAGE
from app.conversation.session_bootstrap import IncomingMessage, _handle_message
from app.models import (
    DeletionRequest,
    OperatorAlert,
    OperatorInvestigation,
    PeriodicInsight,
    ProfileFact,
    SafetySignal,
    SessionSummary,
    SummaryGenerationSignal,
    TelegramSession,
)
from app.safety.service import SafetyAssessment


@pytest.fixture(autouse=True)
def clear_billing_tables(db: Session) -> None:
    db.exec(delete(UserAccessState))
    db.exec(delete(OperatorInvestigation))
    db.exec(delete(OperatorAlert))
    db.exec(delete(SummaryGenerationSignal))
    db.exec(delete(SafetySignal))
    db.exec(delete(ProfileFact))
    db.exec(delete(SessionSummary))
    db.exec(delete(PeriodicInsight))
    db.exec(delete(DeletionRequest))
    db.exec(delete(TelegramSession))
    db.commit()


def test_paywall_message_contract() -> None:
    """Paywall message must NOT contain standalone digit strings representing session counts."""
    # A simple regex for standalone digits.
    # e.g. "3", "5", "10". This verifies the continuity-based framing rule.
    assert not bool(re.search(r'\b\d+\b', PAYWALL_MESSAGE)), "Message should not contain raw counts"
    assert "premium" in PAYWALL_MESSAGE.lower()


@pytest.mark.anyio
async def test_paywall_gate_triggers_on_threshold_reached(db: Session) -> None:
    """User with threshold_reached_at set gets the paywall and no evaluation."""
    user_id = 90001
    chat_id = 29001

    db.add(UserAccessState(
        telegram_user_id=user_id,
        access_tier="free",
        first_session_completed=True,
    ))
    db.commit()

    message = IncomingMessage(
        telegram_user_id=user_id,
        chat_id=chat_id,
        text="Привет, начну новую сессию.",
    )

    with patch(
        "app.conversation.session_bootstrap.evaluate_incoming_message_safety"
    ) as mock_safety:
        result = await _handle_message(db, message, background_tasks=MagicMock())

    assert result.action == "paywall_gate"
    assert "paywall_shown" in result.signals
    assert result.messages[0].text == PAYWALL_MESSAGE
    mock_safety.assert_not_called()

    session_record = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).first()
    assert session_record is not None
    assert session_record.last_user_message == "Привет, начну новую сессию."


@pytest.mark.anyio
async def test_paywall_gate_bypassed_in_crisis_state(db: Session) -> None:
    """If crisis_state='crisis_active', billing gate is bypassed completely."""
    user_id = 90002
    chat_id = 29002

    db.add(UserAccessState(
        telegram_user_id=user_id,
        access_tier="free",
        first_session_completed=True,
    ))

    session_record = TelegramSession(
        telegram_user_id=user_id,
        chat_id=chat_id,
        status="active",
        crisis_state="crisis_active",
        turn_count=2,
    )
    db.add(session_record)
    db.commit()

    message = IncomingMessage(
        telegram_user_id=user_id,
        chat_id=chat_id,
        text="Мне плохо",
    )

    mock_safety = SafetyAssessment(
        classification="crisis",
        trigger_category="self_harm",
        confidence="high",
        blocks_normal_flow=True,
    )

    with (
        patch("app.conversation.session_bootstrap.evaluate_incoming_message_safety", return_value=mock_safety),
        patch("app.conversation.session_bootstrap.create_and_deliver_operator_alert"),
    ):
        result = await _handle_message(db, message, background_tasks=MagicMock())

    assert result.action != "paywall_gate"
    assert "paywall_shown" not in result.signals
    assert "crisis_mode_active" in result.signals


@pytest.mark.anyio
async def test_paywall_gate_bypassed_when_threshold_not_reached(db: Session) -> None:
    """User with threshold_reached_at=None proceeds to normal flow."""
    user_id = 90003
    chat_id = 29003

    db.add(UserAccessState(
        telegram_user_id=user_id,
        access_tier="free",
        free_sessions_used=1,
        threshold_reached_at=None,
    ))
    db.commit()

    message = IncomingMessage(
        telegram_user_id=user_id,
        chat_id=chat_id,
        text="Начну сессию",
    )

    mock_safety = SafetyAssessment(
        classification="safe",
        trigger_category="none",
        confidence="low",
        blocks_normal_flow=False,
    )

    with (
        patch("app.conversation.session_bootstrap.evaluate_incoming_message_safety", return_value=mock_safety),
        patch("app.conversation.first_response.compose_first_trust_response_with_memory") as mock_first_resp,
        patch("app.conversation.session_bootstrap._safe_load_prior_memory_context", return_value=None),
        patch("app.conversation.session_bootstrap._merge_context_for_session", return_value="context"),
    ):
        from app.conversation.first_response import FirstTrustResponse
        mock_first_resp.return_value = FirstTrustResponse(messages=("Привет",))
        result = await _handle_message(db, message, background_tasks=MagicMock())

    assert result.action != "paywall_gate"
    assert "paywall_shown" not in result.signals


@pytest.mark.anyio
async def test_billing_access_check_fails_open(db: Session) -> None:
    """If get_user_access_state raises, fall through to normal flow and record signal."""
    user_id = 90004
    chat_id = 29004

    message = IncomingMessage(
        telegram_user_id=user_id,
        chat_id=chat_id,
        text="Начну сессию",
    )

    mock_safety = SafetyAssessment(
        classification="safe",
        trigger_category="none",
        confidence="low",
        blocks_normal_flow=False,
    )

    with (
        patch("app.conversation.session_bootstrap.get_user_access_state", side_effect=ValueError("DB drop")),
        patch("app.conversation.session_bootstrap.evaluate_incoming_message_safety", return_value=mock_safety),
        patch("app.conversation.first_response.compose_first_trust_response_with_memory") as mock_first_resp,
        patch("app.conversation.session_bootstrap._safe_load_prior_memory_context", return_value=None),
        patch("app.conversation.session_bootstrap._merge_context_for_session", return_value="context"),
    ):
        from app.conversation.first_response import FirstTrustResponse
        mock_first_resp.return_value = FirstTrustResponse(messages=("Привет",))
        result = await _handle_message(db, message, background_tasks=MagicMock())

    assert result.action != "paywall_gate"

    # Check that ops signal was recorded
    signal = db.exec(
        select(SummaryGenerationSignal).where(SummaryGenerationSignal.telegram_user_id == user_id)
    ).first()
    assert signal is not None
    assert signal.signal_type == "billing_access_check_failed"

