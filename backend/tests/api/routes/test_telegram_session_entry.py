from typing import Any, cast
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.conversation.first_response import FirstTrustResponse
from app.conversation.session_bootstrap import OPENING_PROMPT, handle_session_entry
from app.models import (
    OperatorAlert,
    OperatorInvestigation,
    ProfileFact,
    SafetySignal,
    SessionSummary,
    SummaryGenerationSignal,
    TelegramSession,
)


@pytest.fixture(autouse=True)
def clear_telegram_sessions(db: Session) -> None:
    from app.billing.models import FreeSessionEvent, PurchaseIntent, UserAccessState
    from app.models import DeletionRequest, PeriodicInsight, ProcessedTelegramUpdate
    db.execute(delete(FreeSessionEvent))
    db.execute(delete(PurchaseIntent))
    db.execute(delete(UserAccessState))
    db.execute(delete(SummaryGenerationSignal))
    db.execute(delete(OperatorInvestigation))
    db.execute(delete(OperatorAlert))
    db.execute(delete(SafetySignal))
    db.execute(delete(ProfileFact))
    db.execute(delete(SessionSummary))
    db.execute(delete(TelegramSession))
    db.execute(delete(ProcessedTelegramUpdate))
    db.execute(delete(PeriodicInsight))
    db.execute(delete(DeletionRequest))
    db.commit()


def test_start_autostarts_brainstorming_with_typing_signal(
    client: TestClient, db: Session
) -> None:
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
    assert payload["status"] == "ok"
    assert payload["action"] == "brainstorm_autostart"
    assert payload["signals"] == ["typing"]
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["text"] == OPENING_PROMPT
    assert "Опиши задачу или проблему" in payload["messages"][1]["text"]
    assert payload["session_id"] is not None

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1001)
    ).one()
    assert session.chat_id == 2001
    assert session.brainstorm_phase == "collect_topic"
    assert session.brainstorm_data is not None
    assert session.brainstorm_data["ideas"] == []
    assert payload["inline_keyboard"] == []


def test_start_includes_reply_keyboard_with_help_and_reset(
    client: TestClient, db: Session
) -> None:
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

    payload = response.json()
    assert payload["status"] == "ok"
    markup = payload["reply_markup"]
    assert markup is not None
    assert markup["resize_keyboard"] is True
    assert markup["one_time_keyboard"] is False
    button_texts = [btn["text"] for btn in markup["keyboard"][0]]
    assert "❓ Помощь" in button_texts
    assert "🔄 Начать заново" in button_texts


def test_first_message_creates_session_tied_to_telegram_user_id(
    client: TestClient, db: Session
) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 2,
                "text": "Мы снова поссорились, и я не понимаю, это я перегнула или меня правда не слышат.",
                "chat": {"id": 2002, "type": "private"},
                "from": {"id": 1002, "is_bot": False, "first_name": "Masha"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["action"] == "first_trust_response"
    assert payload["signals"] == ["typing"]
    assert payload["session_id"] is not None

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1002)
    ).one()
    assert session.chat_id == 2002
    assert session.status == "active"
    assert session.turn_count == 1
    assert "поссорились" in (session.last_user_message or "")


def test_crisis_message_blocks_normal_reflective_flow_and_records_signal(
    client: TestClient, db: Session
) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 2,
                "text": "Я хочу покончить с собой, потому что дальше так не могу.",
                "chat": {"id": 2102, "type": "private"},
                "from": {"id": 1102, "is_bot": False, "first_name": "Masha"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "crisis_routed"
    assert "safety_crisis_detected" in payload["signals"]
    assert "crisis_mode_active" in payload["signals"]
    assert any("позвони" in message["text"].lower() for message in payload["messages"])
    assert len(payload["inline_keyboard"]) == 1
    assert all("url" in button for button in payload["inline_keyboard"][0])

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1102)
    ).one()
    assert session.safety_classification == "crisis"
    assert session.safety_trigger_category == "self_harm"
    assert session.safety_last_evaluated_at is not None
    assert session.crisis_state == "crisis_active"
    assert session.crisis_activated_at is not None

    signal = db.exec(
        select(SafetySignal).where(SafetySignal.session_id == session.id)
    ).one()
    assert signal.classification == "crisis"
    assert signal.trigger_category == "self_harm"

    alert = db.exec(
        select(OperatorAlert).where(OperatorAlert.session_id == session.id)
    ).one()
    assert alert.status == "delivered"
    assert alert.classification == "crisis"
    assert alert.trigger_category == "self_harm"
    assert "last_user_message" not in alert.payload
    assert "working_context" not in alert.payload
    assert "last_bot_prompt" not in alert.payload


def test_borderline_message_keeps_reflective_flow_but_records_bounded_signal(
    client: TestClient, db: Session
) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 3,
                "text": "Иногда кажется, что лучше бы просто исчезнуть и никому не мешать.",
                "chat": {"id": 2103, "type": "private"},
                "from": {"id": 1103, "is_bot": False, "first_name": "Lena"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "first_trust_response"
    assert "safety_borderline_detected" in payload["signals"]

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1103)
    ).one()
    assert session.safety_classification == "borderline"
    assert session.safety_trigger_category == "self_harm"

    signal = db.exec(
        select(SafetySignal).where(SafetySignal.session_id == session.id)
    ).one()
    assert signal.classification == "borderline"
    assert signal.trigger_category == "self_harm"


def test_later_message_can_flip_session_into_crisis_state(
    client: TestClient, db: Session
) -> None:
    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": 2104, "type": "private"},
                "from": {"id": 1104, "is_bot": False, "first_name": "Rita"},
            }
        }

    first_response = client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Мы снова поссорились, мне очень тяжело и обидно.", 4),
    )
    assert first_response.status_code == 200
    assert first_response.json()["action"] == "first_trust_response"
    first_session_id = first_response.json()["session_id"]

    crisis_response = client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Сейчас мне хочется причинить себе вред, чтобы это прекратилось.", 5),
    )
    assert crisis_response.status_code == 200
    assert crisis_response.json()["action"] == "crisis_routed"
    assert "safety_crisis_detected" in crisis_response.json()["signals"]
    assert "crisis_mode_active" in crisis_response.json()["signals"]
    assert crisis_response.json()["session_id"] == first_session_id

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1104)
    ).one()
    assert session.safety_classification == "crisis"
    assert session.safety_trigger_category == "self_harm"
    assert session.crisis_state == "crisis_active"
    assert session.crisis_activated_at is not None


@pytest.mark.parametrize("mode", ["fast", "deep"])
def test_crisis_routing_takes_priority_over_selected_mode(
    client: TestClient, db: Session, mode: str
) -> None:
    user_id = 1110 if mode == "fast" else 1111
    chat_id = 2110 if mode == "fast" else 2111

    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 50,
                "text": "Мне хочется покончить с собой, я больше не могу так.",
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Masha"},
            }
        },
    )

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).one()
    session.reflective_mode = mode
    db.add(session)
    db.commit()

    with patch(
        "app.conversation.session_bootstrap._compose_first_trust_response"
    ) as first_trust_mock, patch(
        "app.conversation.session_bootstrap.compose_clarification_response"
    ) as clarification_mock, patch(
        "app.conversation.session_bootstrap.compose_session_closure"
    ) as closure_mock:
        crisis_response = client.post(
            "/api/v1/telegram/webhook",
            json={
                "message": {
                    "message_id": 51,
                    "text": "Я убью себя, если это не закончится.",
                    "chat": {"id": chat_id, "type": "private"},
                    "from": {"id": user_id, "is_bot": False, "first_name": "Masha"},
                }
            },
        )

    assert crisis_response.status_code == 200
    payload = crisis_response.json()
    assert payload["action"] == "crisis_routed"
    assert "crisis_mode_active" in payload["signals"]
    first_trust_mock.assert_not_called()
    clarification_mock.assert_not_called()
    closure_mock.assert_not_called()


def test_safe_message_in_crisis_active_session_still_routes_to_crisis(
    client: TestClient, db: Session
) -> None:
    """A safe message sent to a crisis_active session must still route to crisis.

    This exercises the sticky crisis_state branch of should_route_to_crisis in
    isolation — both the first and second messages must route, but the second
    message carries no crisis language, so routing is driven solely by
    crisis_state == "crisis_active".
    """

    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": 2121, "type": "private"},
                "from": {"id": 1121, "is_bot": False, "first_name": "Dasha"},
            }
        }

    client.post("/api/v1/telegram/webhook", json=_payload("Я хочу покончить с собой.", 60))

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1121)
    ).one()
    assert session.crisis_state == "crisis_active"

    with patch(
        "app.conversation.session_bootstrap._compose_first_trust_response"
    ) as first_trust_mock, patch(
        "app.conversation.session_bootstrap.compose_clarification_response"
    ) as clarification_mock:
        safe_response = client.post(
            "/api/v1/telegram/webhook",
            json=_payload("Сегодня был хороший день, мы гуляли в парке.", 61),
        )

    assert safe_response.status_code == 200
    payload = safe_response.json()
    assert payload["action"] == "crisis_routed"
    assert "crisis_mode_active" in payload["signals"]
    # No safety_crisis_detected: the message itself is safe; routing is via sticky state only
    assert "safety_crisis_detected" not in payload["signals"]
    # Normal reflective branches must not be entered
    first_trust_mock.assert_not_called()
    clarification_mock.assert_not_called()
    # Routing response for an already-active session is a single continuation message
    assert len(payload["messages"]) == 1
    assert "чувствительным" in payload["messages"][0]["text"].lower()
    assert "серьезного риска" not in payload["messages"][0]["text"].lower()
    assert payload["inline_keyboard"]


def test_safe_correction_after_crisis_can_enter_step_down_recovery_path(
    client: TestClient, db: Session
) -> None:
    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": 2122, "type": "private"},
                "from": {"id": 1122, "is_bot": False, "first_name": "Masha"},
            }
        }

    first_response = client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Я хочу покончить с собой, потому что дальше так не могу.", 70),
    )
    assert first_response.status_code == 200
    assert first_response.json()["action"] == "crisis_routed"

    safe_response = client.post(
        "/api/v1/telegram/webhook",
        json=_payload(
            "Нет, я не собираюсь причинять себе вред. Я просто очень испугалась своей реакции.",
            71,
        ),
    )

    assert safe_response.status_code == 200
    payload = safe_response.json()
    assert payload["action"] == "crisis_step_down"
    assert "crisis_mode_active" not in payload["signals"]
    assert "safety_recovery_step_down" in payload["signals"]
    assert any("слишком резко" in message["text"].lower() for message in payload["messages"])

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1122)
    ).one()
    assert session.crisis_state == "step_down_pending"
    assert session.crisis_step_down_at is not None


def test_step_down_follow_up_can_resume_reflective_flow(
    client: TestClient, db: Session
) -> None:
    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": 2123, "type": "private"},
                "from": {"id": 1123, "is_bot": False, "first_name": "Masha"},
            }
        }

    client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Я хочу покончить с собой, потому что дальше так не могу.", 72),
    )
    client.post(
        "/api/v1/telegram/webhook",
        json=_payload(
            "Нет, я не собираюсь причинять себе вред. Я просто очень испугалась своей реакции.",
            73,
        ),
    )

    resumed_response = client.post(
        "/api/v1/telegram/webhook",
        json=_payload(
            "Сильнее всего меня задело, что после ссоры я почувствовала себя совсем одной.",
            74,
        ),
    )

    assert resumed_response.status_code == 200
    payload = resumed_response.json()
    assert payload["action"] == "clarification_turn"
    assert "crisis_mode_active" not in payload["signals"]
    assert "safety_recovery_step_down" not in payload["signals"]

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1123)
    ).one()
    assert session.crisis_state == "normal"


def test_step_down_failure_keeps_session_in_crisis_and_records_signal(
    client: TestClient, db: Session
) -> None:
    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": 2124, "type": "private"},
                "from": {"id": 1124, "is_bot": False, "first_name": "Masha"},
            }
        }

    client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Я хочу покончить с собой, потому что дальше так не могу.", 75),
    )

    with patch(
        "app.conversation.session_bootstrap.compose_crisis_step_down_response",
        side_effect=RuntimeError("boom"),
    ):
        response = client.post(
            "/api/v1/telegram/webhook",
            json=_payload(
                "Нет, я не собираюсь причинять себе вред. Я просто очень испугалась своей реакции.",
                76,
            ),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "safety_step_down_error"
    assert "safety_step_down_failed" in payload["signals"]
    assert "crisis_mode_active" in payload["signals"]

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1124)
    ).one()
    assert session.crisis_state == "crisis_active"

    signal = db.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.session_id == session.id
        )
    ).one()
    assert signal.signal_type == "safety_step_down_failed"


def test_new_crisis_message_in_step_down_pending_uses_continuation_copy(
    client: TestClient, db: Session
) -> None:
    """A session in step_down_pending that receives a new explicit crisis message must
    route via high_concern_continuation, not high_concern_activation. The session was
    already in crisis — it is not a new activation."""

    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": 2131, "type": "private"},
                "from": {"id": 1131, "is_bot": False, "first_name": "Masha"},
            }
        }

    # Crisis activation
    client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Я хочу покончить с собой, дальше так не могу.", 80),
    )
    # Step-down: explicit recovery signal
    client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Нет, я не собираюсь причинять себе вред. Просто испугалась.", 81),
    )
    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1131)
    ).one()
    assert session.crisis_state == "step_down_pending"

    # New crisis message while in step_down_pending — must use continuation, not activation
    crisis_response = client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Я снова думаю о том, чтобы причинить себе вред.", 82),
    )

    assert crisis_response.status_code == 200
    payload = crisis_response.json()
    assert payload["action"] == "crisis_routed"
    assert "crisis_mode_active" in payload["signals"]
    # Continuation variant: 1 message, mentions serious risk — NOT the full 2-message activation
    assert len(payload["messages"]) == 1
    combined = payload["messages"][0]["text"].lower()
    assert "серьезного риска" in combined
    # Activation-specific phrase must NOT appear (would indicate wrong variant was used)
    assert "тебе сейчас правда очень тяжело" not in combined

    db.expire_all()
    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1131)
    ).one()
    assert session.crisis_state == "crisis_active"


def test_borderline_message_in_step_down_pending_routes_back_to_crisis(
    client: TestClient, db: Session
) -> None:
    """A borderline message during step_down_pending must not prematurely resume
    to normal flow. Only an explicitly safe (classification == 'safe') message
    should clear the step_down_pending state. A borderline signal during recovery
    routes back to crisis_active with the softer continuation copy."""

    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": 2132, "type": "private"},
                "from": {"id": 1132, "is_bot": False, "first_name": "Masha"},
            }
        }

    # Crisis activation
    client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Я хочу покончить с собой, дальше так не могу.", 83),
    )
    # Step-down: explicit recovery signal
    client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Нет, я не собираюсь причинять себе вред. Просто испугалась.", 84),
    )
    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1132)
    ).one()
    assert session.crisis_state == "step_down_pending"

    # Borderline message during step_down_pending: matches borderline self-harm pattern
    borderline_response = client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Иногда думаю, что всем без меня лучше.", 85),
    )

    assert borderline_response.status_code == 200
    payload = borderline_response.json()
    # Crisis routing must be used: step_down_pending + non-safe message stays cautious
    assert payload["action"] == "crisis_routed"
    assert "crisis_mode_active" in payload["signals"]
    # Uses soft continuation copy (not newly_activated), since session was already in crisis context
    assert len(payload["messages"]) == 1
    assert "чувствительным" in payload["messages"][0]["text"].lower()

    db.expire_all()
    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1132)
    ).one()
    # Borderline during recovery routes back to crisis_active, not stuck in step_down_pending
    assert session.crisis_state == "crisis_active"


def test_repeated_crisis_message_in_active_session_uses_high_concern_continuation(
    client: TestClient, db: Session
) -> None:
    """A crisis_active session that receives another explicit crisis message must use
    high_concern_continuation wording, not the softer variant used for safe messages."""

    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": 2130, "type": "private"},
                "from": {"id": 1130, "is_bot": False, "first_name": "Masha"},
            }
        }

    # First message: activate crisis
    client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Я хочу причинить себе вред, чтобы это прекратилось.", 70),
    )

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1130)
    ).one()
    assert session.crisis_state == "crisis_active"

    # Second message: another explicit crisis signal in already-active session
    # → must route via high_concern_continuation, NOT soft_continuation
    second_response = client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Я снова думаю о том, чтобы причинить себе вред.", 71),
    )

    assert second_response.status_code == 200
    payload = second_response.json()
    assert payload["action"] == "crisis_routed"
    assert "crisis_mode_active" in payload["signals"]
    assert len(payload["messages"]) == 1
    combined = payload["messages"][0]["text"].lower()
    assert "серьезного риска" in combined
    assert "обычный разбор" in combined
    # high_concern_continuation does not mention soft framing
    assert "чувствительным моментом" not in combined

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1130)
    ).one()
    alert = db.exec(
        select(OperatorAlert).where(OperatorAlert.session_id == session.id)
    ).one()
    assert alert.delivery_attempt_count == 2
    assert alert.status == "delivered"


def test_operator_alert_delivery_failure_keeps_alert_record_and_visible_incident(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise_delivery(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("ops inbox unavailable")

    monkeypatch.setattr("app.ops.alerts._deliver_to_ops_inbox", _raise_delivery)

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 56,
                "text": "Я хочу покончить с собой и не вижу смысла продолжать.",
                "chat": {"id": 2116, "type": "private"},
                "from": {"id": 1116, "is_bot": False, "first_name": "Nika"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "crisis_routed"

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1116)
    ).one()
    alert = db.exec(
        select(OperatorAlert).where(OperatorAlert.session_id == session.id)
    ).one()
    assert alert.status == "delivery_failed"
    assert "ops inbox unavailable" in (alert.last_delivery_error or "")

    summary_signal = db.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.session_id == session.id
        )
    ).one()
    assert summary_signal.signal_type == "operator_alert_delivery_failed"


def test_crisis_first_turn_does_not_call_standard_first_trust_branch(
    client: TestClient,
) -> None:
    with patch(
        "app.conversation.session_bootstrap._compose_first_trust_response"
    ) as first_trust_mock:
        response = client.post(
            "/api/v1/telegram/webhook",
            json={
                "message": {
                    "message_id": 52,
                    "text": "Я хочу покончить с собой и не вижу выхода.",
                    "chat": {"id": 2112, "type": "private"},
                    "from": {"id": 1112, "is_bot": False, "first_name": "Lena"},
                }
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "crisis_routed"
    assert len(payload["messages"]) == 2
    combined = " ".join(message["text"] for message in payload["messages"]).lower()
    assert "очень тяжело" in combined
    assert "обычного разбора" in combined
    assert "недостаточно" in combined
    assert "я не могу помочь" not in combined
    first_trust_mock.assert_not_called()


def test_safety_evaluation_failure_creates_visible_signal_and_avoids_silent_safe_path(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(*_args: object, **_kwargs: object) -> SafetySignal:
        raise RuntimeError("safety boom")

    monkeypatch.setattr(
        "app.conversation.session_bootstrap.evaluate_incoming_message_safety",
        _raise,
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 6,
                "text": "Мне сейчас очень плохо, и я не понимаю, что со мной.",
                "chat": {"id": 2105, "type": "private"},
                "from": {"id": 1105, "is_bot": False, "first_name": "Sasha"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "safety_check_error"
    assert "safety_check_failed" in payload["signals"]

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1105)
    ).one()
    summary_signal = db.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.session_id == session.id
        )
    ).one()
    assert summary_signal.signal_type == "safety_evaluation_failed"
    assert summary_signal.details["suggested_action"] == "review_safety_evaluation_failure"


def test_crisis_routing_failure_creates_visible_signal_and_blocks_normal_flow(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("routing boom")

    monkeypatch.setattr(
        "app.conversation.session_bootstrap._compose_crisis_routing_response",
        _raise,
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 53,
                "text": "Я хочу покончить с собой, потому что не вижу смысла продолжать.",
                "chat": {"id": 2113, "type": "private"},
                "from": {"id": 1113, "is_bot": False, "first_name": "Sasha"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "safety_routing_error"
    assert "safety_routing_failed" in payload["signals"]

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1113)
    ).one()
    # Session must be marked crisis_active even when routing itself failed, so
    # subsequent messages don't accidentally resume normal reflective flow.
    assert session.crisis_state == "crisis_active"
    summary_signal = db.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.session_id == session.id
        )
    ).one()
    assert summary_signal.signal_type == "safety_routing_failed"
    assert summary_signal.details["suggested_action"] == "review_crisis_routing_failure"


def test_invalid_crisis_copy_is_blocked_and_recorded_as_visible_failure(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.safety.escalation._MESSAGE_VARIANTS",
        {
            "high_concern_activation": (
                "Я не могу помочь с этим.",
                "Тебе нужен диагноз и срочная терапия.",
            ),
            "high_concern_continuation": (
                "Я не могу помочь с этим.",
            ),
            "soft_continuation": (
                "Я не могу помочь с этим.",
            ),
        },
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 54,
                "text": "Я хочу покончить с собой и больше не справляюсь.",
                "chat": {"id": 2114, "type": "private"},
                "from": {"id": 1114, "is_bot": False, "first_name": "Mira"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "safety_routing_error"
    assert "safety_routing_failed" in payload["signals"]
    combined = " ".join(message["text"] for message in payload["messages"]).lower()
    assert "я не могу помочь" not in combined
    assert "терап" not in combined

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1114)
    ).one()
    assert session.crisis_state == "crisis_active"
    summary_signal = db.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.session_id == session.id
        )
    ).one()
    assert summary_signal.signal_type == "safety_routing_failed"


def test_invalid_crisis_resources_are_blocked_and_recorded_as_visible_failure(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.safety.escalation.get_curated_crisis_resources",
        lambda: (),
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 55,
                "text": "Я хочу покончить с собой и не вижу, как дожить до завтра.",
                "chat": {"id": 2115, "type": "private"},
                "from": {"id": 1115, "is_bot": False, "first_name": "Mira"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "safety_routing_error"
    assert "safety_routing_failed" in payload["signals"]

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1115)
    ).one()
    summary_signal = db.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.session_id == session.id
        )
    ).one()
    assert summary_signal.signal_type == "safety_routing_failed"


def test_borderline_crisis_routing_preserves_classification_in_alert(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Borderline + blocks_normal_flow=True routes to crisis and preserves
    classification nuance in the operator alert (AC6)."""
    from app.safety.service import SafetyAssessment

    def _borderline_assessment(*_args: object, **_kwargs: object) -> SafetyAssessment:
        return SafetyAssessment(
            classification="borderline",
            trigger_category="self_harm",
            confidence="medium",
            blocks_normal_flow=True,
        )

    monkeypatch.setattr(
        "app.conversation.session_bootstrap.evaluate_incoming_message_safety",
        _borderline_assessment,
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 57,
                "text": "Иногда думаю о том, чтобы причинить себе вред.",
                "chat": {"id": 2117, "type": "private"},
                "from": {"id": 1117, "is_bot": False, "first_name": "Vera"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "crisis_routed"

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1117)
    ).one()
    alert = db.exec(
        select(OperatorAlert).where(OperatorAlert.session_id == session.id)
    ).one()
    assert alert.classification == "borderline"
    assert alert.confidence == "medium"
    assert alert.trigger_category == "self_harm"
    assert alert.payload["classification"] == "borderline"
    assert alert.payload["confidence"] == "medium"


def test_short_input_returns_clarifying_prompt(
    client: TestClient, db: Session
) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 3,
                "text": "Не знаю",
                "chat": {"id": 2003, "type": "private"},
                "from": {"id": 1003, "is_bot": False, "first_name": "Lena"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["action"] == "clarify_input"
    assert payload["signals"] == ["typing"]
    assert payload["session_id"] is not None

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1003)
    ).one()
    assert session.turn_count == 1


def test_callback_update_is_ignored(client: TestClient) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "callback_query": {
                "id": "cbq-1",
                "data": "some:data",
                "from": {"id": 1004, "is_bot": False, "first_name": "Test"},
                "message": {"message_id": 4, "chat": {"id": 2004, "type": "private"}},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ignored"
    assert payload["handled"] is False


def test_missing_message_field_is_ignored(client: TestClient) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={"update_id": 999},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_first_turn_calls_compose_first_trust_response(
    client: TestClient, db: Session
) -> None:
    """First message must be routed through _compose_first_trust_response.

    The mock returns a distinctive action and text so we can verify that the
    first-trust seam — not the generic session_entry branch — handled the request.
    """
    with patch(
        "app.conversation.session_bootstrap._compose_first_trust_response",
        return_value=FirstTrustResponse(
            messages=("Кажется, тебе сейчас непросто.",),
            action="first_trust_response",
        ),
    ) as mock_compose:
        response = client.post(
            "/api/v1/telegram/webhook",
            json={
                "message": {
                    "message_id": 10,
                    "text": "Мы с мужем снова поссорились, и я не понимаю, что происходит.",
                    "chat": {"id": 3001, "type": "private"},
                    "from": {"id": 2001, "is_bot": False, "first_name": "Anna"},
                }
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["action"] == "first_trust_response"
    assert payload["messages"][0]["text"] == "Кажется, тебе сейчас непросто."
    assert payload["session_id"] is not None
    mock_compose.assert_called_once()

    record = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 2001)
    ).one()
    assert record.turn_count == 1


def test_second_turn_skips_compose_first_trust_response(
    client: TestClient, db: Session
) -> None:
    """Second message must NOT call _compose_first_trust_response."""

    def _make_webhook(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": 3002, "type": "private"},
                "from": {"id": 2002, "is_bot": False, "first_name": "Boris"},
            }
        }

    # First turn establishes turn_count == 1.
    client.post(
        "/api/v1/telegram/webhook",
        json=_make_webhook("Поругался с коллегой, не знаю как реагировать.", 11),
    )

    # Second turn must bypass the first-trust seam entirely.
    with patch(
        "app.conversation.session_bootstrap._compose_first_trust_response"
    ) as mock_compose:
        response = client.post(
            "/api/v1/telegram/webhook",
            json=_make_webhook("Он просто перебил меня на совещании при всех.", 12),
        )

    assert response.status_code == 200
    assert response.json()["action"] == "clarification_turn"
    mock_compose.assert_not_called()

    record = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 2002)
    ).one()
    assert record.turn_count == 2


def test_oversized_message_is_truncated_and_stored(
    client: TestClient, db: Session
) -> None:
    """Messages longer than 2000 characters must be truncated before DB write."""
    long_text = "А" * 3000

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 13,
                "text": long_text,
                "chat": {"id": 3003, "type": "private"},
                "from": {"id": 2003, "is_bot": False, "first_name": "Cleo"},
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    record = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 2003)
    ).one()
    assert record.last_user_message is not None
    assert len(record.last_user_message) == 2000


def test_first_trust_response_is_chunked_and_reflection_first(
    client: TestClient,
) -> None:
    """Behavioural test: first reply must open with reflection, not advice/diagnosis.

    Assertions are structural so they survive when keyword-matching is replaced
    by an OpenAI API call.
    """
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 14,
                "text": "Мы с мужем снова поссорились, и мне обидно, что он как будто меня вообще не слышит.",
                "chat": {"id": 3004, "type": "private"},
                "from": {"id": 2004, "is_bot": False, "first_name": "Dina"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "first_trust_response"
    # Chunked: exactly 2 messages for Telegram readability
    assert len(payload["messages"]) == 2

    first_text = payload["messages"][0]["text"]
    # Must NOT open with advice or diagnostic language
    advice_openers = ("Попробуй", "Тебе нужно", "Советую", "Рекомендую", "Стоит", "Следует")
    assert not any(first_text.startswith(opener) for opener in advice_openers)
    medical_terms = ("диагноз", "лечение", "терапия", "расстройство", "синдром")
    assert not any(term in first_text.lower() for term in medical_terms)


def test_third_turn_returns_session_closure_with_bounded_next_steps(
    client: TestClient, db: Session
) -> None:
    user_id = 2010
    chat_id = 3010

    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Lena"},
            }
        }

    client.post(
        "/api/v1/telegram/webhook",
        json=_payload(
            "Мы снова поссорились, и мне обидно, что он вообще не слышит меня.",
            21,
        ),
    )
    client.post(
        "/api/v1/telegram/webhook",
        json=_payload(
            "Факт в том, что он перебил меня и ушел. По ощущениям мне обидно и тревожно.",
            22,
        ),
    )
    response = client.post(
        "/api/v1/telegram/webhook",
        json=_payload(
            "Наверное, больше всего меня задевает, что это повторяется и я уже не знаю, как говорить спокойно.",
            23,
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "session_closure"
    assert payload["signals"] == ["typing"]
    assert len(payload["messages"]) == 2
    option_lines = payload["messages"][1]["text"].splitlines()
    assert 2 <= len(option_lines) <= 4

    record = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).one()
    assert record.status == "completed"

    summary = db.exec(
        select(SessionSummary).where(SessionSummary.session_id == record.id)
    ).one()
    profile_facts = db.exec(
        select(ProfileFact).where(ProfileFact.telegram_user_id == user_id)
    ).all()
    assert summary.telegram_user_id == user_id
    assert summary.takeaway == payload["messages"][0]["text"]
    assert summary.key_facts
    assert summary.emotional_tensions
    assert summary.next_step_context
    assert summary.retention_scope == "durable_summary"
    assert profile_facts
    assert "Наверное, больше всего меня задевает" not in " ".join(summary.key_facts)
    assert record.last_user_message is None
    assert record.last_bot_prompt is None
    assert record.working_context is None
    assert record.transcript_purged_at is not None


def test_session_closure_fast_mode_stays_compact(
    client: TestClient, db: Session
) -> None:
    user_id = 2011
    chat_id = 3011

    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Nika"},
            }
        }

    client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Мы с партнером поссорились, мне обидно и я устала.", 31),
    )
    record = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).one()
    record.reflective_mode = "fast"
    db.add(record)
    db.commit()

    client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Он просто закрыл разговор, и я теперь застряла в этом.", 32),
    )
    response = client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Наверное, мне сейчас нужен не длинный разбор, а понятная точка.", 33),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "session_closure"
    assert max(len(message["text"]) for message in payload["messages"]) < 280
    assert payload["messages"][1]["text"].count("\n") <= 2

    first_text = payload["messages"][0]["text"]
    # Must NOT open with advice or diagnostic language
    advice_openers = ("Попробуй", "Тебе нужно", "Советую", "Рекомендую", "Стоит", "Следует")
    assert not any(first_text.startswith(opener) for opener in advice_openers)
    medical_terms = ("диагноз", "лечение", "терапия", "расстройство", "синдром")
    assert not any(term in first_text.lower() for term in medical_terms)

    # Closure must not end with an open question — session is marked completed immediately.
    assert not payload["messages"][-1]["text"].rstrip().endswith("?")


def test_low_confidence_first_trust_response_uses_one_follow_up_question(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 15,
                "text": "Все сложно, даже не знаю.",
                "chat": {"id": 3005, "type": "private"},
                "from": {"id": 2005, "is_bot": False, "first_name": "Eva"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "first_trust_response"
    assert len(payload["messages"]) == 2
    combined = " ".join(message["text"] for message in payload["messages"])
    assert combined.count("?") == 1
    assert "не хочу делать вид" in combined


def test_second_turn_clarification_separates_fact_emotion_and_interpretation(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 16,
                "text": "Мы с мужем снова поссорились, и мне обидно, что он меня не слышит.",
                "chat": {"id": 3006, "type": "private"},
                "from": {"id": 2006, "is_bot": False, "first_name": "Ira"},
            }
        },
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 17,
                "text": "Он опять перебил меня и теперь я думаю, что, может, я правда перегнула.",
                "chat": {"id": 3006, "type": "private"},
                "from": {"id": 2006, "is_bot": False, "first_name": "Ira"},
            }
        },
    )

    payload = response.json()
    combined = " ".join(message["text"] for message in payload["messages"])
    assert payload["action"] == "clarification_turn"
    assert "факт" in combined
    assert "по ощущениям" in combined
    assert "интерпретации" in combined
    assert combined.count("?") == 1


def test_fast_mode_clarification_stays_bounded(
    client: TestClient, db: Session
) -> None:
    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 18,
                "text": "Я поругался с коллегой, и меня это сильно задело.",
                "chat": {"id": 3007, "type": "private"},
                "from": {"id": 2007, "is_bot": False, "first_name": "Max"},
            }
        },
    )
    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 2007)
    ).one()
    session.reflective_mode = "fast"
    db.add(session)
    db.commit()

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 19,
                "text": "На совещании он меня перебил, и теперь мне обидно и неприятно.",
                "chat": {"id": 3007, "type": "private"},
                "from": {"id": 2007, "is_bot": False, "first_name": "Max"},
            }
        },
    )

    payload = response.json()
    assert payload["action"] == "clarification_turn"
    assert len(payload["messages"]) == 2
    assert "один главный узел" in payload["messages"][1]["text"]


def test_returning_user_new_session_loads_prior_memory_into_context(
    client: TestClient, db: Session
) -> None:
    user_id = 2012
    chat_id = 3012
    completed_session = TelegramSession(
        id=uuid4(),
        telegram_user_id=user_id,
        chat_id=chat_id,
        status="completed",
    )
    db.add(completed_session)
    db.commit()
    db.add(
        SessionSummary(
            session_id=completed_session.id,
            telegram_user_id=user_id,
            reflective_mode="deep",
            source_turn_count=3,
            takeaway="В прошлой сессии уже было видно, что пользователя особенно задевает повторяемость конфликта.",
            key_facts=["Ситуация воспринимается как повторяющийся паттерн."],
            emotional_tensions=["Повторение конфликта усиливает тревогу и усталость."],
            uncertainty_notes=[],
            next_step_context=["Спокойно назвать, что именно повторяется."],
        )
    )
    db.add(
        ProfileFact(
            telegram_user_id=user_id,
            source_session_id=completed_session.id,
            fact_key="support_preference",
            fact_value="Пользователю полезнее спокойный и уважительный тон.",
        )
    )
    db.commit()

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 34,
                "text": "Мы опять поссорились, и я устала от того, что это снова повторяется.",
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Nina"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "first_trust_response"

    active_session = db.exec(
        select(TelegramSession)
        .where(TelegramSession.telegram_user_id == user_id)
        .where(TelegramSession.status == "active")
    ).one()
    assert active_session.turn_count == 1
    assert active_session.working_context is not None
    assert "повторяемость конфликта" in active_session.working_context
    assert "Мы опять поссорились" in active_session.working_context


def test_returning_user_recall_failure_falls_back_to_clean_session(
    client: TestClient,
) -> None:
    with patch(
        "app.conversation.session_bootstrap.get_session_recall_context",
        side_effect=RuntimeError("db blew up"),
    ):
        response = client.post(
            "/api/v1/telegram/webhook",
            json={
                "message": {
                    "message_id": 35,
                    "text": "Мы с мужем снова поссорились, и мне обидно, что он меня не слышит.",
                    "chat": {"id": 3013, "type": "private"},
                    "from": {"id": 2013, "is_bot": False, "first_name": "Olya"},
                }
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "first_trust_response"
    assert len(payload["messages"]) == 2
    combined = " ".join(message["text"] for message in payload["messages"])
    assert "в прошлый раз" not in combined.lower()
    assert "я помню" not in combined.lower()


def test_returning_user_recall_is_tentative_not_omniscient(
    client: TestClient,
    db: Session,
) -> None:
    user_id = 2015
    chat_id = 3015
    completed_session = TelegramSession(
        telegram_user_id=user_id,
        chat_id=chat_id,
        status="completed",
    )
    db.add(completed_session)
    db.commit()
    db.refresh(completed_session)

    db.add(
        SessionSummary(
            session_id=completed_session.id,
            telegram_user_id=user_id,
            reflective_mode="deep",
            source_turn_count=3,
            takeaway=(
                "В прошлой сессии было видно, что пользователя особенно задевает "
                "повторяемость конфликта."
            ),
            key_facts=["Ситуация воспринимается как повторяющийся паттерн."],
            emotional_tensions=["Повторение конфликта усиливает тревогу."],
            uncertainty_notes=[],
            next_step_context=["Спокойно назвать, что именно повторяется."],
        )
    )
    db.commit()

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 38,
                "text": "Мы опять поссорились, и мне обидно, что меня не слышат.",
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Mila"},
            }
        },
    )

    assert response.status_code == 200
    combined = " ".join(
        message["text"] for message in response.json()["messages"]
    ).lower()
    assert "могу ошибаться" in combined
    assert "знаком" in combined or "не первый раз" in combined
    assert "я точно знаю" not in combined


def test_user_correction_replaces_prior_memory_frame(
    client: TestClient,
    db: Session,
) -> None:
    user_id = 2016
    chat_id = 3016
    completed_session = TelegramSession(
        telegram_user_id=user_id,
        chat_id=chat_id,
        status="completed",
    )
    db.add(completed_session)
    db.commit()
    db.refresh(completed_session)

    db.add(
        SessionSummary(
            session_id=completed_session.id,
            telegram_user_id=user_id,
            reflective_mode="deep",
            source_turn_count=3,
            takeaway=(
                "В прошлой сессии было видно, что пользователя особенно задевает "
                "повторяемость конфликта."
            ),
            key_facts=["Ситуация воспринимается как повторяющийся паттерн."],
            emotional_tensions=["Повторение конфликта усиливает тревогу."],
            uncertainty_notes=[],
            next_step_context=["Спокойно назвать, что именно повторяется."],
        )
    )
    db.commit()

    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 39,
                "text": "Мы опять поссорились, и мне обидно, что меня не слышат.",
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Mila"},
            }
        },
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 40,
                "text": (
                    "Нет, сейчас это не про повторяемость, а про конкретный разговор "
                    "с начальником сегодня."
                ),
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Mila"},
            }
        },
    )

    assert response.status_code == 200
    combined = " ".join(
        message["text"] for message in response.json()["messages"]
    ).lower()
    assert "беру это как текущую рамку" in combined
    assert "повторяем" not in combined

    active_session = db.exec(
        select(TelegramSession)
        .where(TelegramSession.telegram_user_id == user_id)
        .where(TelegramSession.status == "active")
    ).one()
    assert active_session.working_context is not None
    assert "повторяющийся паттерн" not in active_session.working_context.lower()
    assert "конкретный разговор с начальником" in active_session.working_context.lower()


def test_post_correction_third_turn_does_not_reinstate_old_memory_frame(
    client: TestClient,
    db: Session,
) -> None:
    """AC3: After user corrects recall on turn 2, closure on turn 3 must not re-surface old framing."""
    user_id = 2017
    chat_id = 3017
    completed_session = TelegramSession(
        telegram_user_id=user_id,
        chat_id=chat_id,
        status="completed",
    )
    db.add(completed_session)
    db.commit()
    db.refresh(completed_session)

    db.add(
        SessionSummary(
            session_id=completed_session.id,
            telegram_user_id=user_id,
            reflective_mode="deep",
            source_turn_count=3,
            takeaway=(
                "В прошлой сессии было видно, что пользователя особенно задевает "
                "повторяемость конфликта."
            ),
            key_facts=["Ситуация воспринимается как повторяющийся паттерн."],
            emotional_tensions=["Повторение конфликта усиливает тревогу."],
            uncertainty_notes=[],
            next_step_context=["Спокойно назвать, что именно повторяется."],
        )
    )
    db.commit()

    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Mila"},
            }
        }

    # Turn 1: bot surfaces tentative recall
    client.post("/api/v1/telegram/webhook", json=_payload(
        "Мы опять поссорились, и мне обидно, что меня не слышат.", 41
    ))
    # Turn 2: user explicitly corrects the recall framing
    client.post("/api/v1/telegram/webhook", json=_payload(
        "Нет, это не про повторяемость, а про конкретный разговор с начальником сегодня.", 42
    ))
    # Turn 3: session closes — old memory phrase must NOT appear in the closure summary
    response = client.post("/api/v1/telegram/webhook", json=_payload(
        "Он просто перебил меня на встрече и ушёл.", 43
    ))

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "session_closure"
    combined = " ".join(message["text"] for message in payload["messages"]).lower()
    # The specific prior-session memory phrase must not appear in the closure
    assert "повторяемость конфликта" not in combined
    # The explicit recall cue must not be repeated after correction
    assert "знакомый для тебя узел" not in combined


def test_active_session_second_turn_does_not_reload_prior_memory(
    client: TestClient,
) -> None:
    first_payload = {
        "message": {
            "message_id": 36,
            "text": "Мы снова поссорились, и мне обидно, что он меня не слышит.",
            "chat": {"id": 3014, "type": "private"},
            "from": {"id": 2014, "is_bot": False, "first_name": "Mila"},
        }
    }
    second_payload = {
        "message": {
            "message_id": 37,
            "text": "Он опять перебил меня, и я уже начинаю злиться.",
            "chat": {"id": 3014, "type": "private"},
            "from": {"id": 2014, "is_bot": False, "first_name": "Mila"},
        }
    }

    client.post("/api/v1/telegram/webhook", json=first_payload)
    with patch("app.conversation.session_bootstrap.get_session_recall_context") as recall_mock:
        response = client.post("/api/v1/telegram/webhook", json=second_payload)

    assert response.status_code == 200
    assert response.json()["action"] == "clarification_turn"
    recall_mock.assert_not_called()


def test_deep_mode_clarification_goes_one_layer_deeper(
    client: TestClient, db: Session
) -> None:
    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 190,
                "text": "Мы снова поссорились, и мне обидно, что меня не слышат.",
                "chat": {"id": 3090, "type": "private"},
                "from": {"id": 2090, "is_bot": False, "first_name": "Mira"},
            }
        },
    )
    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 2090)
    ).one()
    session.reflective_mode = "deep"
    db.add(session)
    db.commit()

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 191,
                "text": (
                    "Он снова перебил меня на встрече, и я начинаю думать, "
                    "что мои слова для него ничего не значат."
                ),
                "chat": {"id": 3090, "type": "private"},
                "from": {"id": 2090, "is_bot": False, "first_name": "Mira"},
            }
        },
    )

    payload = response.json()
    assert payload["action"] == "clarification_turn"
    assert len(payload["messages"]) == 2
    assert "Если пойти на слой глубже" in payload["messages"][1]["text"]


def test_vague_contradictory_clarification_uses_tentative_wording(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 192,
                "text": "Мы снова вернулись к этому разговору, и меня уже качает от него.",
                "chat": {"id": 3091, "type": "private"},
                "from": {"id": 2091, "is_bot": False, "first_name": "Lia"},
            }
        },
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 193,
                "text": "Я как будто и злюсь, и не понимаю, права ли я вообще, но все смешалось.",
                "chat": {"id": 3091, "type": "private"},
                "from": {"id": 2091, "is_bot": False, "first_name": "Lia"},
            }
        },
    )

    payload = response.json()
    combined = " ".join(message["text"] for message in payload["messages"])
    assert payload["action"] == "clarification_turn"
    assert len(payload["messages"]) == 2
    assert combined.count("?") == 1
    assert "не хочу делать слишком уверенные выводы" in combined or "ещё не до конца сложилась" in combined


def test_work_and_technology_context_remain_in_scope(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 194,
                "text": "Я поругался с начальником, и меня это задело.",
                "chat": {"id": 3092, "type": "private"},
                "from": {"id": 2092, "is_bot": False, "first_name": "Oleg"},
            }
        },
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 195,
                "text": (
                    "Это было из-за технологического проекта и денег команды, "
                    "и мне обидно, что мой вклад как будто обнулили."
                ),
                "chat": {"id": 3092, "type": "private"},
                "from": {"id": 2092, "is_bot": False, "first_name": "Oleg"},
            }
        },
    )

    payload = response.json()
    combined = " ".join(message["text"] for message in payload["messages"])
    assert payload["action"] == "clarification_turn"
    assert "технологическая тема стала частью живой ситуации" in combined
    assert "общего помощника" not in combined


def test_boundary_response_for_general_assistant_pivot(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 20,
                "text": "Мне тяжело после разговора, я до сих пор злюсь.",
                "chat": {"id": 3008, "type": "private"},
                "from": {"id": 2008, "is_bot": False, "first_name": "Nika"},
            }
        },
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 21,
                "text": "Ладно, тогда просто напиши код калькулятора на python.",
                "chat": {"id": 3008, "type": "private"},
                "from": {"id": 2008, "is_bot": False, "first_name": "Nika"},
            }
        },
    )

    payload = response.json()
    assert payload["action"] == "clarification_boundary"
    assert "общего помощника" in payload["messages"][0]["text"]


def test_third_turn_low_confidence_closure_does_not_end_with_question(
    client: TestClient, db: Session
) -> None:
    """Low-confidence closure must NOT end with an open question.

    The session is marked completed after closure, so any trailing question
    would leave the user with an unanswerable prompt — their next message
    would start a fresh unrelated session.
    """
    user_id = 2019
    chat_id = 3019

    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Vera"},
            }
        }

    client.post("/api/v1/telegram/webhook", json=_payload(
        "Мы с мужем поссорились, мне обидно.", 51
    ))
    client.post("/api/v1/telegram/webhook", json=_payload(
        "Он меня перебил, и я не знаю как на это реагировать.", 52
    ))
    response = client.post("/api/v1/telegram/webhook", json=_payload(
        "Не уверена, что вообще правильно понимаю, что произошло.", 53
    ))

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "session_closure"

    last_message = payload["messages"][-1]["text"].rstrip()
    assert not last_message.endswith("?"), (
        "Closure must not end with an open question when session is marked completed"
    )

    record = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).one()
    assert record.status == "completed"


def test_work_context_is_not_treated_as_off_topic(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 22,
                "text": "Я запутался после разговора с начальником.",
                "chat": {"id": 3009, "type": "private"},
                "from": {"id": 2009, "is_bot": False, "first_name": "Oleg"},
            }
        },
    )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 23,
                "text": "На работе мне сказали переделать проект, и теперь я думаю, что меня просто не ценят.",
                "chat": {"id": 3009, "type": "private"},
                "from": {"id": 2009, "is_bot": False, "first_name": "Oleg"},
            }
        },
    )

    payload = response.json()
    assert payload["action"] == "clarification_turn"
    assert "работе" in payload["messages"][0]["text"]


def test_start_does_not_include_mode_selection_buttons(client: TestClient) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 60,
                "text": "/start",
                "chat": {"id": 5001, "type": "private"},
                "from": {"id": 4001, "is_bot": False, "first_name": "Nina"},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "brainstorm_autostart"
    assert payload["inline_keyboard"] == []


def test_mode_selection_fast_via_callback(client: TestClient, db: Session) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "callback_query": {
                "id": "cbq-200",
                "data": "mode:fast",
                "from": {"id": 4002, "is_bot": False, "first_name": "Kate"},
                "message": {"message_id": 61, "chat": {"id": 5002, "type": "private"}},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["action"] == "mode_selected"

    record = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 4002)
    ).one()
    assert record.reflective_mode == "fast"
    assert record.mode_source == "explicit"


def test_mode_selection_deep_via_callback(client: TestClient, db: Session) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "callback_query": {
                "id": "cbq-201",
                "data": "mode:deep",
                "from": {"id": 4003, "is_bot": False, "first_name": "Leo"},
                "message": {"message_id": 62, "chat": {"id": 5003, "type": "private"}},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["action"] == "mode_selected"

    record = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 4003)
    ).one()
    assert record.reflective_mode == "deep"
    assert record.mode_source == "explicit"


def test_mode_selection_invalid_callback_falls_back_gracefully(
    client: TestClient, db: Session
) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "callback_query": {
                "id": "cbq-202",
                "data": "mode:unknown",
                "from": {"id": 4004, "is_bot": False, "first_name": "Sam"},
                "message": {"message_id": 63, "chat": {"id": 5004, "type": "private"}},
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["action"] == "mode_selected"

    record = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 4004)
    ).one()
    assert record.reflective_mode == "deep"
    assert record.mode_source == "fallback"


class _FakeBackgroundTasks:
    def __init__(self) -> None:
        self.calls: list[tuple[object, tuple[object, ...], dict[str, object]]] = []

    def add_task(self, func: object, *args: object, **kwargs: object) -> None:
        self.calls.append((func, args, kwargs))


@pytest.mark.anyio
async def test_closure_schedules_summary_background_task_without_blocking_response(
    db: Session,
) -> None:
    user_id = 5010
    chat_id = 6010

    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Lena"},
            }
        }

    await handle_session_entry(db, _payload("Мы снова поссорились, и мне обидно.", 1))
    await handle_session_entry(db, _payload("Он перебил меня и ушел.", 2))

    background_tasks = _FakeBackgroundTasks()
    response = await handle_session_entry(
        db,
        _payload("Больше всего меня ранит, что это повторяется.", 3),
        background_tasks=cast(Any, background_tasks),
    )

    assert response.action == "session_closure"
    assert len(background_tasks.calls) == 1

    scheduled_func, scheduled_args, scheduled_kwargs = background_tasks.calls[0]
    assert callable(scheduled_func)
    assert not scheduled_kwargs
    assert len(scheduled_args) == 1


def test_summary_generation_failure_creates_visible_signal_without_breaking_reply(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = 5011
    chat_id = 6011

    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Rita"},
            }
        }

    def _raise_persist_error(_payload: object, _draft: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("app.memory.service.persist_session_summary", _raise_persist_error)

    client.post("/api/v1/telegram/webhook", json=_payload("Мы снова поссорились.", 71))
    client.post("/api/v1/telegram/webhook", json=_payload("Он перебил меня и ушел.", 72))
    response = client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Я не уверена, что правильно это понимаю.", 73),
    )

    assert response.status_code == 200
    assert response.json()["action"] == "session_closure"

    record = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).one()
    assert record.status == "completed"

    assert (
        db.exec(select(SessionSummary).where(SessionSummary.session_id == record.id)).first()
        is None
    )
    signal = db.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.session_id == record.id
        )
    ).one()
    assert signal.signal_type == "session_summary_failed"
    assert signal.retryable is True
    assert signal.details["suggested_action"] == "retry_session_memory_persistence"
    assert signal.retry_payload["summary_draft"]["takeaway"]
    assert record.last_user_message is None
    assert record.last_bot_prompt is None
    assert record.working_context is None


def test_sensitive_session_closure_keeps_standard_recall_conservative(
    client: TestClient, db: Session
) -> None:
    user_id = 5012
    chat_id = 6012

    def _payload(text: str, message_id: int) -> dict[str, object]:
        return {
            "message": {
                "message_id": message_id,
                "text": text,
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "is_bot": False, "first_name": "Sasha"},
            }
        }

    client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Мне страшно после того, что произошло дома.", 81),
    )
    client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Там было насилие, и я до сих пор не могу прийти в себя.", 82),
    )
    response = client.post(
        "/api/v1/telegram/webhook",
        json=_payload("Иногда кажется, что лучше исчезнуть, чем снова это переживать.", 83),
    )

    assert response.status_code == 200
    assert response.json()["action"] == "crisis_routed"
    assert "crisis_mode_active" in response.json()["signals"]

    session = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == user_id)
    ).one()
    assert session.crisis_state == "crisis_active"
    assert (
        db.exec(select(SessionSummary).where(SessionSummary.telegram_user_id == user_id)).first()
        is None
    )
    assert (
        db.exec(select(ProfileFact).where(ProfileFact.telegram_user_id == user_id)).all()
        == []
    )


def test_help_button_returns_phase_guide_without_resetting_session(
    client: TestClient, db: Session
) -> None:
    from unittest.mock import patch
    # Start a session
    client.post(
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
    # Advance to collect_goal by sending a topic
    with patch("app.conversation.brainstorming.orchestrator._ask_openai", return_value="Какова цель?"):
        client.post(
            "/api/v1/telegram/webhook",
            json={
                "message": {
                    "message_id": 2,
                    "text": "Карьерный рост",
                    "chat": {"id": 2001, "type": "private"},
                    "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
                }
            },
        )

    session_row = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1001)
    ).one()
    phase_before = session_row.brainstorm_phase

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 3,
                "text": "❓ Помощь",
                "chat": {"id": 2001, "type": "private"},
                "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
            }
        },
    )

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["action"] == "help_shown"
    assert len(payload["messages"]) == 1
    assert "Как работает мозговой штурм" in payload["messages"][0]["text"]

    db.refresh(session_row)
    assert session_row.brainstorm_phase == phase_before


def test_reset_button_resets_session_like_start(
    client: TestClient, db: Session
) -> None:
    from unittest.mock import patch
    # Create and advance a session
    client.post(
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
    with patch("app.conversation.brainstorming.orchestrator._ask_openai", return_value="Какова цель?"):
        client.post(
            "/api/v1/telegram/webhook",
            json={
                "message": {
                    "message_id": 2,
                    "text": "Карьерный рост",
                    "chat": {"id": 2001, "type": "private"},
                    "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
                }
            },
        )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 3,
                "text": "🔄 Начать заново",
                "chat": {"id": 2001, "type": "private"},
                "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
            }
        },
    )

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["action"] == "brainstorm_reset"
    assert payload["messages"][0]["text"] == OPENING_PROMPT
    markup = payload["reply_markup"]
    assert markup is not None
    button_texts = [btn["text"] for btn in markup["keyboard"][0]]
    assert "🔄 Начать заново" in button_texts

    session_row = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1001)
    ).one()
    assert session_row.brainstorm_phase == "collect_topic"
    assert session_row.brainstorm_data["ideas"] == []
