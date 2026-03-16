from unittest.mock import patch

import httpx
import pytest
from sqlmodel import Session, delete, select

from app.jobs.insight_delivery import deliver_insight, deliver_insights_for_all_users
from app.models import (
    OperatorAlert,
    OperatorInvestigation,
    PeriodicInsight,
    ProfileFact,
    SafetySignal,
    SessionSummary,
    SummaryGenerationSignal,
    TelegramSession,
)


@pytest.fixture
def clear_delivery_tables(db: Session):
    # Cleanup before test using correct dependency order to avoid ForeignKeyViolation
    db.rollback()
    db.exec(delete(PeriodicInsight))
    db.exec(delete(SummaryGenerationSignal))
    db.exec(delete(OperatorInvestigation))
    db.exec(delete(OperatorAlert))
    db.exec(delete(SafetySignal))
    db.exec(delete(ProfileFact))
    db.exec(delete(SessionSummary))
    db.exec(delete(TelegramSession))
    db.commit()

    yield

    # Cleanup after test
    db.rollback()
    db.exec(delete(PeriodicInsight))
    db.exec(delete(SummaryGenerationSignal))
    db.exec(delete(OperatorInvestigation))
    db.exec(delete(OperatorAlert))
    db.exec(delete(SafetySignal))
    db.exec(delete(ProfileFact))
    db.exec(delete(SessionSummary))
    db.exec(delete(TelegramSession))
    db.commit()

def test_deliver_insight_success(db: Session, clear_delivery_tables):
    user_id = 12345
    chat_id = 67890

    # 1. Setup session and pending insight
    ts = TelegramSession(telegram_user_id=user_id, chat_id=chat_id)
    db.add(ts)
    db.flush()

    insight = PeriodicInsight(
        telegram_user_id=user_id,
        insight_text="Your reflective insight is here.",
        status="pending_delivery"
    )
    db.add(insight)
    db.commit()

    # 2. Deliver insight with mock telegram message
    with patch("app.jobs.insight_delivery._send_telegram_message") as mock_send:
        result = deliver_insight(db, insight)

        # 3. Verify
        assert result == "delivered"
        mock_send.assert_called_once_with(chat_id, "Your reflective insight is here.")

        db.expire_all()
        updated_insight = db.exec(select(PeriodicInsight).where(PeriodicInsight.id == insight.id)).one()
        assert updated_insight.status == "delivered"

def test_deliver_insight_no_chat_id(db: Session, clear_delivery_tables):
    user_id = 11111

    # Pending insight but NO session
    insight = PeriodicInsight(
        telegram_user_id=user_id,
        insight_text="Missing chat id insight.",
        status="pending_delivery"
    )
    db.add(insight)
    db.commit()

    with patch("app.jobs.insight_delivery._send_telegram_message") as mock_send:
        result = deliver_insight(db, insight)

        assert result == "skipped"
        mock_send.assert_not_called()

        db.expire_all()
        updated_insight = db.exec(select(PeriodicInsight).where(PeriodicInsight.id == insight.id)).one()
        assert updated_insight.status == "pending_delivery" # Remains pending

def test_deliver_insight_permanent_error_403(db: Session, clear_delivery_tables):
    user_id = 22222
    chat_id = 33333

    ts = TelegramSession(telegram_user_id=user_id, chat_id=chat_id)
    db.add(ts)
    db.flush()

    insight = PeriodicInsight(
        telegram_user_id=user_id,
        insight_text="Failing telegram insight.",
        status="pending_delivery"
    )
    db.add(insight)
    db.commit()

    # 403 Forbidden is a permanent error
    with patch("app.jobs.insight_delivery._send_telegram_message", side_effect=RuntimeError("Telegram API error: 403 Forbidden")):
        result = deliver_insight(db, insight)

        assert result == "failed"

        db.expire_all()
        updated_insight = db.exec(select(PeriodicInsight).where(PeriodicInsight.id == insight.id)).one()
        assert updated_insight.status == "delivery_failed" # Should be failed
        assert "403 Forbidden" in updated_insight.delivery_error

def test_deliver_insight_transient_error_504(db: Session, clear_delivery_tables):
    user_id = 33333
    chat_id = 44444

    ts = TelegramSession(telegram_user_id=user_id, chat_id=chat_id)
    db.add(ts)
    db.flush()

    insight = PeriodicInsight(
        telegram_user_id=user_id,
        insight_text="Transient failing insight.",
        status="pending_delivery"
    )
    db.add(insight)
    db.commit()

    # 504 Gateway Timeout is a transient error
    with patch("app.jobs.insight_delivery._send_telegram_message", side_effect=RuntimeError("Telegram API error: 504 Gateway Timeout")):
        result = deliver_insight(db, insight)

        assert result == "failed"

        db.expire_all()
        updated_insight = db.exec(select(PeriodicInsight).where(PeriodicInsight.id == insight.id)).one()
        assert updated_insight.status == "pending_delivery" # MUST remain pending for retry
        assert "504" in updated_insight.delivery_error

def test_deliver_insight_httpx_timeout_is_transient(db: Session, clear_delivery_tables):
    user_id = 55555
    chat_id = 66666

    ts = TelegramSession(telegram_user_id=user_id, chat_id=chat_id)
    db.add(ts)
    db.flush()

    insight = PeriodicInsight(
        telegram_user_id=user_id,
        insight_text="Timeout insight.",
        status="pending_delivery"
    )
    db.add(insight)
    db.commit()

    # httpx.TimeoutException is transient
    with patch("app.jobs.insight_delivery.httpx.post", side_effect=httpx.TimeoutException("Read timeout")):
        result = deliver_insight(db, insight)

        assert result == "failed"

        db.expire_all()
        updated_insight = db.exec(select(PeriodicInsight).where(PeriodicInsight.id == insight.id)).one()
        assert updated_insight.status == "pending_delivery" # Remains pending

def test_deliver_insights_for_all_users_skips_processed(db: Session, clear_delivery_tables):
    user_id = 44444
    chat_id = 55555

    ts = TelegramSession(telegram_user_id=user_id, chat_id=chat_id)
    db.add(ts)
    db.flush()

    # Insight already delivered
    i1 = PeriodicInsight(
        telegram_user_id=user_id,
        insight_text="Already delivered.",
        status="delivered"
    )
    # Insight with empty text
    i2 = PeriodicInsight(
        telegram_user_id=user_id,
        insight_text="",
        status="pending_delivery"
    )
    db.add(i1)
    db.add(i2)
    db.commit()

    with patch("app.jobs.insight_delivery.deliver_insight") as mock_deliver:
        deliver_insights_for_all_users()
        mock_deliver.assert_not_called()
