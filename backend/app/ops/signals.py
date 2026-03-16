from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.models import SummaryGenerationSignal


def record_retryable_signal(
    session: Session,
    *,
    session_id: uuid.UUID,
    telegram_user_id: int,
    signal_type: str,
    error_type: str,
    error_message: str,
    suggested_action: str,
    retry_payload: dict[str, Any] | None = None,
    failure_stage: str = "persistence",
) -> None:
    now = datetime.now(timezone.utc)
    signal = session.exec(
        select(SummaryGenerationSignal).where(
            SummaryGenerationSignal.session_id == session_id
        )
    ).first()
    attempt_count = 1 if signal is None else signal.attempt_count + 1
    retryable = attempt_count < settings.MEMORY_MAX_RETRY_ATTEMPTS
    if signal is None:
        signal = SummaryGenerationSignal(
            session_id=session_id,
            telegram_user_id=telegram_user_id,
            details={},
            created_at=now,
            updated_at=now,
        )
    signal.telegram_user_id = telegram_user_id
    signal.signal_type = signal_type
    signal.retryable = retryable
    signal.attempt_count = attempt_count
    signal.retry_payload = retry_payload or {}
    signal.retry_available_at = now
    signal.details = {
        "error_type": error_type,
        "error_message": error_message[:500],
        "failure_stage": failure_stage,
        "suggested_action": suggested_action,
    }
    signal.updated_at = now
    session.add(signal)


def resolve_summary_signal(
    session: Session,
    *,
    session_id: uuid.UUID,
    resolution_status: str = "resolved",
) -> None:
    """Mark an open summary failure signal as resolved or retried."""
    signal = session.exec(
        select(SummaryGenerationSignal)
        .where(SummaryGenerationSignal.session_id == session_id)
        .where(SummaryGenerationSignal.status == "open")
    ).first()
    if signal is None:
        return
    now = datetime.now(timezone.utc)
    signal.status = resolution_status
    signal.updated_at = now
    session.add(signal)


def record_summary_failure_signal(
    session: Session,
    *,
    session_id: uuid.UUID,
    telegram_user_id: int,
    error_type: str,
    error_message: str,
    retry_payload: dict[str, Any] | None = None,
    failure_stage: str = "persistence",
) -> None:
    record_retryable_signal(
        session,
        session_id=session_id,
        telegram_user_id=telegram_user_id,
        signal_type="session_summary_failed",
        error_type=error_type,
        error_message=error_message,
        suggested_action="retry_session_memory_persistence",
        retry_payload=retry_payload,
        failure_stage=failure_stage,
    )
