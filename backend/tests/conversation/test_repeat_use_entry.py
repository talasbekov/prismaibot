from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.conversation.session_bootstrap import (
    OPENING_PROMPT,
    RETURNING_USER_OPENING_PROMPT,
)
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


@pytest.fixture(autouse=True)
def clear_db(db: Session) -> None:
    db.execute(delete(SummaryGenerationSignal))
    db.execute(delete(OperatorInvestigation))
    db.execute(delete(OperatorAlert))
    db.execute(delete(SafetySignal))
    db.execute(delete(ProfileFact))
    db.execute(delete(SessionSummary))
    db.execute(delete(PeriodicInsight))
    db.execute(delete(DeletionRequest))
    db.execute(delete(TelegramSession))
    db.commit()

def test_new_user_gets_generic_opening(client: TestClient) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 1,
                "text": "/start",
                "chat": {"id": 2001, "type": "private"},
                "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "opening_prompt"
    
    # New user gets OPENING_PROMPT
    expected_text = OPENING_PROMPT
    assert payload["messages"][0]["text"] == expected_text

    # Verify both buttons exist with new brainstorm:mode:* callback data
    callback_datas = [btn["callback_data"] for btn in payload["inline_keyboard"][0]]
    assert "brainstorm:mode:reflect" in callback_datas
    assert "brainstorm:mode:brainstorm" in callback_datas

def test_returning_user_gets_continuity_aware_opening(client: TestClient, db: Session) -> None:
    # Arrange: create a session summary to simulate returning user
    user_id = 9001

    # SessionSummary needs a valid session_id from telegram_session table
    old_session = TelegramSession(
        id=uuid4(),
        telegram_user_id=user_id,
        chat_id=3001,
        status="completed",
        reflective_mode="fast"
    )
    db.add(old_session)
    db.commit()

    summary = SessionSummary(
        session_id=old_session.id,
        telegram_user_id=user_id,
        reflective_mode="fast",
        source_turn_count=5,
        takeaway="Пользователь разобрался с ситуацией.",
        key_facts=["Повторяющийся паттерн напряжения."],
        emotional_tensions=[],
        uncertainty_notes=[],
        next_step_context=[],
        retention_scope="durable_summary",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(summary)
    db.commit()

    # Act: /start
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 2,
                "text": "/start",
                "chat": {"id": 3001, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Bratan"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "opening_prompt"
    assert payload["messages"][0]["text"] == RETURNING_USER_OPENING_PROMPT

    # Verify both buttons exist for returning user too
    callback_datas = [btn["callback_data"] for btn in payload["inline_keyboard"][0]]
    assert "brainstorm:mode:reflect" in callback_datas
    assert "brainstorm:mode:brainstorm" in callback_datas

def test_error_checking_prior_sessions_fallback_to_generic(client: TestClient, db: Session, monkeypatch) -> None:
    from app.conversation import session_bootstrap

    def mock_has_prior(*args, **kwargs):
        raise Exception("DB error")

    monkeypatch.setattr(session_bootstrap, "_has_prior_sessions", mock_has_prior)

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 3,
                "text": "/start",
                "chat": {"id": 4001, "type": "private"},
                "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "opening_prompt"
    
    # Fallback uses generic opening
    expected_text = OPENING_PROMPT
    assert payload["messages"][0]["text"] == expected_text

def test_returning_user_first_message_uses_memory(client: TestClient, db: Session) -> None:
    # Arrange: create a session summary to simulate returning user
    user_id = 9005
    old_session = TelegramSession(
        id=uuid4(),
        telegram_user_id=user_id,
        chat_id=3005,
        status="completed",
        reflective_mode="deep"
    )
    db.add(old_session)
    db.commit()

    db.add(
        SessionSummary(
            session_id=old_session.id,
            telegram_user_id=user_id,
            reflective_mode="deep",
            source_turn_count=3,
            takeaway="В прошлый раз мы обсуждали страх одиночества.",
            key_facts=["Страх одиночества проявляется в ссорах."],
            emotional_tensions=[],
            uncertainty_notes=[],
            next_step_context=[],
            retention_scope="durable_summary",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    # Act: 1. /start
    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 10,
                "text": "/start",
                "chat": {"id": 3005, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Mila"},
            }
        },
    )

    # 2. First message
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 11,
                "text": "Мне опять немного тревожно.",
                "chat": {"id": 3005, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Mila"},
            }
        },
    )

    # Assert: response is first_trust_response and includes memory context
    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "first_trust_response"

    from sqlmodel import select
    # Verify session in DB has merged context
    active_session = db.exec(
        select(TelegramSession)
        .where(TelegramSession.telegram_user_id == user_id)
        .where(TelegramSession.status == "active")
    ).one()

    assert "страх одиночества" in active_session.working_context.lower()
    assert "Мне опять немного тревожно" in active_session.working_context
