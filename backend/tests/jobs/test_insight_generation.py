
import pytest
from sqlmodel import Session, delete, select

from app.jobs.weekly_insights import generate_insight_for_user
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
def clear_insight_tables(db: Session):
    # Cleanup before test using project patterns and correct dependency order
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

def test_generate_insight_for_user_success(db: Session, clear_insight_tables):
    user_id = 12345

    # Setup user with 2 durable summaries (unique sessions required)
    ts1 = TelegramSession(telegram_user_id=user_id, chat_id=67890)
    ts2 = TelegramSession(telegram_user_id=user_id, chat_id=67890)
    db.add(ts1)
    db.add(ts2)
    db.flush()

    s1 = SessionSummary(
        telegram_user_id=user_id,
        session_id=ts1.id,
        takeaway="Мы обсуждали рабочие конфликты и способы их решения.",
        reflective_mode="deep",
        source_turn_count=2,
        retention_scope="durable_summary",
        key_facts=[],
        emotional_tensions=[],
        uncertainty_notes=[],
        next_step_context=[]
    )
    s2 = SessionSummary(
        telegram_user_id=user_id,
        session_id=ts2.id,
        takeaway="Затронули тему личных границ в отношениях с партнером и рабочих вопросов.",
        reflective_mode="deep",
        source_turn_count=3,
        retention_scope="durable_summary",
        key_facts=[],
        emotional_tensions=[],
        uncertainty_notes=[],
        next_step_context=[]
    )
    db.add(s1)
    db.add(s2)
    db.commit()

    result = generate_insight_for_user(user_id)

    assert result == "generated"
    insight = db.exec(select(PeriodicInsight).where(PeriodicInsight.telegram_user_id == user_id)).one()
    assert insight.status == "pending_delivery"
    assert insight.basis_summary_count == 2
    assert "рабочих" in insight.insight_text
    assert "отношений" in insight.insight_text
    assert len(insight.insight_text) <= 1500

def test_generate_insight_insufficient_context_zero(db: Session, clear_insight_tables):
    user_id = 11111
    # No summaries in DB
    result = generate_insight_for_user(user_id)
    assert result == "skipped"
    insights = db.exec(select(PeriodicInsight).where(PeriodicInsight.telegram_user_id == user_id)).all()
    assert len(insights) == 0

def test_generate_insight_insufficient_context_one(db: Session, clear_insight_tables):
    user_id = 22222
    ts = TelegramSession(telegram_user_id=user_id, chat_id=111)
    db.add(ts)
    db.flush()
    s = SessionSummary(
        telegram_user_id=user_id,
        session_id=ts.id,
        takeaway="Just one summary",
        retention_scope="durable_summary",
        key_facts=[],
        emotional_tensions=[],
        uncertainty_notes=[],
        next_step_context=[]
    )
    db.add(s)
    db.commit()

    result = generate_insight_for_user(user_id)
    assert result == "skipped"
    insights = db.exec(select(PeriodicInsight).where(PeriodicInsight.telegram_user_id == user_id)).all()
    assert len(insights) == 0

def test_insight_text_no_raw_transcript(db: Session, clear_insight_tables):
    user_id = 33333
    ts1 = TelegramSession(telegram_user_id=user_id, chat_id=222, last_user_message="SECRET_MESSAGE_123")
    ts2 = TelegramSession(telegram_user_id=user_id, chat_id=222)
    db.add(ts1)
    db.add(ts2)
    db.flush()

    s1 = SessionSummary(telegram_user_id=user_id, session_id=ts1.id, takeaway="Theme A", retention_scope="durable_summary", key_facts=[], emotional_tensions=[], uncertainty_notes=[], next_step_context=[])
    s2 = SessionSummary(telegram_user_id=user_id, session_id=ts2.id, takeaway="Theme B", retention_scope="durable_summary", key_facts=[], emotional_tensions=[], uncertainty_notes=[], next_step_context=[])
    db.add(s1)
    db.add(s2)
    db.commit()

    generate_insight_for_user(user_id)
    insight = db.exec(select(PeriodicInsight).where(PeriodicInsight.telegram_user_id == user_id)).one()
    assert "SECRET_MESSAGE_123" not in insight.insight_text

def test_insight_text_length_limit(db: Session, clear_insight_tables):
    user_id = 44444
    ts1 = TelegramSession(telegram_user_id=user_id, chat_id=1)
    ts2 = TelegramSession(telegram_user_id=user_id, chat_id=2)
    db.add(ts1)
    db.add(ts2)
    db.flush()

    long_takeaway = "Very long takeaway. " * 100
    s1 = SessionSummary(telegram_user_id=user_id, session_id=ts1.id, takeaway=long_takeaway[:1000], retention_scope="durable_summary", key_facts=[], emotional_tensions=[], uncertainty_notes=[], next_step_context=[])
    s2 = SessionSummary(telegram_user_id=user_id, session_id=ts2.id, takeaway="Short one", retention_scope="durable_summary", key_facts=[], emotional_tensions=[], uncertainty_notes=[], next_step_context=[])
    db.add(s1)
    db.add(s2)
    db.commit()

    generate_insight_for_user(user_id)
    insight = db.exec(select(PeriodicInsight).where(PeriodicInsight.telegram_user_id == user_id)).one()
    assert len(insight.insight_text) <= 1500

def test_generate_insight_error_path_records_failed_status(db: Session, clear_insight_tables, monkeypatch):
    user_id = 55555
    ts1 = TelegramSession(telegram_user_id=user_id, chat_id=1)
    ts2 = TelegramSession(telegram_user_id=user_id, chat_id=2)
    db.add(ts1)
    db.add(ts2)
    db.flush()
    s1 = SessionSummary(telegram_user_id=user_id, session_id=ts1.id, takeaway="A", retention_scope="durable_summary", key_facts=[], emotional_tensions=[], uncertainty_notes=[], next_step_context=[])
    s2 = SessionSummary(telegram_user_id=user_id, session_id=ts2.id, takeaway="B", retention_scope="durable_summary", key_facts=[], emotional_tensions=[], uncertainty_notes=[], next_step_context=[])
    db.add(s1)
    db.add(s2)
    db.commit()

    from app.jobs import weekly_insights
    def mock_build_error(overview):
        raise RuntimeError("Generation crashed")

    monkeypatch.setattr(weekly_insights, "_build_insight_text", mock_build_error)

    with pytest.raises(RuntimeError):
        generate_insight_for_user(user_id)

    insight = db.exec(select(PeriodicInsight).where(PeriodicInsight.telegram_user_id == user_id)).one()
    assert insight.status == "failed"
    assert "Generation crashed" in insight.generation_error
