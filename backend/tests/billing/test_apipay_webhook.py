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
