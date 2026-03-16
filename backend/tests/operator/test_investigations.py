import uuid
from datetime import datetime, timezone

import pytest
from pytest import MonkeyPatch
from sqlmodel import Session, select

from app.models import (
    OperatorAlert,
    OperatorInvestigation,
    SummaryGenerationSignal,
    TelegramSession,
)
from app.ops.investigations import (
    InvestigationConflictError,
    InvestigationContextError,
    InvestigationStateError,
    close_operator_investigation,
    deny_operator_investigation,
    request_and_open_operator_investigation,
)


def test_request_and_open_operator_investigation_creates_auditable_record(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("1fc8af58-1af2-4f3a-a64d-38936b2d57b4"),
        telegram_user_id=7201,
        chat_id=8201,
        crisis_state="crisis_active",
        last_user_message="Мне очень плохо и я боюсь, что сорвусь.",
        last_bot_prompt="Похоже, сейчас нужна более безопасная поддержка.",
        crisis_activated_at=datetime.now(timezone.utc),
        crisis_last_routed_at=datetime.now(timezone.utc),
    )
    alert = OperatorAlert(
        id=uuid.UUID("7545cf80-a0ea-4d2e-b553-f73f580eaf86"),
        session_id=session_record.id,
        telegram_user_id=7201,
        classification="crisis",
        trigger_category="self_harm",
        confidence="high",
        status="delivered",
        payload={
            "classification": "crisis",
            "trigger_category": "self_harm",
            "confidence": "high",
        },
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    db.add(alert)
    db.commit()

    investigation = request_and_open_operator_investigation(
        db,
        operator_alert_id=alert.id,
        reason_code="critical_safety_review",
        requested_by="ops:token",
        approved_by="ops:token",
        audit_notes="Need bounded review of the current crisis turn.",
    )

    assert investigation.operator_alert_id == alert.id
    assert investigation.session_id == session_record.id
    assert investigation.telegram_user_id == 7201
    assert investigation.reason_code == "critical_safety_review"
    assert investigation.status == "opened"
    assert investigation.requested_by == "ops:token"
    assert investigation.approved_by == "ops:token"
    assert investigation.requested_at is not None
    assert investigation.approved_at is not None
    assert investigation.opened_at is not None
    assert investigation.closed_at is None
    assert investigation.context_payload["alert"]["classification"] == "crisis"
    assert investigation.context_payload["current_turn"]["last_user_message"] == (
        "Мне очень плохо и я боюсь, что сорвусь."
    )
    assert "working_context" not in investigation.context_payload


def test_close_operator_investigation_preserves_reviewed_classification(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("d2ab36c8-5aa7-4c81-8aae-0eb99aa67c7b"),
        telegram_user_id=7202,
        chat_id=8202,
        crisis_state="crisis_active",
    )
    alert = OperatorAlert(
        id=uuid.UUID("8dd5ec60-6af7-4aad-9001-a01477e44e4c"),
        session_id=session_record.id,
        telegram_user_id=7202,
        classification="crisis",
        trigger_category="self_harm",
        confidence="high",
        status="delivered",
        payload={},
    )
    db.add(session_record)
    db.commit()
    db.add(alert)
    db.commit()

    investigation = OperatorInvestigation(
        id=uuid.UUID("20ca217f-861e-4817-bcac-b8e2e9e52189"),
        operator_alert_id=alert.id,
        session_id=session_record.id,
        telegram_user_id=7202,
        status="opened",
        reason_code="critical_safety_review",
        requested_by="ops:token",
        approved_by="ops:token",
        requested_at=datetime.now(timezone.utc),
        approved_at=datetime.now(timezone.utc),
        opened_at=datetime.now(timezone.utc),
        source_classification="crisis",
        source_trigger_category="self_harm",
        source_confidence="high",
        context_payload={"alert": {"classification": "crisis"}},
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)

    closed = close_operator_investigation(
        db,
        investigation_id=investigation.id,
        reviewed_by="ops:reviewer",
        reviewed_classification="borderline",
        outcome="false_positive",
        audit_notes="Context suggests risk was overstated.",
    )

    assert closed.status == "closed"
    assert closed.reviewed_by == "ops:reviewer"
    assert closed.reviewed_classification == "borderline"
    assert closed.outcome == "false_positive"
    assert closed.audit_notes == "Context suggests risk was overstated."
    assert closed.closed_at is not None
    assert closed.source_classification == "crisis"


def test_deny_operator_investigation_sets_explicit_denied_state(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("b6809dc8-b4d8-4544-8d64-49f1f2b2fb1e"),
        telegram_user_id=7203,
        chat_id=8203,
        crisis_state="crisis_active",
    )
    alert = OperatorAlert(
        id=uuid.UUID("5ac65ca5-8f4a-436f-a6c8-eb9eed95b383"),
        session_id=session_record.id,
        telegram_user_id=7203,
        classification="borderline",
        trigger_category="self_harm",
        confidence="medium",
        status="delivered",
        payload={},
    )
    db.add(session_record)
    db.commit()
    db.add(alert)
    db.commit()

    investigation = OperatorInvestigation(
        id=uuid.UUID("10f03dd8-851f-4a5d-8c87-9f641fc33306"),
        operator_alert_id=alert.id,
        session_id=session_record.id,
        telegram_user_id=7203,
        status="requested",
        reason_code="operator_training_review",
        requested_by="ops:trainee",
        requested_at=datetime.now(timezone.utc),
        source_classification="borderline",
        source_trigger_category="self_harm",
        source_confidence="medium",
        context_payload={},
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)

    denied = deny_operator_investigation(
        db,
        investigation_id=investigation.id,
        denied_by="ops:lead",
        audit_notes="Reason code not sufficient for exceptional access.",
    )

    assert denied.status == "denied"
    assert denied.approved_by is None
    assert denied.audit_notes is not None
    assert "denied_by:ops:lead" in denied.audit_notes
    assert "Reason code not sufficient for exceptional access." in denied.audit_notes
    assert denied.closed_at is not None


def test_request_and_open_operator_investigation_records_failure_signal_when_context_build_fails(
    db: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("e94d919b-9ce6-4404-b650-7a7f4763940d"),
        telegram_user_id=7204,
        chat_id=8204,
        crisis_state="crisis_active",
    )
    alert = OperatorAlert(
        id=uuid.UUID("f034395c-12d6-48d9-b5e6-f8df7c4f18b2"),
        session_id=session_record.id,
        telegram_user_id=7204,
        classification="borderline",
        trigger_category="self_harm",
        confidence="medium",
        status="delivered",
        payload={},
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    db.add(alert)
    db.commit()

    def _raise_context_error(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise InvestigationContextError("context unavailable")

    monkeypatch.setattr(
        "app.ops.investigations._build_investigation_context_payload",
        _raise_context_error,
    )

    investigation = request_and_open_operator_investigation(
        db,
        operator_alert_id=alert.id,
        reason_code="critical_safety_review",
        requested_by="ops:token",
        approved_by="ops:token",
    )

    assert investigation.status == "failed"
    assert investigation.context_payload == {}
    signal = db.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.session_id == session_record.id
        )
    ).one()
    assert signal.signal_type == "operator_investigation_context_failed"
    assert signal.details["failure_stage"] == "ops_investigation"


def test_deny_operator_investigation_records_denier_in_audit_notes_not_approved_by(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("a1b2c3d4-0001-4000-8000-000000000001"),
        telegram_user_id=7205,
        chat_id=8205,
        crisis_state="crisis_active",
    )
    alert = OperatorAlert(
        id=uuid.UUID("a1b2c3d4-0002-4000-8000-000000000002"),
        session_id=session_record.id,
        telegram_user_id=7205,
        classification="borderline",
        trigger_category="self_harm",
        confidence="medium",
        status="delivered",
        payload={},
    )
    db.add(session_record)
    db.commit()
    db.add(alert)
    db.commit()

    investigation = OperatorInvestigation(
        id=uuid.UUID("a1b2c3d4-0003-4000-8000-000000000003"),
        operator_alert_id=alert.id,
        session_id=session_record.id,
        telegram_user_id=7205,
        status="requested",
        reason_code="operator_training_review",
        requested_by="ops:trainee",
        requested_at=datetime.now(timezone.utc),
        source_classification="borderline",
        source_trigger_category="self_harm",
        source_confidence="medium",
        context_payload={},
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)

    denied = deny_operator_investigation(
        db,
        investigation_id=investigation.id,
        denied_by="ops:lead",
        audit_notes="Not a sufficient reason code for exceptional access.",
    )

    assert denied.status == "denied"
    assert denied.approved_by is None  # must NOT be set — that would corrupt audit trail
    assert denied.audit_notes is not None
    assert "denied_by:ops:lead" in denied.audit_notes
    assert "Not a sufficient reason code" in denied.audit_notes
    assert denied.closed_at is not None


def test_close_operator_investigation_raises_on_non_opened_status(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("a1b2c3d4-0004-4000-8000-000000000004"),
        telegram_user_id=7206,
        chat_id=8206,
        crisis_state="crisis_active",
    )
    alert = OperatorAlert(
        id=uuid.UUID("a1b2c3d4-0005-4000-8000-000000000005"),
        session_id=session_record.id,
        telegram_user_id=7206,
        classification="crisis",
        trigger_category="self_harm",
        confidence="high",
        status="delivered",
        payload={},
    )
    db.add(session_record)
    db.commit()
    db.add(alert)
    db.commit()

    investigation = OperatorInvestigation(
        id=uuid.UUID("a1b2c3d4-0006-4000-8000-000000000006"),
        operator_alert_id=alert.id,
        session_id=session_record.id,
        telegram_user_id=7206,
        status="denied",
        reason_code="critical_safety_review",
        requested_by="ops:token",
        requested_at=datetime.now(timezone.utc),
        source_classification="crisis",
        source_trigger_category="self_harm",
        source_confidence="high",
        context_payload={},
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)

    with pytest.raises(InvestigationStateError, match="investigation_not_closeable"):
        close_operator_investigation(
            db,
            investigation_id=investigation.id,
            reviewed_by="ops:reviewer",
            reviewed_classification="false_positive",
            outcome="false_positive",
        )


def test_request_and_open_raises_conflict_when_open_investigation_exists(
    db: Session,
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("a1b2c3d4-0007-4000-8000-000000000007"),
        telegram_user_id=7207,
        chat_id=8207,
        crisis_state="crisis_active",
    )
    alert = OperatorAlert(
        id=uuid.UUID("a1b2c3d4-0008-4000-8000-000000000008"),
        session_id=session_record.id,
        telegram_user_id=7207,
        classification="crisis",
        trigger_category="self_harm",
        confidence="high",
        status="delivered",
        payload={},
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    db.add(alert)
    db.commit()

    existing_investigation = OperatorInvestigation(
        id=uuid.UUID("a1b2c3d4-0009-4000-8000-000000000009"),
        operator_alert_id=alert.id,
        session_id=session_record.id,
        telegram_user_id=7207,
        status="opened",
        reason_code="critical_safety_review",
        requested_by="ops:token",
        approved_by="ops:token",
        requested_at=datetime.now(timezone.utc),
        approved_at=datetime.now(timezone.utc),
        opened_at=datetime.now(timezone.utc),
        source_classification="crisis",
        source_trigger_category="self_harm",
        source_confidence="high",
        context_payload={},
    )
    db.add(existing_investigation)
    db.commit()

    with pytest.raises(InvestigationConflictError, match="investigation_already_open"):
        request_and_open_operator_investigation(
            db,
            operator_alert_id=alert.id,
            reason_code="critical_safety_review",
            requested_by="ops:token",
            approved_by="ops:token",
        )
