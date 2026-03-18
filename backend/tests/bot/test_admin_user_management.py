import pytest
from sqlmodel import Session, select
from app.conversation.session_bootstrap import handle_session_entry
from app.billing.models import UserAccessState, Subscription
from unittest.mock import patch, AsyncMock, ANY

@pytest.mark.anyio
async def test_admin_user_lookup_success(db: Session):
    admin_id = 12345
    target_user_id = 88888
    
    # Setup target user
    db.add(UserAccessState(telegram_user_id=target_user_id, access_tier="free", free_sessions_used=2))
    db.commit()
    
    update = {
        "update_id": 3001,
        "message": {
            "from": {"id": admin_id},
            "chat": {"id": admin_id},
            "text": str(target_user_id)
        }
    }
    
    with patch("app.core.config.settings.ADMIN_IDS", [admin_id]):
        response = await handle_session_entry(db, update)
        assert response.action == "admin_user_details"
        assert f"Информация о пользователе {target_user_id}" in response.messages[0].text
        assert "Тариф: free" in response.messages[0].text
        assert "🚀 Выдать Premium" in response.inline_keyboard[0][0].text

@pytest.mark.anyio
async def test_admin_grant_premium(db: Session):
    admin_id = 12345
    target_user_id = 77777
    
    update = {
        "update_id": 3002,
        "callback_query": {
            "from": {"id": admin_id},
            "data": f"admin:grant_premium:{target_user_id}"
        }
    }
    
    with (
        patch("app.core.config.settings.ADMIN_IDS", [admin_id]),
        patch("app.bot.utils.send_telegram_message", new_callable=AsyncMock) as mock_send
    ):
        response = await handle_session_entry(db, update)
        assert response.action == "admin_premium_granted"
        
        # Verify DB
        db.expire_all()
        state = db.exec(select(UserAccessState).where(UserAccessState.telegram_user_id == target_user_id)).one()
        assert state.access_tier == "premium"
        
        sub = db.exec(select(Subscription).where(Subscription.telegram_user_id == target_user_id)).one()
        assert sub.status == "active"
        assert sub.provider_type == "manual_admin"
        
        from unittest.mock import ANY
        mock_send.assert_called_once_with(target_user_id, ANY)

@pytest.mark.anyio
async def test_admin_investigate_alert(db: Session):
    from app.models import OperatorAlert, TelegramSession
    admin_id = 12345
    user_id = 11111
    
    # 1. Setup session and alert
    session_record = TelegramSession(telegram_user_id=user_id, chat_id=user_id, last_user_message="I feel bad")
    db.add(session_record)
    db.commit()
    
    alert = OperatorAlert(
        session_id=session_record.id,
        telegram_user_id=user_id,
        classification="crisis",
        trigger_category="self_harm",
        confidence="high"
    )
    db.add(alert)
    db.commit()
    
    # 2. List alerts
    update_list = {
        "update_id": 4001,
        "callback_query": {
            "from": {"id": admin_id},
            "data": "admin:alerts"
        }
    }
    with patch("app.core.config.settings.ADMIN_IDS", [admin_id]):
        response = await handle_session_entry(db, update_list)
        assert response.action == "admin_alerts_list"
        assert "self_harm" in response.messages[0].text
        assert str(alert.id) in response.inline_keyboard[0][0].callback_data
        
    # 3. Investigate
    update_inv = {
        "update_id": 4002,
        "callback_query": {
            "from": {"id": admin_id},
            "data": f"admin:investigate:{alert.id}"
        }
    }
    with patch("app.core.config.settings.ADMIN_IDS", [admin_id]):
        response = await handle_session_entry(db, update_inv)
        assert response.action == "admin_investigation_details"
        assert "I feel bad" in response.messages[0].text
        
        # Verify Investigation record created
        db.expire_all()
        from app.models import OperatorInvestigation
        inv = db.exec(select(OperatorInvestigation).where(OperatorInvestigation.operator_alert_id == alert.id)).one()
        assert inv.status == "opened"
        assert inv.requested_by == f"admin:{admin_id}"
