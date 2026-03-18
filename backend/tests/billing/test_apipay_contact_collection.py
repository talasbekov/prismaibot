import pytest
from sqlmodel import Session, select
from app.conversation.session_bootstrap import handle_session_entry, TelegramWebhookResponse
from app.billing.prompts import KASPI_PHONE_REQUEST_MESSAGE

@pytest.mark.anyio
async def test_kaspi_payment_callback_requests_contact(db: Session):
    user_id = 70001
    chat_id = 70001
    
    update = {
        "update_id": 1001,
        "callback_query": {
            "from": {"id": user_id},
            "message": {"chat": {"id": chat_id}},
            "data": "pay:kaspi"
        }
    }
    
    response = await handle_session_entry(db, update)
    
    assert response.action == "request_contact"
    assert response.messages[0].text == KASPI_PHONE_REQUEST_MESSAGE
    assert response.reply_markup is not None
    assert response.reply_markup.keyboard[0][0].request_contact is True

from app.billing.models import PurchaseIntent
from app.billing.apipay_client import ApiPayInvoiceResponse
from unittest.mock import patch, MagicMock

@pytest.mark.anyio
async def test_contact_received_initiates_kaspi_invoice(db: Session):
    user_id = 70003
    chat_id = 70003
    phone = "77019998877"
    
    update = {
        "update_id": 1003,
        "message": {
            "from": {"id": user_id},
            "chat": {"id": chat_id},
            "contact": {
                "phone_number": phone,
                "first_name": "Test"
            }
        }
    }
    
    mock_response = ApiPayInvoiceResponse(
        id=12345,
        status="pending",
        amount=3000.0,
        external_order_id="some-uuid"
    )
    
    with patch("app.billing.apipay_client.ApiPayClient.create_invoice", return_value=mock_response) as mock_create:
        response = await handle_session_entry(db, update)
        
        assert response.action == "contact_received"
        assert "Счет на 3000 ₸ отправлен" in response.messages[0].text
        assert "kaspi_invoice_initiated" in response.signals
        
        # Verify DB
        intent = db.exec(
            select(PurchaseIntent).where(PurchaseIntent.telegram_user_id == user_id)
        ).one()
        assert intent.provider_type == "apipay"
        assert intent.provider_invoice_id == "12345"
        assert intent.phone_number == "87019998877" # normalized
        
        mock_create.assert_called_once()
