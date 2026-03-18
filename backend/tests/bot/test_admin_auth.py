import pytest
from sqlmodel import Session
from app.conversation.session_bootstrap import handle_session_entry
from app.core.config import settings
from unittest.mock import patch

@pytest.mark.anyio
async def test_admin_command_access_denied(db: Session):
    user_id = 99999 # Not an admin
    update = {
        "update_id": 2001,
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": "/admin"
        }
    }
    
    with patch("app.core.config.settings.ADMIN_IDS", []):
        response = await handle_session_entry(db, update)
        # Should be ignored (handled=False)
        assert response.action == "ignored"
        assert response.handled is False

@pytest.mark.anyio
async def test_admin_command_access_granted(db: Session):
    user_id = 12345
    update = {
        "update_id": 2002,
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id},
            "text": "/admin"
        }
    }
    
    with patch("app.core.config.settings.ADMIN_IDS", [user_id]):
        response = await handle_session_entry(db, update)
        assert response.action == "admin_menu"
        assert response.handled is True
        assert "Admin Dashboard" in response.messages[0].text
        assert len(response.inline_keyboard) == 3

@pytest.mark.anyio
async def test_admin_stats_callback(db: Session):
    user_id = 12345
    update = {
        "update_id": 2003,
        "callback_query": {
            "from": {"id": user_id},
            "data": "admin:stats"
        }
    }
    
    with patch("app.core.config.settings.ADMIN_IDS", [user_id]):
        response = await handle_session_entry(db, update)
        assert response.action == "admin_stats"
        assert "Системная статистика" in response.messages[0].text
        assert "Всего пользователей:" in response.messages[0].text
