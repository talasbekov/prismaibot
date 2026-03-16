from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models import PeriodicInsight, TelegramSession

logger = logging.getLogger(__name__)


def deliver_insights_for_all_users() -> None:
    """Entry point for the periodic insight delivery job."""
    delivered = 0
    skipped = 0
    failed = 0

    with Session(engine) as session:
        # Load all PeriodicInsight with "pending_delivery" status and non-empty insight_text
        # Added limit for basic batching (L2)
        statement = (
            select(PeriodicInsight)
            .where(
                PeriodicInsight.status == "pending_delivery",
                PeriodicInsight.insight_text != "",
            )
            .limit(100)
        )
        insights = session.exec(statement).all()

        for insight in insights:
            try:
                result = deliver_insight(session, insight)
                if result == "delivered":
                    delivered += 1
                elif result == "skipped":
                    skipped += 1
                else:
                    failed += 1
            except Exception:
                logger.exception(
                    "Unexpected error delivering insight id=%s for telegram_user_id=%s",
                    insight.id,
                    insight.telegram_user_id,
                )
                failed += 1

    logger.info(
        "Periodic insight delivery complete. Delivered: %d, Skipped: %d, Failed: %d",
        delivered,
        skipped,
        failed,
    )


def deliver_insight(session: Session, insight: PeriodicInsight) -> str:
    """Logic to deliver a single insight via Telegram."""
    chat_id = _get_chat_id_for_user(session, insight.telegram_user_id)
    if not chat_id:
        logger.warning(
            "No chat_id found for telegram_user_id=%s, skipping insight id=%s",
            insight.telegram_user_id,
            insight.id,
        )
        return "skipped"

    try:
        _send_telegram_message(chat_id, insight.insight_text)

        insight.status = "delivered"
        insight.updated_at = datetime.now(timezone.utc)
        session.add(insight)
        session.commit()

        # Log AFTER commit to avoid false failure if logger fails (L1)
        logger.info(
            "Successfully delivered insight id=%s to telegram_user_id=%s",
            insight.id,
            insight.telegram_user_id,
        )
        return "delivered"
    except Exception as exc:
        session.rollback()

        # Handle transient vs permanent errors (H1)
        is_permanent = _is_permanent_delivery_failure(exc)

        if is_permanent:
            insight.status = "delivery_failed"
            logger.error(
                "Permanent delivery failure for insight id=%s (user=%s): %s",
                insight.id, insight.telegram_user_id, exc
            )
        else:
            # Remains "pending_delivery" for retry in next run
            logger.warning(
                "Transient delivery failure for insight id=%s (user=%s), will retry: %s",
                insight.id, insight.telegram_user_id, exc
            )

        insight.delivery_error = str(exc)[:500]
        insight.updated_at = datetime.now(timezone.utc)
        session.add(insight)
        session.commit()
        return "failed"


def _is_permanent_delivery_failure(exc: Exception) -> bool:
    """Determine if the error is permanent (like 403 Forbidden)."""
    # 1. Check for Telegram specific status codes if it's a RuntimeError from _send_telegram_message
    exc_str = str(exc)

    # 403 Forbidden: bot was blocked by the user
    # 400 Bad Request: chat not found or invalid user_id
    # 401 Unauthorized: invalid token
    permanent_codes = ("403", "400", "401")

    if "Telegram API error" in exc_str:
        return any(code in exc_str for code in permanent_codes)

    # Network errors (timeouts, connection issues) are transient
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return False

    return False # Default to transient to be safe per AC4


def _get_chat_id_for_user(session: Session, telegram_user_id: int) -> int | None:
    """Lookup the most recent chat_id for a user."""
    statement = (
        select(TelegramSession)
        .where(TelegramSession.telegram_user_id == telegram_user_id)
        .order_by(TelegramSession.updated_at.desc())
        .limit(1)
    )
    ts = session.exec(statement).first()
    return ts.chat_id if ts else None


def _send_telegram_message(chat_id: int, text: str) -> None:
    """Send a message to Telegram via Bot API."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not configured")

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    # Removed parse_mode: Markdown to avoid errors with unescaped AI text (M1)
    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    response = httpx.post(url, json=payload, timeout=10.0)
    if not response.is_success:
        raise RuntimeError(
            f"Telegram API error: {response.status_code} {response.text[:200]}"
        )
