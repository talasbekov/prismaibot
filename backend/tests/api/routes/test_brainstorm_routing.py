"""Story C: Tests for detect_mode routing, mode callbacks, and approach callbacks."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.models import (
    OperatorAlert,
    OperatorInvestigation,
    ProcessedTelegramUpdate,
    ProfileFact,
    SafetySignal,
    SessionSummary,
    SummaryGenerationSignal,
    TelegramSession,
)


@pytest.fixture(autouse=True)
def cleanup(db: Session):
    yield
    db.exec(delete(SummaryGenerationSignal))
    db.exec(delete(OperatorInvestigation))
    db.exec(delete(OperatorAlert))
    db.exec(delete(SafetySignal))
    db.exec(delete(ProfileFact))
    db.exec(delete(SessionSummary))
    db.exec(delete(ProcessedTelegramUpdate))
    db.exec(delete(TelegramSession))
    db.commit()


def _start_update(user_id: int = 111_000) -> dict:
    return {
        "update_id": user_id,
        "message": {
            "message_id": 1,
            "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            "chat": {"id": user_id, "type": "private"},
            "text": "/start",
        },
    }


def _callback_update(user_id: int, callback_data: str, update_id: int = 5000) -> dict:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": "cq1",
            "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            "message": {
                "message_id": 1,
                "chat": {"id": user_id, "type": "private"},
            },
            "data": callback_data,
        },
    }


def _message_update(user_id: int, text: str, update_id: int = 9000) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 2,
            "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            "chat": {"id": user_id, "type": "private"},
            "text": text,
        },
    }


# ── Task C1 ──────────────────────────────────────────────────────────────────


def test_start_autostarts_brainstorm(client: TestClient, db: Session):
    """AC2: /start immediately enters brainstorm collect_topic without mode buttons."""
    resp = client.post("/api/v1/telegram/webhook", json=_start_update(111_001))
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "brainstorm_autostart"
    assert data.get("inline_keyboard", []) == []
    assert len(data["messages"]) == 2
    assert "🌀 Prism AI" in data["messages"][0]["text"]
    assert "Опиши задачу или проблему" in data["messages"][1]["text"]
    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 111_001)
    ).first()
    assert session is not None
    assert session.brainstorm_phase == "collect_topic"


def test_start_does_not_show_old_buttons(client: TestClient):
    """Old mode buttons remain absent from /start response."""
    resp = client.post("/api/v1/telegram/webhook", json=_start_update(111_002))
    data = resp.json()
    assert data.get("inline_keyboard", []) == []


# ── Task C2 — brainstorm:mode:reflect ────────────────────────────────────────


def test_reflect_callback_sets_phase_reflect(client: TestClient, db: Session):
    """AC3: brainstorm:mode:reflect → brainstorm_phase='reflect' in DB."""
    user_id = 111_003
    # Now send reflect callback
    resp = client.post(
        "/api/v1/telegram/webhook",
        json=_callback_update(user_id, "brainstorm:mode:reflect", update_id=5003),
    )
    assert resp.status_code == 200
    s = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).first()
    assert s is not None
    assert s.brainstorm_phase == "reflect_listen"


def test_reflect_callback_returns_opening_prompt(client: TestClient):
    """AC3: brainstorm:mode:reflect → handled=True and response contains a message."""
    user_id = 111_004
    resp = client.post(
        "/api/v1/telegram/webhook",
        json=_callback_update(user_id, "brainstorm:mode:reflect", update_id=5004),
    )
    data = resp.json()
    assert data["handled"] is True
    assert len(data["messages"]) > 0


# ── Task C2 — brainstorm:mode:brainstorm ─────────────────────────────────────


def test_brainstorm_callback_sets_phase_collect_topic(client: TestClient, db: Session):
    """AC4: brainstorm:mode:brainstorm → brainstorm_phase='collect_topic' in DB."""
    user_id = 111_005
    with patch(
        "app.conversation._openai.call_chat",
        return_value=None,
    ):
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=_callback_update(user_id, "brainstorm:mode:brainstorm", update_id=5005),
        )
    assert resp.status_code == 200
    s = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).first()
    assert s is not None
    assert s.brainstorm_phase == "collect_topic"


def test_brainstorm_callback_initializes_data(client: TestClient, db: Session):
    """AC4: brainstorm:mode:brainstorm → brainstorm_data initialized with empty schema."""
    user_id = 111_006
    with patch("app.conversation._openai.call_chat", return_value=None):
        client.post(
            "/api/v1/telegram/webhook",
            json=_callback_update(user_id, "brainstorm:mode:brainstorm", update_id=5006),
        )
    s = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).first()
    assert s is not None
    assert s.brainstorm_data is not None
    assert "topic" in s.brainstorm_data
    assert "ideas" in s.brainstorm_data
    assert isinstance(s.brainstorm_data["ideas"], list)
    assert s.brainstorm_data["facilitation_turns"] == 0


def test_brainstorm_callback_returns_question(client: TestClient):
    """AC4: brainstorm:mode:brainstorm → bot asks first brainstorming question."""
    user_id = 111_007
    with patch("app.conversation._openai.call_chat", return_value=None):
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=_callback_update(user_id, "brainstorm:mode:brainstorm", update_id=5007),
        )
    data = resp.json()
    assert data["handled"] is True
    assert len(data["messages"]) > 0


# ── Task C4 — crisis reset ────────────────────────────────────────────────────


def test_crisis_resets_brainstorm_phase(client: TestClient, db: Session):
    """AC13: Crisis routing resets brainstorm_phase and brainstorm_data to None."""
    from app.safety import SafetyAssessment

    user_id = 111_010
    # Start session directly in brainstorming
    with patch("app.conversation._openai.call_chat", return_value=None):
        client.post("/api/v1/telegram/webhook", json=_start_update(user_id))

    # Verify brainstorm_phase is set
    s = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).first()
    assert s is not None
    db.refresh(s)
    assert s.brainstorm_phase == "collect_topic"

    # Send crisis message — mock safety to return crisis classification
    crisis_assessment = SafetyAssessment(
        classification="crisis",
        trigger_category="self_harm",
        confidence="high",
        blocks_normal_flow=True,
    )
    with (
        patch(
            "app.conversation.session_bootstrap.evaluate_incoming_message_safety",
            return_value=crisis_assessment,
        ),
        patch("app.safety.compose_crisis_routing_response") as mock_crisis,
        patch("app.conversation.session_bootstrap.create_and_deliver_operator_alert"),
    ):
        from app.safety import CrisisRoutingResponse
        mock_crisis.return_value = CrisisRoutingResponse(
            messages=("Поддержка рядом.",),
            resources=(),
            action="crisis_routing",
            inline_buttons=(),
        )
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=_message_update(user_id, "мне очень плохо хочу умереть", update_id=9010),
        )
    assert resp.status_code == 200

    db.expire_all()
    s2 = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).first()
    assert s2 is not None
    assert s2.brainstorm_phase is None
    assert s2.brainstorm_data is None
