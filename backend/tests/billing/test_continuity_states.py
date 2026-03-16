from datetime import datetime, timezone

import pytest
from sqlmodel import Session, select, text

from app.billing.models import UserAccessState
from app.conversation.session_bootstrap import handle_session_entry
from app.models import (
    ProfileFact,
    SessionSummary,
    TelegramSession,
)


@pytest.fixture
def clear_billing_and_memory_tables(db: Session):
    db.rollback()
    db.exec(text("DELETE FROM user_access_states"))
    db.exec(text("DELETE FROM purchase_intents"))
    db.exec(text("DELETE FROM free_session_events"))
    db.exec(text("DELETE FROM summary_generation_signal"))
    db.exec(text("DELETE FROM profile_fact"))
    db.exec(text("DELETE FROM session_summary"))
    db.exec(text("DELETE FROM operator_investigation"))
    db.exec(text("DELETE FROM operator_alert"))
    db.exec(text("DELETE FROM safety_signal"))
    db.exec(text("DELETE FROM telegram_session"))
    db.commit()

def test_cancellation_preserves_memory_records(db: Session, clear_billing_and_memory_tables):
    user_id = 12345
    chat_id = 67890

    # 1. Setup premium user with memory records
    state = UserAccessState(telegram_user_id=user_id, access_tier="premium")

    # Need a session for memory records to refer to
    tsession = TelegramSession(telegram_user_id=user_id, chat_id=chat_id)
    db.add(tsession)
    db.flush()

    summary = SessionSummary(
        telegram_user_id=user_id,
        session_id=tsession.id,
        takeaway="Prior takeaway",
        reflective_mode="deep",
        source_turn_count=1
    )
    fact = ProfileFact(
        telegram_user_id=user_id,
        source_session_id=tsession.id,
        fact_key="user_interest",
        fact_value="User fact",
        confidence="medium"
    )
    db.add(state)
    db.add(summary)
    db.add(fact)
    db.commit()

    # 2. Cancel premium
    cancel_update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": "/cancel"
        }
    }
    response = handle_session_entry(db, cancel_update)
    assert response.status == "ok"
    assert "сохраняются" in response.messages[0].text

    # 3. Verify access is free but memory records STILL EXIST
    db.expire_all()
    updated_state = db.exec(select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)).one()
    assert updated_state.access_tier == "free"

    summaries = db.exec(select(SessionSummary).where(SessionSummary.telegram_user_id == user_id)).all()
    assert len(summaries) == 1
    assert summaries[0].takeaway == "Prior takeaway"

    facts = db.exec(select(ProfileFact).where(ProfileFact.telegram_user_id == user_id)).all()
    assert len(facts) == 1
    assert facts[0].fact_value == "User fact"

def test_payment_upgrade_enables_immediate_access_without_paywall(db: Session, clear_billing_and_memory_tables):
    user_id = 11111
    chat_id = 22222

    # 1. User reached threshold
    state = UserAccessState(
        telegram_user_id=user_id,
        access_tier="free",
        threshold_reached_at=datetime.now(timezone.utc)
    )
    db.add(state)
    db.commit()

    # 2. Message returns paywall
    msg_update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": "Hello"
        }
    }
    response = handle_session_entry(db, msg_update)
    assert response.action == "paywall_gate"

    # 3. Upgrade to premium (simulated payment confirmation)
    state.access_tier = "premium"
    db.add(state)
    db.commit()

    # 4. Next message in same flow passes gate immediately
    response2 = handle_session_entry(db, msg_update)
    assert response2.action != "paywall_gate"
    assert response2.status == "ok"

def test_cancellation_restores_paywall_if_threshold_already_reached(db: Session, clear_billing_and_memory_tables):
    user_id = 33333
    chat_id = 44444

    # 1. User reached threshold then upgraded to premium
    state = UserAccessState(
        telegram_user_id=user_id,
        access_tier="premium",
        threshold_reached_at=datetime.now(timezone.utc)
    )
    db.add(state)
    db.commit()

    # 2. Message passes (premium)
    msg_update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": "Hello"
        }
    }
    response = handle_session_entry(db, msg_update)
    assert response.action != "paywall_gate"

    # 3. Cancel premium
    cancel_update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": "/cancel"
        }
    }
    handle_session_entry(db, cancel_update)

    # 4. Next message is blocked again (threshold still set)
    response2 = handle_session_entry(db, msg_update)
    assert response2.action == "paywall_gate"

def test_full_lifecycle_continuity(db: Session, clear_billing_and_memory_tables):
    user_id = 77777
    chat_id = 88888

    # 1. Free session with memory
    tsession = TelegramSession(telegram_user_id=user_id, chat_id=chat_id)
    db.add(tsession)
    db.flush()

    state = UserAccessState(telegram_user_id=user_id, access_tier="free")
    summary = SessionSummary(
        telegram_user_id=user_id,
        session_id=tsession.id,
        takeaway="The important memory",
        reflective_mode="deep",
        source_turn_count=1
    )
    db.add(state)
    db.add(summary)
    db.commit()

    # 2. Reach threshold
    state.threshold_reached_at = datetime.now(timezone.utc)
    db.add(state)
    db.commit()

    # 3. Verify paywall
    msg_update = {
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "text": "Hello again"
        }
    }
    assert handle_session_entry(db, msg_update).action == "paywall_gate"

    # 4. Upgrade
    state.access_tier = "premium"
    db.add(state)
    db.commit()

    # 5. Verify premium session with recall (first turn)
    # Note: we need a new chat_id or clear sessions to trigger is_first_turn if we want to check recall
    # but here we just check it passes gate.
    response = handle_session_entry(db, msg_update)
    assert response.action != "paywall_gate"

    # 6. Cancel
    cancel_update = {"message": {"from": {"id": user_id}, "chat": {"id": chat_id}, "text": "/cancel"}}
    handle_session_entry(db, cancel_update)

    # 7. Verify memory still exists and paywall is back
    db.expire_all()
    assert db.exec(select(SessionSummary).where(SessionSummary.telegram_user_id == user_id)).one().takeaway == "The important memory"
    assert handle_session_entry(db, msg_update).action == "paywall_gate"
