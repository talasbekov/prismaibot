from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlmodel import Session, select

from app.models import (
    DeletionRequest,
    PeriodicInsight,
    ProfileFact,
    SessionSummary,
    TelegramSession,
)

logger = logging.getLogger(__name__)


class DeletionRequestIntakeError(RuntimeError):
    """Raised when deletion request cannot be recorded."""


class DeletionExecutionError(RuntimeError):
    """Raised when deletion execution fails."""


@dataclass
class DeletionExecutionResult:
    request_id: uuid.UUID
    telegram_user_id: int
    summaries_deleted: int
    profile_facts_deleted: int
    insights_deleted: int
    sessions_purged: int
    status: str
    audit_notes: str


def request_user_data_deletion(
    session: Session,
    *,
    telegram_user_id: int,
) -> tuple[DeletionRequest, bool]:
    """
    Idempotently register a user's request to delete their data.
    If a 'pending' request already exists for this user, returns (request, False).
    Otherwise, creates a new one and returns (request, True).
    """
    try:
        existing = session.exec(
            select(DeletionRequest).where(
                DeletionRequest.telegram_user_id == telegram_user_id,
                DeletionRequest.status == "pending",
            )
        ).first()

        if existing is not None:
            return existing, False

        now = datetime.now(timezone.utc)
        request = DeletionRequest(
            telegram_user_id=telegram_user_id,
            status="pending",
            requested_at=now,
        )
        session.add(request)
        session.commit()
        session.refresh(request)
        return request, True
    except Exception as exc:
        session.rollback()
        raise DeletionRequestIntakeError(f"Failed to record deletion request: {exc}") from exc


def list_pending_deletion_requests(session: Session) -> list[DeletionRequest]:
    """List all deletion requests with 'pending' status."""
    return list(
        session.exec(
            select(DeletionRequest).where(DeletionRequest.status == "pending")
        ).all()
    )


def execute_user_data_deletion(
    session: Session, *, request_id: uuid.UUID
) -> DeletionExecutionResult:
    """
    Execute a registered deletion request by removing user artifacts and purging sessions.
    """
    request = session.get(DeletionRequest, request_id)
    if not request:
        raise LookupError(f"DeletionRequest with id {request_id} not found")

    uid = request.telegram_user_id

    # Idempotency check
    if request.status == "completed":
        return DeletionExecutionResult(
            request_id=request.id,
            telegram_user_id=uid,
            summaries_deleted=0,
            profile_facts_deleted=0,
            insights_deleted=0,
            sessions_purged=0,
            status="already_completed",
            audit_notes=request.audit_notes or "",
        )

    try:
        # 1. Delete SessionSummary entries
        res_summaries = session.execute(
            sa_delete(SessionSummary).where(
                SessionSummary.telegram_user_id == uid,
                SessionSummary.deletion_eligible == True,
            )
        )
        summaries_deleted = res_summaries.rowcount

        # 2. Delete ProfileFact entries
        res_facts = session.execute(
            sa_delete(ProfileFact).where(
                ProfileFact.telegram_user_id == uid,
                ProfileFact.deletion_eligible == True,
            )
        )
        profile_facts_deleted = res_facts.rowcount

        # 3. Delete PeriodicInsight entries
        res_insights = session.execute(
            sa_delete(PeriodicInsight).where(PeriodicInsight.telegram_user_id == uid)
        )
        insights_deleted = res_insights.rowcount

        # 4. Purge TelegramSession content (transcript items)
        now = datetime.now(timezone.utc)
        res_sessions = session.execute(
            sa_update(TelegramSession)
            .where(TelegramSession.telegram_user_id == uid)
            .values(
                working_context=None,
                last_user_message=None,
                last_bot_prompt=None,
                transcript_purged_at=now,
            )
        )
        sessions_purged = res_sessions.rowcount

        # 5. Update DeletionRequest
        audit_notes = (
            f"summaries:{summaries_deleted}, facts:{profile_facts_deleted}, "
            f"insights:{insights_deleted}, sessions_purged:{sessions_purged}"
        )
        request.status = "completed"
        request.completed_at = now
        request.audit_notes = audit_notes
        session.add(request)

        session.commit()

        return DeletionExecutionResult(
            request_id=request.id,
            telegram_user_id=uid,
            summaries_deleted=summaries_deleted,
            profile_facts_deleted=profile_facts_deleted,
            insights_deleted=insights_deleted,
            sessions_purged=sessions_purged,
            status="completed",
            audit_notes=audit_notes,
        )
    except Exception as exc:
        session.rollback()
        logger.exception("Deletion execution failed for request %s: %s", request_id, exc)
        raise DeletionExecutionError(f"Deletion execution failed: {exc}") from exc
