import uuid

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.memory import get_continuity_overview
from app.models import DeletionRequest, OperatorAlert, OperatorInvestigation
from app.ops.alerts import list_operator_alerts
from app.ops.billing_review import (
    BillingIssue,
    UserBillingContext,
    get_user_billing_context,
    list_billing_issues,
)
from app.ops.deletion import (
    DeletionExecutionError,
    execute_user_data_deletion,
    list_pending_deletion_requests,
)
from app.ops.health import check_service_health
from app.ops.investigations import (
    InvestigationConflictError,
    InvestigationStateError,
    close_operator_investigation,
    get_operator_investigation,
    request_and_open_operator_investigation,
)
from app.ops.status import get_operational_status

router = APIRouter(prefix="/ops", tags=["ops"])


class OpenInvestigationRequest(BaseModel):
    reason_code: str
    audit_notes: str | None = None


class CloseInvestigationRequest(BaseModel):
    reviewed_classification: str = Field(max_length=16)
    outcome: str
    audit_notes: str | None = None


def _verify_ops_token(ops_auth_token: str | None) -> None:
    expected_token = settings.OPS_AUTH_TOKEN
    if not expected_token:
        return
    if ops_auth_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_ops_auth_token",
        )


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> JSONResponse:
    result = check_service_health(engine)
    http_status = (
        status.HTTP_200_OK
        if result.status == "ready"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(
        status_code=http_status,
        content={
            "status": result.status,
            "service": result.service,
            "database_configured": result.database_configured,
            "database_reachable": result.database_reachable,
        },
    )


@router.get("/auth-check")
def auth_check(
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    return {
        "status": "ok",
        "scope": "ops",
    }


@router.get("/status")
def operational_status(
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        result = get_operational_status(session)
    return {
        "data": {
            "session_activity": {
                "total_active": result.session_activity.total_active,
                "total_crisis_active": result.session_activity.total_crisis_active,
            },
            "open_summary_failure_signals": result.open_summary_failure_signals,
            "undelivered_operator_alerts": result.undelivered_operator_alerts,
            "pending_deletion_requests": result.pending_deletion_requests,
            "payment_signals": {
                "pending": result.payment_signals.pending,
                "confirmed": result.payment_signals.confirmed,
                "failed": result.payment_signals.failed,
            },
            "degraded_fields": result.degraded_fields,
        },
        "error": None,
    }


@router.get("/billing-issues")
def billing_issues(
    limit: int = 100,
    offset: int = 0,
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        issues = list_billing_issues(session, limit=limit, offset=offset)
    return {
        "data": [_serialize_billing_issue(issue) for issue in issues],
        "error": None,
    }


@router.get("/billing/{telegram_user_id}")
def user_billing_context(
    telegram_user_id: int,
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        ctx = get_user_billing_context(session, telegram_user_id)
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="billing_context_not_found",
        )
    return {
        "data": _serialize_user_billing_context(ctx),
        "error": None,
    }


@router.get("/continuity/{telegram_user_id}")
def continuity_overview(
    telegram_user_id: int,
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        overview = get_continuity_overview(session, telegram_user_id=telegram_user_id)

    if not overview.summaries and not overview.profile_facts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="continuity_not_found",
        )

    return {
        "data": overview.model_dump(mode="json"),
        "error": None,
    }


@router.get("/alerts")
def alerts_inbox(
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        alerts = list_operator_alerts(session)

    return {
        "data": [
            _serialize_alert(alert)
            for alert in alerts
        ],
        "error": None,
    }


@router.get("/deletion-requests")
def pending_deletion_requests(
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        requests = list_pending_deletion_requests(session)

    return {
        "data": [
            _serialize_deletion_request(req)
            for req in requests
        ],
        "error": None,
    }


@router.post("/deletion-requests/{request_id}/execute")
def execute_deletion(
    request_id: uuid.UUID,
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        try:
            result = execute_user_data_deletion(session, request_id=request_id)
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except DeletionExecutionError:
            return {"data": None, "error": "deletion_execution_failed"}

    return {
        "data": {
            "request_id": str(result.request_id),
            "telegram_user_id": result.telegram_user_id,
            "summaries_deleted": result.summaries_deleted,
            "profile_facts_deleted": result.profile_facts_deleted,
            "insights_deleted": result.insights_deleted,
            "sessions_purged": result.sessions_purged,
            "status": result.status,
            "audit_notes": result.audit_notes,
        },
        "error": None,
    }


@router.post("/alerts/{operator_alert_id}/investigations")
def open_investigation(
    operator_alert_id: uuid.UUID,
    payload: OpenInvestigationRequest,
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        try:
            investigation = request_and_open_operator_investigation(
                session,
                operator_alert_id=operator_alert_id,
                reason_code=payload.reason_code,
                requested_by="ops:token",
                approved_by="ops:token",
                audit_notes=payload.audit_notes,
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except InvestigationConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

    return {
        "data": _serialize_investigation(investigation),
        "error": None,
    }


@router.get("/investigations/{investigation_id}")
def get_investigation(
    investigation_id: uuid.UUID,
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        try:
            investigation = get_operator_investigation(
                session, investigation_id=investigation_id
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    return {
        "data": _serialize_investigation(investigation),
        "error": None,
    }


@router.post("/investigations/{investigation_id}/close")
def close_investigation(
    investigation_id: uuid.UUID,
    payload: CloseInvestigationRequest,
    ops_auth_token: str | None = Header(default=None, alias="X-Ops-Auth-Token"),
) -> dict[str, object]:
    _verify_ops_token(ops_auth_token)
    with Session(engine) as session:
        try:
            investigation = close_operator_investigation(
                session,
                investigation_id=investigation_id,
                reviewed_by="ops:token",
                reviewed_classification=payload.reviewed_classification,
                outcome=payload.outcome,
                audit_notes=payload.audit_notes,
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except InvestigationStateError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

    return {
        "data": _serialize_investigation(investigation),
        "error": None,
    }


def _serialize_alert(alert: OperatorAlert) -> dict[str, object]:
    return {
        "id": str(alert.id),
        "session_id": str(alert.session_id),
        "telegram_user_id": alert.telegram_user_id,
        "classification": alert.classification,
        "trigger_category": alert.trigger_category,
        "confidence": alert.confidence,
        "delivery_channel": alert.delivery_channel,
        "status": alert.status,
        "payload": alert.payload,
        "delivery_attempt_count": alert.delivery_attempt_count,
        "last_delivery_error": alert.last_delivery_error,
        "first_routed_at": (
            alert.first_routed_at.isoformat()
            if alert.first_routed_at is not None
            else None
        ),
        "last_delivery_attempt_at": (
            alert.last_delivery_attempt_at.isoformat()
            if alert.last_delivery_attempt_at is not None
            else None
        ),
        "delivered_at": (
            alert.delivered_at.isoformat()
            if alert.delivered_at is not None
            else None
        ),
        "created_at": (
            alert.created_at.isoformat()
            if alert.created_at is not None
            else None
        ),
        "updated_at": (
            alert.updated_at.isoformat()
            if alert.updated_at is not None
            else None
        ),
    }


def _serialize_deletion_request(request: DeletionRequest) -> dict[str, object]:
    return {
        "id": str(request.id),
        "telegram_user_id": request.telegram_user_id,
        "status": request.status,
        "requested_at": (
            request.requested_at.isoformat()
            if request.requested_at is not None
            else None
        ),
        "completed_at": (
            request.completed_at.isoformat()
            if request.completed_at is not None
            else None
        ),
        "audit_notes": request.audit_notes,
    }


def _serialize_investigation(
    investigation: OperatorInvestigation,
) -> dict[str, object]:
    return {
        "id": str(investigation.id),
        "operator_alert_id": str(investigation.operator_alert_id),
        "session_id": str(investigation.session_id),
        "telegram_user_id": investigation.telegram_user_id,
        "reason_code": investigation.reason_code,
        "status": investigation.status,
        "requested_by": investigation.requested_by,
        "approved_by": investigation.approved_by,
        "reviewed_by": investigation.reviewed_by,
        "source_classification": investigation.source_classification,
        "source_trigger_category": investigation.source_trigger_category,
        "source_confidence": investigation.source_confidence,
        "reviewed_classification": investigation.reviewed_classification,
        "outcome": investigation.outcome,
        "audit_notes": investigation.audit_notes,
        "context_payload": investigation.context_payload,
        "requested_at": (
            investigation.requested_at.isoformat()
            if investigation.requested_at is not None
            else None
        ),
        "approved_at": (
            investigation.approved_at.isoformat()
            if investigation.approved_at is not None
            else None
        ),
        "opened_at": (
            investigation.opened_at.isoformat()
            if investigation.opened_at is not None
            else None
        ),
        "closed_at": (
            investigation.closed_at.isoformat()
            if investigation.closed_at is not None
            else None
        ),
        "created_at": (
            investigation.created_at.isoformat()
            if investigation.created_at is not None
            else None
        ),
        "updated_at": (
            investigation.updated_at.isoformat()
            if investigation.updated_at is not None
            else None
        ),
    }


def _serialize_billing_issue(issue: BillingIssue) -> dict[str, object]:
    return {
        "telegram_user_id": issue.telegram_user_id,
        "issue_category": issue.issue_category,
        "intent_id": str(issue.intent_id) if issue.intent_id is not None else None,
        "intent_status": issue.intent_status,
        "intent_created_at": (
            issue.intent_created_at.isoformat()
            if issue.intent_created_at is not None
            else None
        ),
        "intent_updated_at": (
            issue.intent_updated_at.isoformat()
            if issue.intent_updated_at is not None
            else None
        ),
        "provider_payment_charge_id": issue.provider_payment_charge_id,
        "access_tier": issue.access_tier,
        "access_updated_at": (
            issue.access_updated_at.isoformat()
            if issue.access_updated_at is not None
            else None
        ),
    }


def _serialize_user_billing_context(ctx: UserBillingContext) -> dict[str, object]:
    return {
        "telegram_user_id": ctx.telegram_user_id,
        "access_tier": ctx.access_tier,
        "free_sessions_used": ctx.free_sessions_used,
        "threshold_reached_at": (
            ctx.threshold_reached_at.isoformat()
            if ctx.threshold_reached_at is not None
            else None
        ),
        "purchase_intents": ctx.purchase_intents,
    }
