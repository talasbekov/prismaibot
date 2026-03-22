import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks

from app.api.deps import SessionDep
from app.conversation.session_bootstrap import (
    TelegramWebhookResponse,
    handle_session_entry,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


def _deliver_telegram_response(chat_id: int, response: TelegramWebhookResponse) -> None:
    """Deliver the structured webhook response to Telegram via Bot API."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured; cannot deliver response.")
        return

    base_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"

    with httpx.Client(timeout=10.0) as client:
        # 1. Handle typing signal if requested
        if "typing" in response.signals:
            try:
                client.post(f"{base_url}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
            except Exception:
                logger.exception("Failed to send typing chat action to chat_id=%s", chat_id)

        # 2. Deliver text messages
        for idx, message in enumerate(response.messages):
            if idx > 0:
                time.sleep(0.5)
            payload: dict[str, Any] = {"chat_id": chat_id, "text": message.text, "parse_mode": "Markdown"}
            
            # Add inline keyboard if present for the LAST message only (common pattern)
            if response.inline_keyboard and message == response.messages[-1]:
                keyboard = []
                for row in response.inline_keyboard:
                    row_data = []
                    for btn in row:
                        btn_data = {"text": btn.text}
                        if btn.callback_data:
                            btn_data["callback_data"] = btn.callback_data
                        elif btn.url:
                            btn_data["url"] = btn.url
                        row_data.append(btn_data)
                    keyboard.append(row_data)
                payload["reply_markup"] = {"inline_keyboard": keyboard}
            elif response.reply_markup and message == response.messages[-1]:
                payload["reply_markup"] = response.reply_markup.model_dump()

            try:
                res = client.post(f"{base_url}/sendMessage", json=payload)
                res.raise_for_status()
            except Exception:
                logger.exception("Failed to deliver message to chat_id=%s: %s", chat_id, message.text[:50])


@router.post("/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook(
    update: dict[str, Any],
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> TelegramWebhookResponse:
    """Telegram-first ingress that delegates conversation state to the session seam."""
    response = await handle_session_entry(session, update, background_tasks=background_tasks)
    
    # Extract chat_id to deliver the response asynchronously
    chat_id = None
    if "message" in update:
        chat_id = update["message"].get("chat", {}).get("id")
    elif "callback_query" in update:
        chat_id = update["callback_query"].get("message", {}).get("chat", {}).get("id")

    if chat_id and response.handled:
        background_tasks.add_task(_deliver_telegram_response, chat_id, response)
        
    return response
