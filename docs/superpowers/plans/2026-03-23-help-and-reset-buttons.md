# Help and Reset Buttons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two persistent ReplyKeyboard buttons — "❓ Помощь" (shows phase guide) and "🔄 Начать заново" (resets session) — to the Telegram bot's `/start` response.

**Architecture:** All changes are isolated to `session_bootstrap.py`. A new `HELP_MESSAGE` string constant is added. Two `if` handlers are inserted alongside the existing `/start`/`/cancel` handlers. `_start_brainstorming_session` is updated to attach a `ReplyKeyboardMarkup` to its response.

**Tech Stack:** Python, FastAPI, SQLModel, pytest, Telegram Bot API

---

## File Map

| File | Change |
|------|--------|
| `backend/app/conversation/session_bootstrap.py` | Add `HELP_MESSAGE` constant; update `_start_brainstorming_session` to include `reply_markup`; add two button text handlers |
| `backend/tests/api/routes/test_telegram_session_entry.py` | Add 3 tests: keyboard on `/start`, help handler, reset handler |

---

## Task 1: Add HELP_MESSAGE constant and keyboard to `/start`

**Files:**
- Modify: `backend/app/conversation/session_bootstrap.py`
- Test: `backend/tests/api/routes/test_telegram_session_entry.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/api/routes/test_telegram_session_entry.py`:

```python
def test_start_includes_reply_keyboard_with_help_and_reset(
    client: TestClient, db: Session
) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 1,
                "text": "/start",
                "chat": {"id": 2001, "type": "private"},
                "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
            }
        },
    )

    payload = response.json()
    assert payload["status"] == "ok"
    markup = payload["reply_markup"]
    assert markup is not None
    assert markup["resize_keyboard"] is True
    assert markup["one_time_keyboard"] is False
    button_texts = [btn["text"] for btn in markup["keyboard"][0]]
    assert "❓ Помощь" in button_texts
    assert "🔄 Начать заново" in button_texts
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /home/erda/Музыка/goals
uv run pytest backend/tests/api/routes/test_telegram_session_entry.py::test_start_includes_reply_keyboard_with_help_and_reset -v
```

Expected: FAIL — `reply_markup` is `None`

- [ ] **Step 3: Add constants to `session_bootstrap.py`**

After the `DELETE_REQUEST_ERROR_PROMPT` block (around line 113), add:

```python
HELP_MESSAGE = (
    "🧠 *Как работает мозговой штурм:*\n\n"
    "1. *Тема* — ты называешь, над чем хочешь подумать\n"
    "2. *Цель* — уточняем, чего ты хочешь достичь\n"
    "3. *Ограничения* — что нельзя или важно учесть\n"
    "4. *Идеи* — бот помогает генерировать идеи свободно\n"
    "5. *Группировка* — похожие идеи объединяются в кластеры\n"
    "6. *Приоритеты* — выбираем самые важные направления\n"
    "7. *План действий* — конкретные шаги на основе лучших идей"
)

_HELP_BUTTON_TEXT = "❓ Помощь"
_RESET_BUTTON_TEXT = "🔄 Начать заново"

_PERSISTENT_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[ReplyButton(text=_HELP_BUTTON_TEXT), ReplyButton(text=_RESET_BUTTON_TEXT)]],
    resize_keyboard=True,
    one_time_keyboard=False,
)
```

Note: `parse_mode` in `bot/api.py` is `"Markdown"` (v1), not MarkdownV2, so regular `*bold*` syntax applies.

- [ ] **Step 4: Update `_start_brainstorming_session` to attach keyboard**

In `_start_brainstorming_session` (around line 1439), update the return:

```python
    response = _build_response(
        action=action,
        session_record=active_session,
        message_texts=[OPENING_PROMPT, FALLBACKS["collect_topic"]],
        extra_signals=("typing",),
    )
    response.reply_markup = _PERSISTENT_KEYBOARD
    return response
```

- [ ] **Step 5: Run test to confirm it passes**

```bash
cd /home/erda/Музыка/goals
uv run pytest backend/tests/api/routes/test_telegram_session_entry.py::test_start_includes_reply_keyboard_with_help_and_reset -v
```

Expected: PASS

- [ ] **Step 6: Run full session entry test file to check for regressions**

```bash
cd /home/erda/Музыка/goals
uv run pytest backend/tests/api/routes/test_telegram_session_entry.py -v
```

Expected: all existing tests pass (the existing `/start` test does not assert `reply_markup is None`)

- [ ] **Step 7: Commit**

```bash
git add backend/app/conversation/session_bootstrap.py backend/tests/api/routes/test_telegram_session_entry.py
git commit -m "feat: add persistent help/reset keyboard to /start response"
```

---

## Task 2: Handle "❓ Помощь" and "🔄 Начать заново" buttons

**Files:**
- Modify: `backend/app/conversation/session_bootstrap.py`
- Test: `backend/tests/api/routes/test_telegram_session_entry.py`

- [ ] **Step 1: Write failing tests for both buttons**

Add to the test file:

```python
def test_help_button_returns_phase_guide_without_resetting_session(
    client: TestClient, db: Session
) -> None:
    from unittest.mock import patch
    # Start a session
    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 1,
                "text": "/start",
                "chat": {"id": 2001, "type": "private"},
                "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
            }
        },
    )
    # Advance to collect_goal by sending a topic
    with patch("app.conversation.brainstorming.orchestrator._ask_openai", return_value="Какова цель?"):
        client.post(
            "/api/v1/telegram/webhook",
            json={
                "message": {
                    "message_id": 2,
                    "text": "Карьерный рост",
                    "chat": {"id": 2001, "type": "private"},
                    "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
                }
            },
        )

    session_row = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1001)
    ).one()
    phase_before = session_row.brainstorm_phase

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 3,
                "text": "❓ Помощь",
                "chat": {"id": 2001, "type": "private"},
                "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
            }
        },
    )

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["action"] == "help_shown"
    assert len(payload["messages"]) == 1
    assert "Как работает мозговой штурм" in payload["messages"][0]["text"]

    db.refresh(session_row)
    assert session_row.brainstorm_phase == phase_before


def test_reset_button_resets_session_like_start(
    client: TestClient, db: Session
) -> None:
    from unittest.mock import patch
    # Create and advance a session
    client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 1,
                "text": "/start",
                "chat": {"id": 2001, "type": "private"},
                "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
            }
        },
    )
    with patch("app.conversation.brainstorming.orchestrator._ask_openai", return_value="Какова цель?"):
        client.post(
            "/api/v1/telegram/webhook",
            json={
                "message": {
                    "message_id": 2,
                    "text": "Карьерный рост",
                    "chat": {"id": 2001, "type": "private"},
                    "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
                }
            },
        )

    response = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {
                "message_id": 3,
                "text": "🔄 Начать заново",
                "chat": {"id": 2001, "type": "private"},
                "from": {"id": 1001, "is_bot": False, "first_name": "Masha"},
            }
        },
    )

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["action"] == "brainstorm_reset"
    assert payload["messages"][0]["text"] == OPENING_PROMPT
    markup = payload["reply_markup"]
    assert markup is not None
    button_texts = [btn["text"] for btn in markup["keyboard"][0]]
    assert "🔄 Начать заново" in button_texts

    session_row = db.exec(
        select(TelegramSession).where(TelegramSession.telegram_user_id == 1001)
    ).one()
    assert session_row.brainstorm_phase == "collect_topic"
    assert session_row.brainstorm_data["ideas"] == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /home/erda/Музыка/goals
uv run pytest backend/tests/api/routes/test_telegram_session_entry.py::test_help_button_returns_phase_guide_without_resetting_session backend/tests/api/routes/test_telegram_session_entry.py::test_reset_button_resets_session_like_start -v
```

Expected: FAIL — button texts are routed to the brainstorming orchestrator

- [ ] **Step 3: Add both handlers to `session_bootstrap.py`**

In `handle_session_entry`, after the `/start` handler (around line 237), add:

```python
    if message.text.strip() == _HELP_BUTTON_TEXT:
        return TelegramWebhookResponse(
            status="ok",
            action="help_shown",
            handled=True,
            messages=[TelegramMessageOut(text=HELP_MESSAGE)],
        )

    if message.text.strip() == _RESET_BUTTON_TEXT:
        return _start_brainstorming_session(
            session=session,
            telegram_user_id=message.telegram_user_id,
            chat_id=message.chat_id,
            action="brainstorm_reset",
        )
```

- [ ] **Step 4: Run both tests to confirm they pass**

```bash
cd /home/erda/Музыка/goals
uv run pytest backend/tests/api/routes/test_telegram_session_entry.py::test_help_button_returns_phase_guide_without_resetting_session backend/tests/api/routes/test_telegram_session_entry.py::test_reset_button_resets_session_like_start -v
```

Expected: PASS

- [ ] **Step 5: Run full backend test suite**

```bash
cd /home/erda/Музыка/goals
uv run pytest backend/tests/ -v --tb=short
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/conversation/session_bootstrap.py backend/tests/api/routes/test_telegram_session_entry.py
git commit -m "feat: handle help and reset button texts; add tests"
```
