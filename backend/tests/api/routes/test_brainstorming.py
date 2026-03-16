"""Story D — Task D4: Full brainstorming orchestrator tests (10 scenarios)."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.models import ProcessedTelegramUpdate, TelegramSession


@pytest.fixture(autouse=True)
def cleanup(db: Session):
    yield
    db.exec(delete(ProcessedTelegramUpdate))
    db.exec(delete(TelegramSession))
    db.commit()


# ── helpers ──────────────────────────────────────────────────────────────────

def _start(user_id: int, update_id: int = 1) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 1,
            "from": {"id": user_id, "is_bot": False, "first_name": "T"},
            "chat": {"id": user_id, "type": "private"},
            "text": "/start",
        },
    }


def _cbq(user_id: int, data: str, update_id: int = 2) -> dict:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": "cq1",
            "from": {"id": user_id, "is_bot": False, "first_name": "T"},
            "message": {"message_id": 1, "chat": {"id": user_id, "type": "private"}},
            "data": data,
        },
    }


def _msg(user_id: int, text: str, update_id: int = 3) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 2,
            "from": {"id": user_id, "is_bot": False, "first_name": "T"},
            "chat": {"id": user_id, "type": "private"},
            "text": text,
        },
    }


def _enter_brainstorm(client: TestClient, user_id: int) -> None:
    """Start session and select brainstorm mode."""
    client.post("/api/v1/telegram/webhook", json=_start(user_id, update_id=user_id * 10))
    with patch("app.conversation._openai.call_chat", return_value=None):
        client.post(
            "/api/v1/telegram/webhook",
            json=_cbq(user_id, "brainstorm:mode:brainstorm", update_id=user_id * 10 + 1),
        )


def _get_session(db: Session, user_id: int) -> TelegramSession | None:
    db.expire_all()
    return db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).first()


# ── Scenario 1: /start shows new buttons ─────────────────────────────────────

def test_scenario_1_start_shows_correct_buttons(client: TestClient):
    """/start → 'Разобраться в ситуации' and 'Придумать решение' buttons, not old ones."""
    resp = client.post("/api/v1/telegram/webhook", json=_start(201_001))
    data = resp.json()
    all_btns = [b for row in data.get("inline_keyboard", []) for b in row]
    cb_datas = [b.get("callback_data", "") for b in all_btns]
    assert "brainstorm:mode:reflect" in cb_datas
    assert "brainstorm:mode:brainstorm" in cb_datas
    assert "mode:fast" not in cb_datas
    assert "mode:deep" not in cb_datas


# ── Scenario 2: brainstorm mode callback ─────────────────────────────────────

def test_scenario_2_brainstorm_callback_sets_collect_topic(client: TestClient, db: Session):
    """callback brainstorm:mode:brainstorm → phase=collect_topic + question returned."""
    user_id = 201_002
    client.post("/api/v1/telegram/webhook", json=_start(user_id, update_id=10))
    with patch("app.conversation._openai.call_chat", return_value=None):
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=_cbq(user_id, "brainstorm:mode:brainstorm", update_id=11),
        )
    assert resp.status_code == 200
    assert resp.json()["handled"] is True
    assert len(resp.json()["messages"]) > 0
    s = _get_session(db, user_id)
    assert s is not None
    assert s.brainstorm_phase == "collect_topic"


# ── Scenario 3: reflect mode callback ────────────────────────────────────────

def test_scenario_3_reflect_callback_sets_reflect_phase(client: TestClient, db: Session):
    """callback brainstorm:mode:reflect → phase=reflect + standard opening prompt."""
    user_id = 201_003
    client.post("/api/v1/telegram/webhook", json=_start(user_id, update_id=10))
    resp = client.post(
        "/api/v1/telegram/webhook",
        json=_cbq(user_id, "brainstorm:mode:reflect", update_id=11),
    )
    assert resp.status_code == 200
    assert resp.json()["handled"] is True
    s = _get_session(db, user_id)
    assert s is not None
    assert s.brainstorm_phase == "reflect"


# ── Scenario 4: phase transitions collect_topic → goal → constraints ──────────

def test_scenario_4_phase_transitions_and_data_accumulation(client: TestClient, db: Session):
    """collect_topic → collect_goal → collect_constraints: brainstorm_data accumulates."""
    user_id = 201_004
    _enter_brainstorm(client, user_id)

    with patch("app.conversation.brainstorming.orchestrator.call_chat", return_value=None):
        # Turn 1: answer to collect_topic (enough words)
        client.post(
            "/api/v1/telegram/webhook",
            json=_msg(user_id, "Хочу запустить онлайн-курс по Python для начинающих", update_id=100),
        )
        s = _get_session(db, user_id)
        assert s is not None
        assert s.brainstorm_phase == "collect_goal"
        assert s.brainstorm_data is not None
        assert "онлайн-курс" in s.brainstorm_data.get("topic", "")

        # Turn 2: answer to collect_goal
        client.post(
            "/api/v1/telegram/webhook",
            json=_msg(user_id, "Получить первых платящих студентов за месяц", update_id=101),
        )
        s = _get_session(db, user_id)
        assert s.brainstorm_phase == "collect_constraints"
        assert "студентов" in s.brainstorm_data.get("goal", "")

        # Turn 3: answer to collect_constraints
        client.post(
            "/api/v1/telegram/webhook",
            json=_msg(user_id, "Бюджет ноль рублей, времени два часа в день максимум", update_id=102),
        )
        s = _get_session(db, user_id)
        assert s.brainstorm_phase == "choose_approach"
        assert "два часа" in s.brainstorm_data.get("constraints", "")


# ── Scenario 5: facilitation_loop — cluster button threshold ─────────────────

def test_scenario_5_facilitation_loop_cluster_button_threshold(client: TestClient, db: Session):
    """facilitation_loop: 2 turns → no cluster button; 3rd turn → cluster button appears."""
    user_id = 201_005
    _enter_brainstorm(client, user_id)

    # Fast-forward to facilitation_loop by directly setting session state
    s = _get_session(db, user_id)
    assert s is not None
    s.brainstorm_phase = "facilitation_loop"
    s.brainstorm_data = {
        "topic": "тест",
        "goal": "цель",
        "constraints": "нет",
        "approach": "ideas",
        "ideas": [],
        "facilitation_turns": 0,
    }
    db.add(s)
    db.commit()

    with patch("app.conversation.brainstorming.orchestrator.call_chat", return_value=None):
        # Turn 1 (facilitation_turns will become 1)
        resp1 = client.post(
            "/api/v1/telegram/webhook",
            json=_msg(user_id, "Первая идея вот такая замечательная", update_id=200),
        )
        kb1 = [b for row in resp1.json().get("inline_keyboard", []) for b in row]
        assert not any("кластер" in b.get("text", "").lower() or "группировк" in b.get("text", "").lower() for b in kb1)

        # Turn 2 (facilitation_turns = 2)
        resp2 = client.post(
            "/api/v1/telegram/webhook",
            json=_msg(user_id, "Вторая идея немного другого плана", update_id=201),
        )
        kb2 = [b for row in resp2.json().get("inline_keyboard", []) for b in row]
        assert not any("группировк" in b.get("text", "").lower() for b in kb2)

        # Turn 3 (facilitation_turns = 3) → cluster button must appear
        resp3 = client.post(
            "/api/v1/telegram/webhook",
            json=_msg(user_id, "Третья идея и теперь можно группировать", update_id=202),
        )
        kb3 = [b for row in resp3.json().get("inline_keyboard", []) for b in row]
        assert any("группировк" in b.get("text", "").lower() for b in kb3)


# ── Scenario 6: facilitation_loop — ideas accumulate in order ─────────────────

def test_scenario_6_ideas_accumulate_in_order(client: TestClient, db: Session):
    """facilitation_loop: ideas are appended in the order they were sent."""
    user_id = 201_006
    _enter_brainstorm(client, user_id)

    s = _get_session(db, user_id)
    assert s is not None
    s.brainstorm_phase = "facilitation_loop"
    s.brainstorm_data = {
        "topic": "тест",
        "goal": "цель",
        "constraints": "нет",
        "approach": "ideas",
        "ideas": [],
        "facilitation_turns": 0,
    }
    db.add(s)
    db.commit()

    ideas_to_send = [
        "Идея альфа с пятью словами вот",
        "Идея бета с пятью словами вот",
        "Идея гамма с пятью словами вот",
    ]
    with patch("app.conversation.brainstorming.orchestrator.call_chat", return_value=None):
        for i, idea in enumerate(ideas_to_send):
            client.post(
                "/api/v1/telegram/webhook",
                json=_msg(user_id, idea, update_id=300 + i),
            )

    s = _get_session(db, user_id)
    assert s is not None
    ideas = s.brainstorm_data.get("ideas", [])
    assert len(ideas) == 3
    assert ideas[0] == ideas_to_send[0]
    assert ideas[1] == ideas_to_send[1]
    assert ideas[2] == ideas_to_send[2]


# ── Scenario 7: OpenAI fallback ───────────────────────────────────────────────

def test_scenario_7_openai_fallback_returns_fallback_text(client: TestClient, db: Session):
    """When call_chat returns None, bot replies with fallback text and phase advances."""
    user_id = 201_007
    _enter_brainstorm(client, user_id)

    with patch("app.conversation.brainstorming.orchestrator.call_chat", return_value=None):
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=_msg(user_id, "Хочу разобраться с управлением командой", update_id=400),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) > 0
    # Phase should advance even without OpenAI
    s = _get_session(db, user_id)
    assert s is not None
    assert s.brainstorm_phase == "collect_goal"


# ── Scenario 8: crisis resets brainstorm phase ────────────────────────────────

def test_scenario_8_crisis_resets_brainstorm_state(client: TestClient, db: Session):
    """Crisis routing resets brainstorm_phase=None and brainstorm_data=None."""
    from app.safety import SafetyAssessment

    user_id = 201_008
    _enter_brainstorm(client, user_id)

    s = _get_session(db, user_id)
    assert s is not None
    assert s.brainstorm_phase == "collect_topic"

    crisis = SafetyAssessment(
        classification="crisis",
        trigger_category="self_harm",
        confidence="high",
        blocks_normal_flow=True,
    )
    from app.safety.escalation import CrisisRoutingResponse
    with (
        patch("app.conversation.session_bootstrap.evaluate_incoming_message_safety", return_value=crisis),
        patch("app.conversation.session_bootstrap._compose_crisis_routing_response") as mock_cr,
        patch("app.conversation.session_bootstrap.create_and_deliver_operator_alert"),
    ):
        mock_cr.return_value = CrisisRoutingResponse(
            messages=("Поддержка рядом.",),
            resources=(),
            action="crisis_routing",
            inline_buttons=(),
        )
        client.post(
            "/api/v1/telegram/webhook",
            json=_msg(user_id, "мне очень плохо хочу исчезнуть", update_id=500),
        )

    s = _get_session(db, user_id)
    assert s is not None
    assert s.brainstorm_phase is None
    assert s.brainstorm_data is None


# ── Scenario 9: phase persistence (resume mid-session) ───────────────────────

def test_scenario_9_phase_persistence_resumes_from_cluster_ideas(client: TestClient, db: Session):
    """Session with brainstorm_phase=cluster_ideas resumes from that phase, not start."""
    user_id = 201_009
    _enter_brainstorm(client, user_id)

    # Manually advance session to cluster_ideas with pre-filled data
    s = _get_session(db, user_id)
    assert s is not None
    s.brainstorm_phase = "cluster_ideas"
    s.brainstorm_data = {
        "topic": "запуск курса",
        "goal": "студенты",
        "constraints": "нет денег",
        "approach": "ideas",
        "ideas": ["идея 1", "идея 2", "идея 3"],
        "facilitation_turns": 3,
    }
    db.add(s)
    db.commit()

    with patch("app.conversation.brainstorming.orchestrator.call_chat", return_value=None):
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=_msg(user_id, "Продолжаем — готов группировать идеи", update_id=600),
        )

    assert resp.status_code == 200
    # Phase should advance to prioritize (cluster_ideas → prioritize)
    s = _get_session(db, user_id)
    assert s is not None
    assert s.brainstorm_phase == "prioritize"


# ── Scenario 10: short input validation in collect_topic ─────────────────────

def test_scenario_10_short_input_keeps_collect_topic_phase(client: TestClient, db: Session):
    """collect_topic with < 5 words → phase stays collect_topic, question repeated."""
    user_id = 201_010
    _enter_brainstorm(client, user_id)

    with patch("app.conversation.brainstorming.orchestrator.call_chat", return_value=None):
        resp = client.post(
            "/api/v1/telegram/webhook",
            json=_msg(user_id, "курс Python", update_id=700),  # only 2 words
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) > 0
    # Phase must NOT advance
    s = _get_session(db, user_id)
    assert s is not None
    assert s.brainstorm_phase == "collect_topic"
    # topic should still be empty (not saved)
    assert s.brainstorm_data is not None
    assert s.brainstorm_data.get("topic", "") == ""
