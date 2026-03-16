"""Tests for scripts/register_webhook.py (AC1)."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


def _import_script():
    """Import register_webhook from the scripts directory."""
    import importlib.util
    import pathlib

    script_path = pathlib.Path(__file__).parents[3] / "scripts" / "register_webhook.py"
    spec = importlib.util.spec_from_file_location("register_webhook", script_path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_successful_registration(monkeypatch, capsys):
    """AC1: Given TELEGRAM_BOT_TOKEN and WEBHOOK_URL set, script exits 0 and prints ok:true."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_token")
    monkeypatch.setenv("WEBHOOK_URL", "https://example.com/api/v1/telegram/webhook")

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True, "result": True}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        module = _import_script()
        module.main()

    captured = capsys.readouterr()
    assert '"ok": true' in captured.out.lower() or "true" in captured.out.lower()


def test_missing_token_exits_1(monkeypatch):
    """Script exits with code 1 if TELEGRAM_BOT_TOKEN is not set."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("WEBHOOK_URL", "https://example.com/api/v1/telegram/webhook")

    module = _import_script()
    with pytest.raises(SystemExit) as exc_info:
        module.main()
    assert exc_info.value.code == 1


def test_missing_webhook_url_exits_1(monkeypatch):
    """Script exits with code 1 if WEBHOOK_URL is not set."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_token")
    monkeypatch.delenv("WEBHOOK_URL", raising=False)

    module = _import_script()
    with pytest.raises(SystemExit) as exc_info:
        module.main()
    assert exc_info.value.code == 1


def test_api_returns_ok_false_exits_1(monkeypatch):
    """Script exits with code 1 if Telegram API returns ok:false."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_token")
    monkeypatch.setenv("WEBHOOK_URL", "https://example.com/api/v1/telegram/webhook")

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": False, "description": "Unauthorized"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        module = _import_script()
        with pytest.raises(SystemExit) as exc_info:
            module.main()
    assert exc_info.value.code == 1
