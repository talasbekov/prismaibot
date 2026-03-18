# backend/tests/operator/test_billing_review.py
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, delete

from app.billing.models import PurchaseIntent, UserAccessState
from app.ops.billing_review import get_user_billing_context, list_billing_issues


def test_list_billing_issues_empty_on_clean_db(db: Session) -> None:
    # Clear session-scoped DB leftovers to ensure clean baseline for this test
    db.execute(delete(PurchaseIntent))
    db.execute(delete(UserAccessState))
    db.commit()
    
    issues = list_billing_issues(db)
    assert issues == []


def test_list_billing_issues_detects_failed_payment(db: Session) -> None:
    intent = PurchaseIntent(
        telegram_user_id=70001,
        invoice_payload="premium_70001",
        amount=100,
        status="failed",
    )
    db.add(intent)
    db.commit()

    issues = list_billing_issues(db)
    assert any(
        i.telegram_user_id == 70001 and i.issue_category == "payment_failed"
        for i in issues
    )


def test_list_billing_issues_detects_stale_pending(db: Session) -> None:
    stale_time = datetime.now(timezone.utc) - timedelta(hours=25)
    intent = PurchaseIntent(
        telegram_user_id=70002,
        invoice_payload="premium_70002",
        amount=100,
        status="pending",
        created_at=stale_time,
        updated_at=stale_time,
    )
    db.add(intent)
    db.commit()

    issues = list_billing_issues(db)
    assert any(
        i.telegram_user_id == 70002 and i.issue_category == "payment_stale_pending"
        for i in issues
    )


def test_list_billing_issues_ignores_fresh_pending(db: Session) -> None:
    intent = PurchaseIntent(
        telegram_user_id=70003,
        invoice_payload="premium_70003",
        amount=100,
        status="pending",
        # created_at defaults to now — fresh, should NOT be flagged
    )
    db.add(intent)
    db.commit()

    issues = list_billing_issues(db)
    assert not any(
        i.telegram_user_id == 70003
        for i in issues
    )


def test_list_billing_issues_detects_completed_no_access(db: Session) -> None:
    intent = PurchaseIntent(
        telegram_user_id=70004,
        invoice_payload="premium_70004",
        amount=100,
        status="completed",
        provider_payment_charge_id="charge_abc",
    )
    state = UserAccessState(
        telegram_user_id=70004,
        access_tier="free",
        free_sessions_used=3,
    )
    db.add(intent)
    db.add(state)
    db.commit()

    issues = list_billing_issues(db)
    assert any(
        i.telegram_user_id == 70004 and i.issue_category == "payment_completed_no_access"
        for i in issues
    )


def test_list_billing_issues_detects_premium_access_no_payment(db: Session) -> None:
    state = UserAccessState(
        telegram_user_id=70005,
        access_tier="premium",
        free_sessions_used=3,
    )
    db.add(state)
    db.commit()

    issues = list_billing_issues(db)
    assert any(
        i.telegram_user_id == 70005 and i.issue_category == "premium_access_no_payment"
        for i in issues
    )


def test_get_user_billing_context_returns_none_for_unknown(db: Session) -> None:
    result = get_user_billing_context(db, telegram_user_id=99999)
    assert result is None


def test_get_user_billing_context_returns_intents_and_access(db: Session) -> None:
    state = UserAccessState(
        telegram_user_id=70006,
        access_tier="premium",
        free_sessions_used=2,
    )
    intent = PurchaseIntent(
        telegram_user_id=70006,
        invoice_payload="premium_70006",
        amount=100,
        status="completed",
        provider_payment_charge_id="charge_xyz",
    )
    db.add(state)
    db.add(intent)
    db.commit()

    ctx = get_user_billing_context(db, telegram_user_id=70006)
    assert ctx is not None
    assert ctx.access_tier == "premium"
    assert ctx.free_sessions_used == 2
    assert len(ctx.purchase_intents) == 1
    assert ctx.purchase_intents[0]["status"] == "completed"


def test_list_billing_issues_pagination(db: Session) -> None:
    # Check current count to be robust against session-wide DB
    initial_issues = list_billing_issues(db, limit=1000)
    base_count = len(initial_issues)

    # Create 5 failed intents
    for i in range(5):
        intent = PurchaseIntent(
            telegram_user_id=80000 + i,
            invoice_payload=f"premium_80000_{i}",
            amount=100,
            status="failed",
        )
        db.add(intent)
    db.commit()

    total_count = base_count + 5

    # Test limit=2
    issues = list_billing_issues(db, limit=2)
    assert len(issues) == 2

    # Test offset
    # If we have total_count, and offset is total_count - 2, we should get 2
    offset = total_count - 2
    issues = list_billing_issues(db, offset=offset)
    assert len(issues) == 2
