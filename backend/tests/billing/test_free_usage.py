"""Tests for billing free-usage tracking (Story 4.1)."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, delete, select

from app.billing import repository, service
from app.billing.models import FreeSessionEvent, UserAccessState
from app.core.config import settings


@pytest.fixture(autouse=True)
def clear_billing_tables(db: Session) -> None:
    db.execute(delete(FreeSessionEvent))
    db.execute(delete(UserAccessState))
    db.commit()


# ---------------------------------------------------------------------------
# repository: get_or_create_user_access_state
# ---------------------------------------------------------------------------


def test_get_or_create_creates_new_record_with_defaults(db: Session) -> None:
    user_id = 80001
    state = repository.get_or_create_user_access_state(db, user_id)
    db.commit()
    db.refresh(state)

    assert state.telegram_user_id == user_id
    assert state.access_tier == "free"
    assert state.free_sessions_used == 0
    assert state.first_session_completed is False


def test_get_or_create_returns_existing_record_on_second_call(db: Session) -> None:
    user_id = 80002
    state1 = repository.get_or_create_user_access_state(db, user_id)
    db.commit()
    state2 = repository.get_or_create_user_access_state(db, user_id)
    assert state1.id == state2.id


# ---------------------------------------------------------------------------
# service: first call increments counter
# ---------------------------------------------------------------------------


def test_first_call_increments_free_sessions_used(db: Session) -> None:
    user_id = 80010
    session_id = uuid.uuid4()

    service.record_eligible_session_completion(
        db, telegram_user_id=user_id, session_id=session_id
    )
    db.commit()

    state = db.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)
    ).one()
    assert state.free_sessions_used == 1
    assert state.first_session_completed is True
    assert state.threshold_reached_at is not None


# ---------------------------------------------------------------------------
# service: idempotency
# ---------------------------------------------------------------------------


def test_idempotency_same_session_id_not_double_counted(db: Session) -> None:
    user_id = 80011
    session_id = uuid.uuid4()

    service.record_eligible_session_completion(
        db, telegram_user_id=user_id, session_id=session_id
    )
    db.commit()

    # Second call with the same session_id must be a no-op
    service.record_eligible_session_completion(
        db, telegram_user_id=user_id, session_id=session_id
    )
    db.commit()

    state = db.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)
    ).one()
    assert state.free_sessions_used == 1

    events = db.exec(
        select(FreeSessionEvent).where(FreeSessionEvent.session_id == session_id)
    ).all()
    assert len(events) == 1


# ---------------------------------------------------------------------------
# service: threshold crossing
# ---------------------------------------------------------------------------


def test_threshold_reached_at_set_when_counter_meets_threshold(db: Session) -> None:
    user_id = 80020
    threshold = settings.FREE_SESSION_THRESHOLD

    for _ in range(threshold):
        service.record_eligible_session_completion(
            db, telegram_user_id=user_id, session_id=uuid.uuid4()
        )
        db.commit()

    state = db.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)
    ).one()
    assert state.free_sessions_used == threshold
    assert state.threshold_reached_at is not None


def test_threshold_not_reached_one_below_limit(db: Session) -> None:
    user_id = 80021
    threshold = settings.FREE_SESSION_THRESHOLD

    # Ensure state exists even if loop runs 0 times
    repository.get_or_create_user_access_state(db, user_id)
    db.commit()

    for _ in range(threshold - 1):
        service.record_eligible_session_completion(
            db, telegram_user_id=user_id, session_id=uuid.uuid4()
        )
        db.commit()

    state = db.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)
    ).one()
    assert state.free_sessions_used == threshold - 1
    assert state.first_session_completed is False


# ---------------------------------------------------------------------------
# service: is_free_eligible
# ---------------------------------------------------------------------------


def test_is_free_eligible_true_before_threshold(db: Session) -> None:
    user_id = 80030
    state = repository.get_or_create_user_access_state(db, user_id)
    db.commit()
    assert service.is_free_eligible(state) is True


def test_is_free_eligible_false_after_threshold_reached(db: Session) -> None:
    user_id = 80031
    for _ in range(settings.FREE_SESSION_THRESHOLD):
        service.record_eligible_session_completion(
            db, telegram_user_id=user_id, session_id=uuid.uuid4()
        )
        db.commit()

    state = db.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)
    ).one()
    assert service.is_free_eligible(state) is False


# ---------------------------------------------------------------------------
# session_bootstrap integration: billing call at session closure
# ---------------------------------------------------------------------------


def _clear_session_tables(db: Session) -> None:
    """Delete all tables with FK deps on telegram_session, then telegram_session itself."""
    from app.models import (
        OperatorAlert,
        OperatorInvestigation,
        ProfileFact,
        SafetySignal,
        SessionSummary,
        SummaryGenerationSignal,
        TelegramSession,
    )

    db.execute(delete(SummaryGenerationSignal))
    db.execute(delete(OperatorInvestigation))
    db.execute(delete(OperatorAlert))
    db.execute(delete(SafetySignal))
    db.execute(delete(ProfileFact))
    db.execute(delete(SessionSummary))
    db.execute(delete(TelegramSession))
    db.commit()


@pytest.mark.anyio
async def test_session_closure_triggers_free_usage_recording(db: Session) -> None:
    """Closing a session must create a FreeSessionEvent and increment the counter."""
    from app.conversation.closure import ClosureResponse
    from app.conversation.session_bootstrap import IncomingMessage, _handle_message
    from app.models import TelegramSession
    from app.safety.service import SafetyAssessment

    _clear_session_tables(db)

    user_id = 80040
    chat_id = 28040

    # Pre-create a session at the closure threshold so the next message triggers closure
    session_record = TelegramSession(
        telegram_user_id=user_id,
        chat_id=chat_id,
        status="active",
        turn_count=settings.CONVERSATION_CLOSURE_MIN_TURN_COUNT,
        working_context="Мы поссорились, и я не понимаю, как быть дальше.",
    )
    db.add(session_record)
    db.commit()

    message = IncomingMessage(
        telegram_user_id=user_id,
        chat_id=chat_id,
        text="Если подвести итог — я просто хочу, чтобы меня слышали.",
    )

    mock_safety = SafetyAssessment(
        classification="safe",
        trigger_category="none",
        confidence="low",
        blocks_normal_flow=False,
    )
    mock_closure = ClosureResponse(
        messages=("Спасибо, что поделился. Держи следующий шаг.",),
        next_steps=("Поговори с близким человеком",),
        takeaway="Пользователь хочет, чтобы его слышали.",
    )

    with (
        patch(
            "app.conversation.session_bootstrap.evaluate_incoming_message_safety",
            return_value=mock_safety,
        ),
        patch(
            "app.conversation.closure.compose_session_closure",
            return_value=mock_closure,
        ),
        patch(
            "app.conversation.session_bootstrap.schedule_session_summary_generation"
        ),
        patch(
            "app.memory.derive_allowed_profile_facts",
            return_value=[],
        ),
    ):
        await _handle_message(db, message)

    state = db.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)
    ).first()
    assert state is not None, "UserAccessState must be created after session closure"
    assert state.free_sessions_used == 1
    assert state.first_session_completed is True


@pytest.mark.anyio
async def test_non_closing_turn_does_not_trigger_billing(db: Session) -> None:
    """A turn that does not close the session must NOT create a FreeSessionEvent."""
    from app.conversation.first_response import FirstTrustResponse
    from app.conversation.session_bootstrap import IncomingMessage, _handle_message
    from app.models import TelegramSession
    from app.safety.service import SafetyAssessment

    _clear_session_tables(db)

    user_id = 80041
    chat_id = 28041

    # Session with turn_count == 0: next message is first-turn path (not closure)
    session_record = TelegramSession(
        telegram_user_id=user_id,
        chat_id=chat_id,
        status="active",
        turn_count=0,
    )
    db.add(session_record)
    db.commit()

    message = IncomingMessage(
        telegram_user_id=user_id,
        chat_id=chat_id,
        text="Мы снова поссорились, и я не понимаю, что делать.",
    )

    mock_safety = SafetyAssessment(
        classification="safe",
        trigger_category="none",
        confidence="low",
        blocks_normal_flow=False,
    )
    mock_first = FirstTrustResponse(
        messages=("Расскажи подробнее, что происходит.",),
    )

    with (
        patch(
            "app.conversation.session_bootstrap.evaluate_incoming_message_safety",
            return_value=mock_safety,
        ),
        patch(
            "app.conversation.first_response.compose_first_trust_response_with_memory",
            return_value=mock_first,
        ),
        patch(
            "app.conversation.session_bootstrap._safe_load_prior_memory_context",
            return_value=None,
        ),
        patch(
            "app.conversation.session_bootstrap._merge_context_for_session",
            return_value="context",
        ),
    ):
        await _handle_message(db, message)

    state = db.exec(
        select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)
    ).first()
    assert state is None or state.free_sessions_used == 0


# ---------------------------------------------------------------------------
# Failure path: billing error is non-blocking, ops signal is recorded
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_billing_failure_records_ops_signal_and_does_not_raise(db: Session) -> None:
    """If record_eligible_session_completion raises, session closure still succeeds
    and an ops signal of type 'billing_free_usage_record_failed' is recorded."""
    from app.conversation.closure import ClosureResponse
    from app.conversation.session_bootstrap import IncomingMessage, _handle_message
    from app.models import SummaryGenerationSignal, TelegramSession
    from app.safety.service import SafetyAssessment

    _clear_session_tables(db)

    user_id = 80050
    chat_id = 28050

    session_record = TelegramSession(
        telegram_user_id=user_id,
        chat_id=chat_id,
        status="active",
        turn_count=settings.CONVERSATION_CLOSURE_MIN_TURN_COUNT,
        working_context="Контекст предыдущего разговора.",
    )
    db.add(session_record)
    db.commit()

    message = IncomingMessage(
        telegram_user_id=user_id,
        chat_id=chat_id,
        text="Если подвести итог — я хочу просто чтобы меня слышали.",
    )

    mock_safety = SafetyAssessment(
        classification="safe",
        trigger_category="none",
        confidence="low",
        blocks_normal_flow=False,
    )
    mock_closure = ClosureResponse(
        messages=("Спасибо, что поделился.",),
        next_steps=("Поговори с близким",),
        takeaway="Пользователь хочет быть услышан.",
    )

    with (
        patch(
            "app.conversation.session_bootstrap.evaluate_incoming_message_safety",
            return_value=mock_safety,
        ),
        patch(
            "app.conversation.closure.compose_session_closure",
            return_value=mock_closure,
        ),
        patch(
            "app.conversation.session_bootstrap.schedule_session_summary_generation"
        ),
        patch(
            "app.memory.derive_allowed_profile_facts",
            return_value=[],
        ),
        patch(
            "app.conversation.session_bootstrap.record_eligible_session_completion",
            side_effect=RuntimeError("simulated billing DB failure"),
        ),
    ):
        result = await _handle_message(db, message, background_tasks=MagicMock())

    # Session closure must succeed despite billing failure
    assert result is not None
    assert result.status == "ok"

    signal = db.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.telegram_user_id == user_id
        )
    ).first()
    assert signal is not None
    assert signal.signal_type == "billing_free_usage_record_failed"
