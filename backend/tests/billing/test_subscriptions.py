import pytest
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select
from app.billing import repository, service
from app.billing.models import Subscription, UserAccessState
from unittest.mock import patch

def test_create_subscription_on_payment(db: Session):
    user_id = 44444
    service.confirm_payment_and_upgrade(
        db,
        invoice_payload="test_payload",
        telegram_payment_charge_id="charge_123",
        telegram_user_id=user_id
    )
    db.commit()
    
    sub = repository.get_subscription(db, user_id)
    assert sub is not None
    assert sub.status == "active"
    # expires in ~30 days
    assert sub.current_period_end > datetime.now(timezone.utc) + timedelta(days=29)

def test_grace_period_access(db: Session):
    user_id = 55555
    # Create an expired subscription (just-now expired)
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=expired_time
    )
    db.commit()
    
    # Check status - should move to past_due
    sub = service.check_and_update_subscription_status(db, user_id)
    assert sub.status == "past_due"
    
    # Should still have premium access during grace period
    assert service.has_premium_access(db, user_id) is True

def test_suspended_access_after_grace_period(db: Session):
    user_id = 66666
    # Create subscription that expired > 24h ago
    expired_time = datetime.now(timezone.utc) - timedelta(hours=25)
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=expired_time
    )
    db.commit()
    
    # Check status - should move to suspended
    sub = service.check_and_update_subscription_status(db, user_id)
    assert sub.status == "suspended"
    
    # Should NOT have premium access
    assert service.has_premium_access(db, user_id) is False
    
    # UserAccessState should be downgraded to free
    state = repository.get_or_create_user_access_state(db, user_id)
    assert state.access_tier == "free"

def test_idempotent_subscription_update(db: Session):
    user_id = 77777
    # First payment
    service.confirm_payment_and_upgrade(
        db,
        invoice_payload="p1",
        telegram_payment_charge_id="c1",
        telegram_user_id=user_id
    )
    db.commit()
    sub1 = repository.get_subscription(db, user_id)
    first_end = sub1.current_period_end
    
    # Second payment (manual or renewal)
    service.confirm_payment_and_upgrade(
        db,
        invoice_payload="p2",
        telegram_payment_charge_id="c2",
        telegram_user_id=user_id
    )
    db.commit()
    sub2 = repository.get_subscription(db, user_id)
    
    assert sub2.status == "active"
    assert sub2.current_period_end > first_end
