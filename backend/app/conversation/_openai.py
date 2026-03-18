"""Thin OpenAI client using httpx (no openai package required)."""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_MODEL = "gpt-4o-mini"
_TIMEOUT = 20.0


def call_chat(
    messages: list[dict],
    *,
    max_tokens: int = 400,
    temperature: float = 0.7,
) -> str | None:
    """Call OpenAI Chat Completions and return the text content, or None on failure."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("OpenAI API call failed")
        return None


async def async_call_chat(
    messages: list[dict],
    *,
    max_tokens: int = 400,
    temperature: float = 0.7,
) -> str | None:
    """Call OpenAI Chat Completions asynchronously."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("OpenAI Async API call failed")
        return None


def parse_two_messages(text: str) -> tuple[str, str] | None:
    """Split GPT response into exactly two messages separated by '---'."""
    parts = text.strip().split("---")
    if len(parts) < 2:
        return None
    msg1 = parts[0].strip()
    msg2 = parts[1].strip()
    if not msg1 or not msg2:
        return None
    return msg1, msg2
