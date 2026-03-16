import uuid

from pytest import MonkeyPatch
from sqlmodel import Session, select

from app.models import OperatorAlert, TelegramSession
from app.ops.alerts import AlertDeliveryError, create_and_deliver_operator_alert
from app.safety.service import SafetyAssessment


def test_create_and_deliver_operator_alert_persists_bounded_payload(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("f38f8d8d-0f2e-4808-a9fb-7be6f38410aa"),
        telegram_user_id=7101,
        chat_id=8101,
        crisis_state="crisis_active",
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)

    alert = create_and_deliver_operator_alert(
        db,
        session_record=session_record,
        assessment=SafetyAssessment(
            classification="crisis",
            trigger_category="self_harm",
            confidence="high",
            blocks_normal_flow=True,
        ),
        newly_activated=True,
    )

    assert alert.telegram_user_id == 7101
    assert alert.session_id == session_record.id
    assert alert.status == "delivered"
    assert alert.classification == "crisis"
    assert alert.trigger_category == "self_harm"
    assert alert.confidence == "high"
    assert alert.delivery_channel == "ops_inbox"
    assert alert.delivery_attempt_count == 1
    assert alert.last_delivery_error is None
    assert alert.payload["classification"] == "crisis"
    assert alert.payload["trigger_category"] == "self_harm"
    assert alert.payload["confidence"] == "high"
    assert "last_user_message" not in alert.payload
    assert "working_context" not in alert.payload
    assert "last_bot_prompt" not in alert.payload


def test_repeated_crisis_routing_updates_existing_alert_instead_of_creating_duplicate(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("52fc1610-e6a8-45b0-9739-098be2023563"),
        telegram_user_id=7102,
        chat_id=8102,
        crisis_state="crisis_active",
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)

    first = create_and_deliver_operator_alert(
        db,
        session_record=session_record,
        assessment=SafetyAssessment(
            classification="crisis",
            trigger_category="self_harm",
            confidence="high",
            blocks_normal_flow=True,
        ),
        newly_activated=True,
    )
    second = create_and_deliver_operator_alert(
        db,
        session_record=session_record,
        assessment=SafetyAssessment(
            classification="crisis",
            trigger_category="self_harm",
            confidence="high",
            blocks_normal_flow=True,
        ),
        newly_activated=False,
    )

    alerts = db.exec(
        select(OperatorAlert).where(OperatorAlert.session_id == session_record.id)
    ).all()
    assert len(alerts) == 1
    assert first.id == second.id
    assert second.delivery_attempt_count == 2
    assert second.last_delivery_error is None


def test_delivery_failure_keeps_alert_record_and_marks_failure_state(
    db: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("0ecfe7a2-eb57-4744-8ae2-6bb39b90a65d"),
        telegram_user_id=7103,
        chat_id=8103,
        crisis_state="crisis_active",
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)

    def _raise_delivery(*_args: object, **_kwargs: object) -> None:
        raise AlertDeliveryError("ops inbox unavailable")

    monkeypatch.setattr("app.ops.alerts._deliver_to_ops_inbox", _raise_delivery)

    alert = create_and_deliver_operator_alert(
        db,
        session_record=session_record,
        assessment=SafetyAssessment(
            classification="borderline",
            trigger_category="self_harm",
            confidence="medium",
            blocks_normal_flow=False,
        ),
        newly_activated=True,
    )

    assert alert.status == "delivery_failed"
    assert alert.delivery_attempt_count == 1
    assert "ops inbox unavailable" in (alert.last_delivery_error or "")
