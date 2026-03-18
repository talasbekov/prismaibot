import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

async def send_telegram_message(chat_id: int, text: str) -> bool:
    """Send a plain text message to a Telegram chat."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return False
        
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, timeout=10.0)
            res.raise_for_status()
            return True
    except Exception:
        logger.exception("Failed to send telegram message to chat_id=%s", chat_id)
        return False

def is_admin(user_id: int) -> bool:
    """Check if a user has administrative access."""
    return user_id in settings.ADMIN_IDS
