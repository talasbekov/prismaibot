from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import (
    DeletionRequest,
    PeriodicInsight,
    ProfileFact,
    SessionSummary,
    TelegramSession,
)
from app.ops.deletion import (
    execute_user_data_deletion,
    list_pending_deletion_requests,
    request_user_data_deletion,
)


def test_execute_user_data_deletion_removes_summaries_facts_insights(db: Session) -> None:
    uid = 8001

    # Setup: create TelegramSession
    ts = TelegramSession(telegram_user_id=uid, chat_id=uid)
    db.add(ts)
    db.commit()
    db.refresh(ts)

    # Setup: create DeletionRequest
    req, _ = request_user_data_deletion(db, telegram_user_id=uid)

    # Setup: create artifacts
    summary = SessionSummary(session_id=ts.id, telegram_user_id=uid, takeaway="test", deletion_eligible=True)
    fact = ProfileFact(telegram_user_id=uid, source_session_id=ts.id, fact_key="name", fact_value="John", deletion_eligible=True)
    insight = PeriodicInsight(telegram_user_id=uid, insight_text="test insight")

    db.add(summary)
    db.add(fact)
    db.add(insight)
    db.commit()

    # Execute deletion
    result = execute_user_data_deletion(db, request_id=req.id)

    # Verify result counts
    assert result.summaries_deleted == 1
    assert result.profile_facts_deleted == 1
    assert result.insights_deleted == 1
    assert result.status == "completed"

    # Verify DB: artifacts are gone
    assert len(db.exec(select(SessionSummary).where(SessionSummary.telegram_user_id == uid)).all()) == 0
    assert len(db.exec(select(ProfileFact).where(ProfileFact.telegram_user_id == uid)).all()) == 0
    assert len(db.exec(select(PeriodicInsight).where(PeriodicInsight.telegram_user_id == uid)).all()) == 0

    # Verify DeletionRequest updated
    db.refresh(req)
    assert req.status == "completed"
    assert req.completed_at is not None
    assert "summaries:1" in req.audit_notes
    assert "facts:1" in req.audit_notes
    assert "insights:1" in req.audit_notes


def test_execute_user_data_deletion_purges_sessions(db: Session) -> None:
    uid = 8002

    # Setup: create TelegramSession with content
    ts = TelegramSession(
        telegram_user_id=uid,
        chat_id=uid,
        working_context="some context",
        last_user_message="hello",
        last_bot_prompt="hi"
    )
    db.add(ts)
    db.commit()
    db.refresh(ts)

    # Setup: create DeletionRequest
    req, _ = request_user_data_deletion(db, telegram_user_id=uid)

    # Execute deletion
    result = execute_user_data_deletion(db, request_id=req.id)

    assert result.sessions_purged == 1

    # Verify DB: content is purged
    db.refresh(ts)
    assert ts.working_context is None
    assert ts.last_user_message is None
    assert ts.last_bot_prompt is None
    assert ts.transcript_purged_at is not None


def test_execute_user_data_deletion_is_idempotent(db: Session) -> None:
    uid = 8003

    # Setup: create DeletionRequest
    req, _ = request_user_data_deletion(db, telegram_user_id=uid)

    # Execute first time
    result1 = execute_user_data_deletion(db, request_id=req.id)
    assert result1.status == "completed"

    # Execute second time
    result2 = execute_user_data_deletion(db, request_id=req.id)
    assert result2.status == "already_completed"
    assert result2.summaries_deleted == 0


def test_execute_user_data_deletion_handles_missing_artifacts(db: Session) -> None:
    uid = 8004

    # Setup: create DeletionRequest but NO artifacts
    req, _ = request_user_data_deletion(db, telegram_user_id=uid)

    # Execute deletion
    result = execute_user_data_deletion(db, request_id=req.id)

    assert result.summaries_deleted == 0
    assert result.profile_facts_deleted == 0
    assert result.insights_deleted == 0
    assert result.sessions_purged == 0
    assert result.status == "completed"


def test_request_user_data_deletion_creates_new_pending_request(db: Session) -> None:
    telegram_user_id = 9001

    request, created = request_user_data_deletion(db, telegram_user_id=telegram_user_id)

    assert created is True
    assert request.telegram_user_id == telegram_user_id
    assert request.status == "pending"
    assert request.requested_at is not None
    assert request.completed_at is None

def test_request_user_data_deletion_is_idempotent_for_pending_status(db: Session) -> None:
    telegram_user_id = 9002

    # First request
    req1, created1 = request_user_data_deletion(db, telegram_user_id=telegram_user_id)
    assert created1 is True

    # Second request
    req2, created2 = request_user_data_deletion(db, telegram_user_id=telegram_user_id)
    assert created2 is False
    assert req1.id == req2.id

def test_request_user_data_deletion_allows_new_request_after_completion(db: Session) -> None:
    telegram_user_id = 9003

    # Existing completed request
    old_req = DeletionRequest(
        telegram_user_id=telegram_user_id,
        status="completed",
        requested_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(old_req)
    db.commit()

    # New request
    new_req, created = request_user_data_deletion(db, telegram_user_id=telegram_user_id)

    assert created is True
    assert new_req.id != old_req.id
    assert new_req.status == "pending"

def test_list_pending_deletion_requests_filters_correctly(db: Session) -> None:
    # 1 pending
    req_p = DeletionRequest(telegram_user_id=9004, status="pending")
    # 1 completed
    req_c = DeletionRequest(telegram_user_id=9005, status="completed")

    db.add(req_p)
    db.add(req_c)
    db.commit()

    pending_list = list_pending_deletion_requests(db)

    # Verify our record is present and completed one is not
    assert any(r.telegram_user_id == 9004 for r in pending_list)
    assert not any(r.telegram_user_id == 9005 for r in pending_list)
