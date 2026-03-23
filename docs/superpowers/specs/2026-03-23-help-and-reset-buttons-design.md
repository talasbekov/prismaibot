---
title: Help and Reset ReplyKeyboard Buttons
date: 2026-03-23
status: approved
---

# Design: Help and Reset ReplyKeyboard Buttons

## Overview

Add two persistent ReplyKeyboard buttons to the Telegram bot:
- **❓ Помощь** — sends a static message explaining the 7 brainstorming phases
- **🔄 Начать заново** — resets the session and restarts from `collect_topic`

## Scope

- Brainstorming flow only (reflection phases excluded)
- No inline keyboards, no multi-step menus
- No chat history deletion (Telegram API limitation — bots cannot delete old messages)

## ReplyKeyboard

The keyboard is shown on `/start` response and persists (`one_time_keyboard: false`, `resize_keyboard: true`):

```
[ ❓ Помощь ]  [ 🔄 Начать заново ]
```

Displayed as a single row of two buttons.

## Feature 1: "❓ Помощь" Button

**Trigger:** user sends the text `"❓ Помощь"`

**Behavior:**
- Bot replies with a single static message describing all 7 brainstorming phases
- Session state is NOT modified — user continues from where they left off

**Message content:**
```
🧠 Как работает мозговой штурм:

1. Тема — ты называешь, над чем хочешь подумать
2. Цель — уточняем, чего ты хочешь достичь
3. Ограничения — что нельзя или важно учесть
4. Идеи — бот помогает генерировать идеи свободно
5. Группировка — похожие идеи объединяются в кластеры
6. Приоритеты — выбираем самые важные направления
7. План действий — конкретные шаги на основе лучших идей
```

**Implementation:**
- Add handler in `session_bootstrap.py` alongside `/start`, `/cancel`, etc.
- `if message.text.strip() == "❓ Помощь":` → return static `TelegramWebhookResponse`
- No DB writes, no session lookup beyond what's already done

## Feature 2: "🔄 Начать заново" Button

**Trigger:** user sends the text `"🔄 Начать заново"`

**Behavior:**
- Identical to `/start`: session resets, bot restarts from `collect_topic`
- No confirmation prompt — immediate reset
- Chat message history in Telegram remains (cannot be deleted by bot)

**Implementation:**
- Add handler in `session_bootstrap.py`:
  `if message.text.strip() == "🔄 Начать заново":` → delegate to `_start_brainstorming_session(...)`
- Reuses existing `/start` logic entirely

## Changes Required

| File | Change |
|------|--------|
| `backend/app/conversation/session_bootstrap.py` | Add two `if` handlers for button texts; add keyboard to `/start` response |

No new files, no schema changes, no DB migrations.

## Out of Scope

- Reflection phase explanation
- Contextual help (phase-aware messages)
- Confirmation dialog for reset
- Deleting chat history
