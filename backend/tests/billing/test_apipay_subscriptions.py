import pytest
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select
from app.billing import repository, service
from app.billing.models import Subscription, UserAccessState
from app.billing.apipay_client import ApiPaySubscriptionResponse
from unittest.mock import patch, AsyncMock

@pytest.mark.anyio
async def test_create_apipay_subscription_success(db: Session):
    user_id = 90001
    phone = "87011112233"
    
    mock_resp = ApiPaySubscriptionResponse(
        id=555,
        status="active",
        amount=3000.0,
        billing_period="monthly"
    )    
    with patch("app.billing.apipay_client.ApiPayClient.create_subscription", return_value=mock_resp):
        res = await service.create_apipay_subscription(db, telegram_user_id=user_id, phone_number=phone)
        assert "оформлена" in res
        
        sub = repository.get_subscription(db, user_id)
        assert sub.provider_subscription_id == "555"
        assert sub.provider_type == "apipay"
        assert sub.status == "active"

@pytest.mark.anyio
async def test_webhook_subscription_payment_succeeded(db: Session):
    user_id = 90002
    provider_sub_id = "789"
    
    # Setup sub
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=1),
        provider_type="apipay",
        provider_subscription_id=provider_sub_id
    )
    db.commit()
    
    payload = {
        "event": "subscription.payment_succeeded",
        "subscription": {"id": 789}
    }
    
    await service.process_apipay_webhook(db, payload)
    
    db.expire_all()
    sub = repository.get_subscription(db, user_id)
    # Extended to ~30 days from now
    assert sub.current_period_end > datetime.now(timezone.utc) + timedelta(days=29)

@pytest.mark.anyio
async def test_webhook_subscription_payment_failed(db: Session):
    user_id = 90003
    provider_sub_id = "456"
    
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=1),
        provider_type="apipay",
        provider_subscription_id=provider_sub_id
    )
    db.commit()
    
    payload = {
        "event": "subscription.payment_failed",
        "subscription": {"id": 456}
    }
    
    with patch("app.billing.service.send_telegram_message", new_callable=AsyncMock) as mock_send:
        await service.process_apipay_webhook(db, payload)
        
        db.expire_all()
        sub = repository.get_subscription(db, user_id)
        assert sub.status == "past_due"
        mock_send.assert_called_once()

@pytest.mark.anyio
async def test_cancel_apipay_subscription(db: Session):
    user_id = 90004
    provider_sub_id = "666"
    
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=10),
        provider_type="apipay",
        provider_subscription_id=provider_sub_id
    )
    db.commit()
    
    with patch("app.billing.apipay_client.ApiPayClient.cancel_subscription", return_value=True) as mock_cancel:
        success = await service.cancel_apipay_subscription(db, telegram_user_id=user_id)
        assert success is True
        
        db.expire_all()
        sub = repository.get_subscription(db, user_id)
        assert sub.cancel_at_period_end is True
        mock_cancel.assert_called_once_with(666)
