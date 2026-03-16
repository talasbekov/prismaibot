from sqlmodel import Session, select
from app.safety.service import evaluate_incoming_message_safety
from app.core.config import settings
from app.models import TelegramSession, SafetySignal
import pytest

def test_evaluate_incoming_message_safety_respects_flag(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    session_record = TelegramSession(
        telegram_user_id=123,
        chat_id=123,
        crisis_state="normal",
    )
    db.add(session_record)
    db.flush()
    
    session_id = session_record.id

    # Case 1: Flag Enabled (Explicitly set via monkeypatch)
    monkeypatch.setattr(settings, "SAFETY_ENABLED", True)
    assessment = evaluate_incoming_message_safety(
        db,
        session_record=session_record,
        message_text="не хочу жить",
        turn_index=1,
    )
    assert assessment.classification == "crisis"
    assert session_record.safety_classification == "crisis"
    
    signal = db.exec(
        select(SafetySignal)
        .where(SafetySignal.session_id == session_id)
        .where(SafetySignal.turn_index == 1)
    ).first()
    assert signal is not None

    # Case 2: Flag Disabled (Explicitly set via monkeypatch)
    monkeypatch.setattr(settings, "SAFETY_ENABLED", False)
    
    # We DON'T manually reset safety_classification here to avoid tautology.
    # It was set to 'crisis' in Case 1. The function should update it back to 'safe'.
    
    assessment = evaluate_incoming_message_safety(
        db,
        session_record=session_record,
        message_text="не хочу жить",
        turn_index=2,
    )
    assert assessment.classification == "safe"
    # Should have been updated to 'safe' despite the text being the same as in turn 1
    assert session_record.safety_classification == "safe"
    
    signal2 = db.exec(
        select(SafetySignal)
        .where(SafetySignal.session_id == session_id)
        .where(SafetySignal.turn_index == 2)
    ).first()
    assert signal2 is None

    db.rollback()
