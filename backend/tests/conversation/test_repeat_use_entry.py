from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

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

def test_new_user_start_autostarts_brainstorming(client: TestClient, db: Session) -> None:
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
    assert payload["action"] == "brainstorm_autostart"
    assert payload["session_id"] is not None
    assert payload["inline_keyboard"] == []
    assert len(payload["messages"]) == 2
    assert "🌀 Prism AI" in payload["messages"][0]["text"]
    assert "Опиши задачу или проблему" in payload["messages"][1]["text"]

    active_session = db.exec(
        select(TelegramSession)
        .where(TelegramSession.telegram_user_id == 1001)
        .where(TelegramSession.status == "active")
    ).one()
    assert active_session.brainstorm_phase == "collect_topic"
    assert active_session.brainstorm_data is not None

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
    assert payload["action"] == "brainstorm_autostart"
    assert payload["session_id"] is not None
    assert payload["inline_keyboard"] == []
    assert len(payload["messages"]) == 2
    assert "🌀 Prism AI" in payload["messages"][0]["text"]
    assert "Опиши задачу или проблему" in payload["messages"][1]["text"]

    active_session = db.exec(
        select(TelegramSession)
        .where(TelegramSession.telegram_user_id == user_id)
        .where(TelegramSession.status == "active")
    ).one()
    assert active_session.brainstorm_phase == "collect_topic"
    assert active_session.brainstorm_data is not None

def test_start_reuses_existing_active_brainstorm_session(client: TestClient, db: Session) -> None:
    user_id = 1007
    existing_session = TelegramSession(
        telegram_user_id=user_id,
        chat_id=4001,
        status="active",
        brainstorm_phase="facilitation_loop",
        brainstorm_data={
            "topic": "старый контекст",
            "goal": "старая цель",
            "constraints": "старые ограничения",
            "approach": "ideas",
            "ideas": ["идея 1"],
            "facilitation_turns": 1,
        },
    )
    db.add(existing_session)
    db.commit()

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 3,
                "text": "/start",
                "chat": {"id": 4001, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Masha"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "brainstorm_autostart"
    assert payload["session_id"] == str(existing_session.id)
    assert len(payload["messages"]) == 2
    assert "🌀 Prism AI" in payload["messages"][0]["text"]
    assert "Опиши задачу или проблему" in payload["messages"][1]["text"]

    db.expire_all()
    active_session = db.exec(
        select(TelegramSession)
        .where(TelegramSession.telegram_user_id == user_id)
        .where(TelegramSession.status == "active")
    ).one()
    assert active_session.id == existing_session.id
    assert active_session.brainstorm_phase == "collect_topic"
    assert active_session.brainstorm_data is not None
    assert active_session.brainstorm_data["ideas"] == []

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

    # Act: 1. /start (autostart brainstorming)
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
                "text": "Мне опять немного тревожно после нашей ссоры вчера вечером.",
                "chat": {"id": 3005, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Mila"},
            }
        },
    )

    # Assert: response is first_trust_response and includes memory context
    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "brainstorm_collect_topic"

    # Verify session in DB has merged context
    active_session = db.exec(
        select(TelegramSession)
        .where(TelegramSession.telegram_user_id == user_id)
        .where(TelegramSession.status == "active")
    ).one()

    assert active_session.brainstorm_phase == "collect_goal"
    assert active_session.brainstorm_data is not None
    assert (
        active_session.brainstorm_data["topic"]
        == "Мне опять немного тревожно после нашей ссоры вчера вечером."
    )
