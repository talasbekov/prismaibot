import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlmodel import Session

from app.memory.schemas import ProfileFactInput, SessionSummaryPayload
from app.memory.service import build_session_summary, persist_session_summary
from app.models import (
    DeletionRequest,
    OperatorAlert,
    OperatorInvestigation,
    ProfileFact,
    SafetySignal,
    SessionSummary,
    TelegramSession,
)
from app.ops import api as ops_api


def test_healthz(client: TestClient) -> None:
    response = client.get("/api/v1/ops/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_check_requires_ops_token(client: TestClient) -> None:
    response = client.get("/api/v1/ops/auth-check")

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_ops_auth_token"


def test_auth_check_accepts_valid_ops_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/ops/auth-check",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "scope": "ops"}


def test_readyz(client: TestClient, monkeypatch: MonkeyPatch) -> None:
    # Ensure settings are configured for the test
    monkeypatch.setattr("app.ops.health.settings.POSTGRES_SERVER", "server")
    monkeypatch.setattr("app.ops.health.settings.POSTGRES_USER", "user")
    monkeypatch.setattr("app.ops.health.settings.POSTGRES_DB", "db")

    response = client.get("/api/v1/ops/readyz")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ready"
    assert payload["service"] == "telegram-first-backend"
    assert payload["database_configured"] is True
    assert payload["database_reachable"] is True


def test_readyz_returns_503_when_database_probe_fails(
    client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    # Ensure settings are configured for the test
    monkeypatch.setattr("app.ops.health.settings.POSTGRES_SERVER", "server")
    monkeypatch.setattr("app.ops.health.settings.POSTGRES_USER", "user")
    monkeypatch.setattr("app.ops.health.settings.POSTGRES_DB", "db")

    class BrokenConnection:
        def __enter__(self) -> "BrokenConnection":
            raise RuntimeError("db unavailable")

        def __exit__(
            self, exc_type: object, exc: object, tb: object
        ) -> Literal[False]:
            return False

    class BrokenEngine:
        def connect(self) -> BrokenConnection:
            return BrokenConnection()

    monkeypatch.setattr(ops_api, "engine", BrokenEngine())

    response = client.get("/api/v1/ops/readyz")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["service"] == "telegram-first-backend"
    assert payload["database_configured"] is True
    assert payload["database_reachable"] is False


def test_readyz_returns_503_when_database_not_configured(
    client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    # Use string path to avoid mypy "not explicitly exported" error
    monkeypatch.setattr("app.ops.health.settings.POSTGRES_SERVER", None)

    response = client.get("/api/v1/ops/readyz")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["database_configured"] is False
    assert payload["database_reachable"] is False


def test_operational_status_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/ops/status")
    assert response.status_code == 401


def test_operational_status_returns_signal_structure(client: TestClient) -> None:
    response = client.get(
        "/api/v1/ops/status",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "session_activity" in data
    assert "total_active" in data["session_activity"]
    assert "total_crisis_active" in data["session_activity"]
    assert "open_summary_failure_signals" in data
    assert "undelivered_operator_alerts" in data
    assert "pending_deletion_requests" in data
    assert "payment_signals" in data
    assert "failed" in data["payment_signals"]
    assert "degraded_fields" in data
    assert isinstance(data["degraded_fields"], list)
    # Verify no PII fields exposed
    assert "working_context" not in data
    assert "last_user_message" not in data


def test_continuity_overview_returns_transcript_free_memory_view(
    client: TestClient, db: Session
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
        telegram_user_id=9901,
        chat_id=8801,
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)

    payload = SessionSummaryPayload(
        session_id=session_record.id,
        telegram_user_id=9901,
        reflective_mode="deep",
        source_turn_count=3,
        prior_context="Мы снова спорим с начальником.",
        latest_user_message="Мне важно, чтобы меня дослушивали.",
        takeaway="Больше всего задевает, когда вклад пользователя обнуляют.",
        next_steps=["1. Зафиксировать, в какой момент разговор сорвался."],
        allowed_profile_facts=[
            ProfileFactInput(
                fact_key="work_context",
                fact_value="Напряжение пользователя регулярно связано с рабочими разговорами.",
            )
        ],
    )
    persist_session_summary(payload, build_session_summary(payload))

    response = client.get(
        "/api/v1/ops/continuity/9901",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["error"] is None
    assert payload["data"]["telegram_user_id"] == 9901
    assert payload["data"]["summaries"]
    assert payload["data"]["profile_facts"]
    dumped = response.text
    assert "last_user_message" not in dumped
    assert "working_context" not in dumped


def test_continuity_overview_returns_404_for_missing_user(client: TestClient) -> None:
    response = client.get(
        "/api/v1/ops/continuity/123456",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "continuity_not_found"


def test_continuity_overview_requires_ops_token(client: TestClient) -> None:
    response = client.get("/api/v1/ops/continuity/123456")

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_ops_auth_token"


def test_continuity_overview_hides_restricted_profile_facts(
    client: TestClient, db: Session
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("d4246378-9b36-4eaf-9458-9ba4456cc4ff"),
        telegram_user_id=9902,
        chat_id=8802,
        status="completed",
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)

    db.add(
        SessionSummary(
            session_id=session_record.id,
            telegram_user_id=9902,
            reflective_mode="deep",
            source_turn_count=3,
            takeaway="Пользователю особенно нужен спокойный и ясный разговор.",
            key_facts=["Напряжение связано с тяжелой личной ситуацией."],
            emotional_tensions=["Сессия была эмоционально тяжелой."],
            uncertainty_notes=[],
            next_step_context=[],
        )
    )
    db.add(
        ProfileFact(
            telegram_user_id=9902,
            source_session_id=session_record.id,
            fact_key="support_preference",
            fact_value="Пользователю полезнее спокойный и уважительный тон.",
            confidence="high",
            retention_scope="restricted_profile",
        )
    )
    db.commit()

    response = client.get(
        "/api/v1/ops/continuity/9902",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["error"] is None
    assert payload["data"]["summaries"]
    assert payload["data"]["profile_facts"] == []


def test_alerts_endpoint_returns_bounded_operator_alerts(
    client: TestClient, db: Session
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("8b170822-fe07-4d09-8339-e284e2b1a90f"),
        telegram_user_id=9903,
        chat_id=8803,
        crisis_state="crisis_active",
    )
    db.add(session_record)
    db.commit()

    db.add(
        OperatorAlert(
            session_id=session_record.id,
            telegram_user_id=9903,
            classification="crisis",
            trigger_category="self_harm",
            confidence="high",
            delivery_channel="ops_inbox",
            status="delivered",
            payload={
                "classification": "crisis",
                "trigger_category": "self_harm",
                "confidence": "high",
            },
        )
    )
    db.commit()

    response = client.get(
        "/api/v1/ops/alerts",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["error"] is None
    assert payload["data"]
    dumped = response.text
    assert "last_user_message" not in dumped
    assert "working_context" not in dumped
    assert "last_bot_prompt" not in dumped


def test_alerts_endpoint_requires_ops_token(client: TestClient) -> None:
    response = client.get("/api/v1/ops/alerts")

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_ops_auth_token"


def test_deletion_requests_endpoint_returns_pending_requests(
    client: TestClient, db: Session
) -> None:
    db.add(DeletionRequest(telegram_user_id=9910, status="pending"))
    db.add(DeletionRequest(telegram_user_id=9911, status="completed"))
    db.commit()

    response = client.get(
        "/api/v1/ops/deletion-requests",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["error"] is None
    # Filter for our specific user in case of shared test DB
    pending_users = [req["telegram_user_id"] for req in payload["data"]]
    assert 9910 in pending_users
    assert 9911 not in pending_users


def test_deletion_requests_endpoint_requires_ops_token(client: TestClient) -> None:
    response = client.get("/api/v1/ops/deletion-requests")

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_ops_auth_token"


def test_execute_deletion_endpoint_requires_ops_token(client: TestClient) -> None:
    response = client.post(f"/api/v1/ops/deletion-requests/{uuid.uuid4()}/execute")

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_ops_auth_token"


def test_execute_deletion_endpoint_successfully_executes(
    client: TestClient, db: Session
) -> None:
    uid = 9912
    # Setup: create TelegramSession and DeletionRequest
    ts = TelegramSession(telegram_user_id=uid, chat_id=uid, working_context="secret")
    db.add(ts)
    db.commit()
    db.refresh(ts)

    req = DeletionRequest(telegram_user_id=uid, status="pending")
    db.add(req)
    db.commit()
    db.refresh(req)

    # Setup: create some artifacts
    db.add(SessionSummary(session_id=ts.id, telegram_user_id=uid, takeaway="test"))
    db.commit()

    response = client.post(
        f"/api/v1/ops/deletion-requests/{req.id}/execute",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["error"] is None
    assert payload["data"]["status"] == "completed"
    assert payload["data"]["summaries_deleted"] == 1
    assert payload["data"]["sessions_purged"] == 1

    # Verify DB
    db.refresh(req)
    assert req.status == "completed"
    db.refresh(ts)
    assert ts.working_context is None


def test_execute_deletion_endpoint_returns_404_for_missing_request(
    client: TestClient
) -> None:
    response = client.post(
        f"/api/v1/ops/deletion-requests/{uuid.uuid4()}/execute",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_execute_deletion_endpoint_returns_error_on_execution_failure(
    client: TestClient, db: Session, monkeypatch: MonkeyPatch
) -> None:
    uid = 9913
    req = DeletionRequest(telegram_user_id=uid, status="pending")
    db.add(req)
    db.commit()
    db.refresh(req)

    def mock_execute_fail(*_: object, **__: object) -> None:
        from app.ops.deletion import DeletionExecutionError
        raise DeletionExecutionError("Simulated failure")

    from app.ops import api as ops_api_mod
    monkeypatch.setattr(ops_api_mod, "execute_user_data_deletion", mock_execute_fail)

    response = client.post(
        f"/api/v1/ops/deletion-requests/{req.id}/execute",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] is None
    assert payload["error"] == "deletion_execution_failed"

    # Verify DeletionRequest status remains "pending" (rollback worked)
    db.refresh(req)
    assert req.status == "pending"


def test_open_investigation_endpoint_requires_ops_token(
    client: TestClient, db: Session
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("c89f43e0-2049-42bb-9298-42be08b303f8"),
        telegram_user_id=9904,
        chat_id=8804,
        crisis_state="crisis_active",
    )
    alert = OperatorAlert(
        id=uuid.UUID("713c42c1-4f84-4a17-848e-e3853723d4ec"),
        session_id=session_record.id,
        telegram_user_id=9904,
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

    response = client.post(
        f"/api/v1/ops/alerts/{alert.id}/investigations",
        json={"reason_code": "critical_safety_review"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_ops_auth_token"


def test_open_and_close_investigation_flow_returns_wrapped_payload(
    client: TestClient, db: Session
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("10d9bf60-7fd9-4289-9b18-20679fa10341"),
        telegram_user_id=9905,
        chat_id=8805,
        crisis_state="crisis_active",
        last_user_message="Я боюсь, что могу навредить себе сегодня.",
        last_bot_prompt="Сейчас важно переключиться на более безопасный шаг.",
        crisis_activated_at=datetime.now(timezone.utc),
        crisis_last_routed_at=datetime.now(timezone.utc),
    )
    alert = OperatorAlert(
        id=uuid.UUID("20e8e09f-c237-4cf4-810b-4346daa891f4"),
        session_id=session_record.id,
        telegram_user_id=9905,
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
    safety_signal = SafetySignal(
        session_id=session_record.id,
        telegram_user_id=9905,
        turn_index=1,
        classification="crisis",
        trigger_category="self_harm",
        confidence="high",
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    db.add(alert)
    db.add(safety_signal)
    db.commit()

    open_response = client.post(
        f"/api/v1/ops/alerts/{alert.id}/investigations",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
        json={
            "reason_code": "critical_safety_review",
            "audit_notes": "Need bounded review of the current incident.",
        },
    )

    assert open_response.status_code == 200
    open_payload = open_response.json()
    assert open_payload["error"] is None
    investigation_id = open_payload["data"]["id"]
    assert open_payload["data"]["status"] == "opened"
    assert (
        open_payload["data"]["context_payload"]["current_turn"]["last_user_message"]
        == "Я боюсь, что могу навредить себе сегодня."
    )

    close_response = client.post(
        f"/api/v1/ops/investigations/{investigation_id}/close",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
        json={
            "reviewed_classification": "borderline",
            "outcome": "false_positive",
            "audit_notes": "Full emergency framing not confirmed.",
        },
    )

    assert close_response.status_code == 200
    close_payload = close_response.json()
    assert close_payload["error"] is None
    assert close_payload["data"]["status"] == "closed"
    assert close_payload["data"]["reviewed_classification"] == "borderline"
    assert close_payload["data"]["outcome"] == "false_positive"


def test_get_investigation_context_requires_existing_investigation(
    client: TestClient, db: Session
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("858ac62d-f2f5-4cbe-893a-34d9cefc5b9a"),
        telegram_user_id=9906,
        chat_id=8806,
        crisis_state="crisis_active",
    )
    alert = OperatorAlert(
        id=uuid.UUID("798a5ee7-f7db-4eb7-b5ab-c3b884ba2268"),
        session_id=session_record.id,
        telegram_user_id=9906,
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
        id=uuid.UUID("b6f7be03-6828-48e1-9d99-9e1e54eeb348"),
        operator_alert_id=alert.id,
        session_id=session_record.id,
        telegram_user_id=9906,
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

    response = client.get(
        f"/api/v1/ops/investigations/{investigation.id}",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["error"] is None
    assert payload["data"]["id"] == str(investigation.id)
    assert payload["data"]["context_payload"]["alert"]["classification"] == "crisis"


def test_open_investigation_returns_404_for_missing_alert(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/ops/alerts/{uuid.uuid4()}/investigations",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
        json={"reason_code": "critical_safety_review"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "operator_alert_not_found"


def test_get_investigation_requires_ops_token(client: TestClient) -> None:
    response = client.get(f"/api/v1/ops/investigations/{uuid.uuid4()}")

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_ops_auth_token"


def test_close_investigation_requires_ops_token(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/ops/investigations/{uuid.uuid4()}/close",
        json={
            "reviewed_classification": "borderline",
            "outcome": "false_positive",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_ops_auth_token"


def test_open_investigation_returns_409_when_open_investigation_already_exists(
    client: TestClient, db: Session
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("f1e2d3c4-b5a6-4000-8000-000000000001"),
        telegram_user_id=9907,
        chat_id=8807,
        crisis_state="crisis_active",
    )
    alert = OperatorAlert(
        id=uuid.UUID("f1e2d3c4-b5a6-4000-8000-000000000002"),
        session_id=session_record.id,
        telegram_user_id=9907,
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

    first_response = client.post(
        f"/api/v1/ops/alerts/{alert.id}/investigations",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
        json={"reason_code": "critical_safety_review"},
    )
    assert first_response.status_code == 200

    duplicate_response = client.post(
        f"/api/v1/ops/alerts/{alert.id}/investigations",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
        json={"reason_code": "critical_safety_review"},
    )
    assert duplicate_response.status_code == 409
    assert "investigation_already_open" in duplicate_response.json()["detail"]


def test_close_investigation_returns_409_when_not_in_opened_status(
    client: TestClient, db: Session
) -> None:
    session_record = TelegramSession(
        id=uuid.UUID("f1e2d3c4-b5a6-4000-8000-000000000003"),
        telegram_user_id=9908,
        chat_id=8808,
        crisis_state="crisis_active",
    )
    alert = OperatorAlert(
        id=uuid.UUID("f1e2d3c4-b5a6-4000-8000-000000000004"),
        session_id=session_record.id,
        telegram_user_id=9908,
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

    investigation = OperatorInvestigation(
        id=uuid.UUID("f1e2d3c4-b5a6-4000-8000-000000000005"),
        operator_alert_id=alert.id,
        session_id=session_record.id,
        telegram_user_id=9908,
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

    response = client.post(
        f"/api/v1/ops/investigations/{investigation.id}/close",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
        json={
            "reviewed_classification": "crisis",
            "outcome": "confirmed_crisis",
        },
    )

    assert response.status_code == 409
    assert "investigation_not_closeable" in response.json()["detail"]


def test_billing_issues_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/ops/billing-issues")
    assert response.status_code == 401


def test_billing_issues_returns_list(client: TestClient) -> None:
    response = client.get(
        "/api/v1/ops/billing-issues",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["data"], list)
    assert data["error"] is None


def test_billing_issues_pagination(client: TestClient, db: Session) -> None:
    from app.billing.models import PurchaseIntent

    # Get initial count
    resp = client.get(
        "/api/v1/ops/billing-issues?limit=1000",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )
    base_count = len(resp.json()["data"])

    # Create 3 failed intents
    for i in range(3):
        intent = PurchaseIntent(
            telegram_user_id=72000 + i,
            invoice_payload=f"premium_72000_{i}",
            amount=100,
            status="failed",
        )
        db.add(intent)
    db.commit()

    total_count = base_count + 3

    # Test limit=2
    response = client.get(
        "/api/v1/ops/billing-issues?limit=2",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2

    # Test offset
    offset = total_count - 1
    response = client.get(
        f"/api/v1/ops/billing-issues?offset={offset}",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


def test_billing_per_user_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/ops/billing/12345")
    assert response.status_code == 401


def test_billing_per_user_returns_404_for_unknown(client: TestClient) -> None:
    response = client.get(
        "/api/v1/ops/billing/999999999",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )
    assert response.status_code == 404


def test_billing_per_user_returns_context(client: TestClient, db: Session) -> None:
    from app.billing.models import PurchaseIntent, UserAccessState

    state = UserAccessState(
        telegram_user_id=71001, access_tier="premium", free_sessions_used=0
    )
    intent = PurchaseIntent(
        telegram_user_id=71001,
        invoice_payload="premium_71001",
        amount=100,
        status="completed",
    )
    db.add(state)
    db.add(intent)
    db.commit()

    response = client.get(
        "/api/v1/ops/billing/71001",
        headers={"X-Ops-Auth-Token": "local-ops-auth-token"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["access_tier"] == "premium"
    assert len(data["purchase_intents"]) == 1
    assert "status" in data["purchase_intents"][0]
    assert data["purchase_intents"][0]["status"] == "completed"
