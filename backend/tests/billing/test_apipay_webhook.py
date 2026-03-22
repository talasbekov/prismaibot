import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.billing.repository import create_purchase_intent
from app.billing.models import PurchaseIntent, Subscription, UserAccessState
from app.core.config import settings
from unittest.mock import patch, AsyncMock, ANY

client = TestClient(app)

@pytest.fixture
def webhook_secret():
    return "test_secret"

def test_apipay_webhook_invalid_signature(webhook_secret):
    response = client.post(
        f"{settings.API_V1_STR}/billing/apipay/webhook",
        json={"event": "test"},
        headers={"X-Webhook-Signature": "sha256=invalid"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_signature"

@pytest.mark.anyio
async def test_apipay_webhook_paid_success(db: Session, webhook_secret):
    user_id = 80001
    provider_invoice_id = "123"
    
    # 1. Create pending intent
    create_purchase_intent(
        db,
        telegram_user_id=user_id,
        invoice_payload=f"apipay_{provider_invoice_id}",
        amount=3000,
        currency="KZT",
        provider_type="apipay",
        provider_invoice_id=provider_invoice_id
    )
    db.commit()
    
    payload = {
        "event": "invoice.status_changed",
        "invoice": {
            "id": 123,
            "status": "paid"
        }
    }

    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    
    with (
        patch("app.billing.api.verify_apipay_signature", return_value=True),
        patch("app.billing.service.send_telegram_message", new_callable=AsyncMock) as mock_send
    ):
        response = client.post(
            f"{settings.API_V1_STR}/billing/apipay/webhook",
            content=body,
            headers={"X-Webhook-Signature": signature}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "payment_confirmed"
        
        # Verify DB updates
        db.expire_all()
        intent = db.exec(select(PurchaseIntent).where(PurchaseIntent.telegram_user_id == user_id)).one()
        assert intent.status == "completed"
        
        state = db.exec(select(UserAccessState).where(UserAccessState.telegram_user_id == user_id)).one()
        assert state.access_tier == "premium"
        
        sub = db.exec(select(Subscription).where(Subscription.telegram_user_id == user_id)).one()
        assert sub.status == "active"
        
        mock_send.assert_called_once_with(user_id, ANY)

def test_apipay_webhook_intent_not_found(webhook_secret):
    payload = {
        "event": "invoice.status_changed",
        "invoice": {
            "id": 999,
            "status": "paid"
        }
    }
    body = json.dumps(payload).encode()

    with patch("app.billing.api.verify_apipay_signature", return_value=True):
        response = client.post(
            f"{settings.API_V1_STR}/billing/apipay/webhook",
            content=body,
            headers={"X-Webhook-Signature": "sha256=dummy"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "error"
        assert response.json()["message"] == "intent_not_found"


@pytest.mark.anyio
async def test_apipay_webhook_subscription_payment_failed_no_status_change(db: Session):
    """payment_failed should NOT set past_due — just log and notify with retry message."""
    from app.billing.repository import create_or_update_subscription
    from datetime import datetime, timedelta, timezone

    user_id = 80010
    provider_sub_id = "999"
    end = datetime.now(timezone.utc) + timedelta(days=10)
    create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=end,
        provider_type="apipay",
        provider_subscription_id=provider_sub_id,
    )
    db.commit()

    payload = {
        "event": "subscription.payment_failed",
        "subscription": {"id": 999},
    }
    body = json.dumps(payload).encode()

    with (
        patch("app.billing.api.verify_apipay_signature", return_value=True),
        patch("app.billing.service.send_telegram_message", new_callable=AsyncMock) as mock_send,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/billing/apipay/webhook",
            content=body,
            headers={"X-Webhook-Signature": "sha256=dummy"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Status must remain "active" — no state mutation
    db.expire_all()
    from sqlmodel import select
    from app.billing.models import Subscription
    sub = db.exec(select(Subscription).where(Subscription.telegram_user_id == user_id)).one()
    assert sub.status == "active"

    # User must be notified with retry message
    from app.billing.prompts import PAYMENT_RETRY_MESSAGE
    mock_send.assert_called_once_with(user_id, PAYMENT_RETRY_MESSAGE)


def test_apipay_webhook_invoice_refunded_ignored():
    """invoice.refunded should be logged and return ok without DB changes."""
    payload = {
        "event": "invoice.refunded",
        "refund": {"id": 5, "amount": "2000.00", "status": "completed"},
        "invoice": {"id": 42, "external_order_id": "order_123"},
    }
    body = json.dumps(payload).encode()

    with patch("app.billing.api.verify_apipay_signature", return_value=True):
        response = client.post(
            f"{settings.API_V1_STR}/billing/apipay/webhook",
            content=body,
            headers={"X-Webhook-Signature": "sha256=dummy"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["message"] == "refund_logged"
