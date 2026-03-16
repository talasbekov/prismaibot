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

def test_delete_command_creates_request(client: TestClient, db: Session) -> None:
    user_id = 6001

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 1,
                "text": "/delete",
                "chat": {"id": 7001, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "deletion_confirmed"
    assert "запрос на удаление данных принят" in payload["messages"][0]["text"]

    req = db.exec(select(DeletionRequest).where(DeletionRequest.telegram_user_id == user_id)).one()
    assert req.status == "pending"

def test_delete_command_idempotency(client: TestClient, db: Session) -> None:
    user_id = 6002

    # First call
    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 1,
                "text": "/delete",
                "chat": {"id": 7002, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            }
        },
    )

    # Second call
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 2,
                "text": "/delete",
                "chat": {"id": 7002, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "deletion_already_pending"
    assert "уже отправил запрос" in payload["messages"][0]["text"]

    requests = db.exec(select(DeletionRequest).where(DeletionRequest.telegram_user_id == user_id)).all()
    assert len(requests) == 1

def test_normal_flow_continues_after_delete(client: TestClient, db: Session) -> None:
    user_id = 6003
    chat_id = 7003

    # 1. /delete
    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 1,
                "text": "/delete",
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            }
        },
    )

    # 2. Normal message
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 2,
                "text": "Я хочу просто поговорить о своем дне.",
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    # It should be first_trust_response because it's a new session
    assert payload["action"] == "first_trust_response"
    assert payload["session_id"] is not None
