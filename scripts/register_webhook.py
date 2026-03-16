#!/usr/bin/env python3
"""Register the Telegram webhook for this bot.

Usage:
    uv run scripts/register_webhook.py

Required environment variables:
    TELEGRAM_BOT_TOKEN  — Bot API token from @BotFather
    WEBHOOK_URL         — Public HTTPS URL of the webhook endpoint
                          (e.g. https://your-domain.com/api/v1/telegram/webhook)

Exit codes:
    0 — Webhook registered successfully (Telegram returned ok: true)
    1 — Missing env variables or Telegram returned ok: false
"""
from __future__ import annotations

import json
import os
import sys

import httpx


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    webhook_url = os.environ.get("WEBHOOK_URL")

    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set.", file=sys.stderr)
        sys.exit(1)

    if not webhook_url:
        print("ERROR: WEBHOOK_URL is not set.", file=sys.stderr)
        sys.exit(1)

    api_url = f"https://api.telegram.org/bot{token}/setWebhook"

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(api_url, json={"url": webhook_url})
        resp.raise_for_status()
        data = resp.json()

    print(json.dumps(data, indent=2, ensure_ascii=False))

    if not data.get("ok"):
        print(
            f"ERROR: Telegram returned ok=false. Description: {data.get('description', 'unknown')}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
