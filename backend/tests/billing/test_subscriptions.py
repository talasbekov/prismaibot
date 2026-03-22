import pytest
from datetime import datetime, timedelta, timezone
from sqlmodel import Session
from app.billing import repository, service
from app.billing.models import Subscription


def test_create_subscription_direct(db: Session):
    user_id = 44444
    current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=current_period_end,
        provider_type="apipay",
    )
    db.commit()

    sub = repository.get_subscription(db, user_id)
    assert sub is not None
    assert sub.status == "active"
    assert sub.current_period_end > datetime.now(timezone.utc) + timedelta(days=29)


def test_check_subscription_status_read_only(db: Session):
    """check_and_update_subscription_status must NOT mutate status, even if period has expired."""
    user_id = 55555
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=expired_time,
    )
    db.commit()

    sub = service.check_and_update_subscription_status(db, user_id)
    # Status must remain "active" — no automatic transition
    assert sub.status == "active"
    # No flush/commit should have happened
    db.expire_all()
    sub_reloaded = repository.get_subscription(db, user_id)
    assert sub_reloaded.status == "active"


def test_has_premium_access_past_due_subscription(db: Session):
    """past_due subscription (set by webhook) still grants premium access."""
    user_id = 55556
    # Simulate what grace_period_started webhook would set
    expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="past_due",
        current_period_end=expires_at,
    )
    db.commit()

    assert service.has_premium_access(db, user_id) is True


def test_has_premium_access_suspended_subscription(db: Session):
    """suspended subscription (set by subscription.expired webhook) revokes access."""
    user_id = 66666
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="suspended",
        current_period_end=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.commit()

    assert service.has_premium_access(db, user_id) is False


def test_idempotent_subscription_update(db: Session):
    user_id = 77777
    end1 = datetime.now(timezone.utc) + timedelta(days=30)
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=end1,
        provider_type="apipay",
    )
    db.commit()
    sub1 = repository.get_subscription(db, user_id)
    first_end = sub1.current_period_end

    end2 = datetime.now(timezone.utc) + timedelta(days=60)
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=end2,
        provider_type="apipay",
    )
    db.commit()
    sub2 = repository.get_subscription(db, user_id)

    assert sub2.status == "active"
    assert sub2.current_period_end > first_end
