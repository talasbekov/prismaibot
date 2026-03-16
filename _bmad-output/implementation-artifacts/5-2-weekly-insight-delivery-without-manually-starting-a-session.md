# Story 5.2: Delivery weekly insight без необходимости вручную стартовать сессию

Status: done

## Story

As a user who may not actively reopen the bot every time,
I want получать periodic reflective insight без ручного запуска новой сессии,
So that продукт может мягко возвращать ценность и напоминать о continuity outside acute moments.

## Acceptance Criteria

1. **Given** для пользователя уже подготовлен valid reflective insight (`status = "pending_delivery"`, непустой `insight_text`), **When** наступает scheduled delivery time, **Then** система отправляет insight пользователю через Telegram Bot API без необходимости вручную стартовать сессию, **And** delivery происходит через `sendMessage` endpoint. [Source: epics.md#story-52-AC1]

2. **Given** insight доставляется proactively rather than in-session, **When** пользователь получает это сообщение, **Then** message feels like low-pressure reflective support, **And** не воспринимается как spammy nudge, aggressive re-engagement tactic или generic notification blast. [Source: epics.md#story-52-AC2]

3. **Given** delivery model зависит от scheduler/job execution, **When** система запускает batch insight delivery, **Then** delivery pipeline использует explicit async/scheduled flow (отдельный scheduler job), **And** не блокирует active conversational traffic or main request path. [Source: epics.md#story-52-AC3]

4. **Given** пользователь недоступен, delivery fails, или Telegram API возвращает ошибку, **When** система не может успешно отправить insight, **Then** failure становится observable и traceable через `delivery_error` field и логи, **And** продукт не предполагает silently, что value already delivered — `status` остается `"pending_delivery"` при транзиентных ошибках или выставляется `"delivery_failed"` при окончательных. [Source: epics.md#story-52-AC4]

5. **Given** пользователю не следует получать irrelevant or low-quality periodic message, **When** insight delivery readiness оценивается перед отправкой, **Then** система отправляет только insights с непустым `insight_text` и статусом `"pending_delivery"`, **And** не шлет placeholder, empty или weak-content message. [Source: epics.md#story-52-AC5]

6. **Given** пользователь получает periodic insight и решает вернуться в продукт, **When** он отвечает на insight message или открывает новый conversation flow, **Then** продукт естественно продолжит continuity-aware interaction (обеспечивается существующим story 2.3 механизмом), **And** delivery message служит мягкой точкой входа. [Source: epics.md#story-52-AC6]

## Tasks / Subtasks

- [x] Добавить `delivery_error` поле в модель `PeriodicInsight` в `backend/app/models.py` (AC: 4)
  - [x] `delivery_error: str | None = Field(default=None, max_length=500)` — по аналогии с `generation_error`

- [x] Создать Alembic migration для нового поля (AC: 4)
  - [x] `uv run alembic revision --autogenerate -m "add_delivery_error_to_periodic_insight"` из `backend/`
  - [x] Проверить сгенерированный migration файл

- [x] Добавить `INSIGHT_DELIVERY_INTERVAL_HOURS: int = 24` в `backend/app/core/config.py` (AC: 3)

- [x] Создать `backend/app/jobs/insight_delivery.py` — delivery logic (AC: 1, 2, 3, 4, 5)
  - [x] `deliver_insights_for_all_users() -> None` — entry point для scheduler; открывает Session(engine); загружает все `PeriodicInsight` WHERE `status = "pending_delivery"` AND `len(insight_text) > 0`; вызывает `deliver_insight(session, insight)` для каждого; логирует delivered/skipped/failed count
  - [x] `deliver_insight(session: Session, insight: PeriodicInsight) -> str` — логика доставки для одного insight; вызывает `_get_chat_id_for_user(session, insight.telegram_user_id)` — если `chat_id` не найден → логирует с user_id, возвращает `"skipped"`; вызывает `_send_telegram_message(chat_id, text)` — если успех → обновляет `insight.status = "delivered"`, `insight.updated_at`; если исключение → логирует ошибку, обновляет `insight.delivery_error = str(exc)[:500]`, `insight.status = "delivery_failed"`, возвращает `"failed"`; **никогда не логирует insight_text content** — только `insight.id` и `telegram_user_id`
  - [x] `_get_chat_id_for_user(session: Session, telegram_user_id: int) -> int | None` — выбирает последний `chat_id` из `TelegramSession` по `telegram_user_id`, сортировка по `updated_at DESC` LIMIT 1; возвращает `None` если нет сессий
  - [x] `_send_telegram_message(chat_id: int, text: str) -> None` — делает HTTP POST запрос к `https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage` через **`httpx.post()` (sync)**; payload: `{"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}`; если response статус не 2xx → поднимает `RuntimeError(f"Telegram API error: {status_code} {response_body[:200]}")`; если `settings.TELEGRAM_BOT_TOKEN is None` → поднимает `RuntimeError("TELEGRAM_BOT_TOKEN not configured")`; timeout=10 секунд

- [x] Зарегистрировать новый scheduler job в `backend/app/jobs/scheduler.py` (AC: 3)
  - [x] Импортировать `deliver_insights_for_all_users` из `app.jobs.insight_delivery`
  - [x] Добавить job в `start_scheduler()`:
    ```python
    scheduler.add_job(
        deliver_insights_for_all_users,
        IntervalTrigger(hours=settings.INSIGHT_DELIVERY_INTERVAL_HOURS),
        id="insight_delivery",
        replace_existing=True,
    )
    ```

- [x] Создать `backend/tests/jobs/test_insight_delivery.py` (AC: 1, 3, 4, 5)
  - [x] Fixture `clear_delivery_tables` — аналог `clear_insight_tables` из story 5.1
  - [x] Test: `pending_delivery` insight + существующая TelegramSession → delivery вызывает Telegram API, статус становится `"delivered"` (mock `_send_telegram_message`)
  - [x] Test: нет `chat_id` для пользователя → функция не вызывает API, результат `"skipped"`
  - [x] Test: Telegram API возвращает ошибку → `insight.status = "delivery_failed"`, `delivery_error` не пустой
  - [x] Test: insight с `status != "pending_delivery"` не подбирается для доставки (уже delivered → не обрабатывается)
  - [x] Test: insight с пустым `insight_text` пропускается (не доставляется)

- [x] Запустить проверки (AC: все)
  - [x] `uv run alembic upgrade heads` из `backend/`
  - [x] `uv run pytest tests/ -q` из `backend/`
  - [x] `uv run ruff check --fix app tests` из `backend/`
  - [x] `uv run mypy app tests`

## Dev Notes

### Ключевой архитектурный паттерн для проактивной доставки

**КРИТИЧНО**: Текущий bot flow — webhook-driven (входящие сообщения через `/telegram/webhook`). Для story 5.2 нужен обратный путь: backend → Telegram Bot API. Это **не** webhook response — это прямой HTTP call из scheduler job.

**Правильный подход**: использовать `httpx.post()` (sync, уже установлен в проекте) для вызова `https://api.telegram.org/bot{TOKEN}/sendMessage`. **НЕ** использовать `python-telegram-bot` async API из sync scheduler — это приведет к event loop конфликтам.

### Telegram API

```python
# Пример вызова из insight_delivery.py
import httpx
from app.core.config import settings

def _send_telegram_message(chat_id: int, text: str) -> None:
    if settings.TELEGRAM_BOT_TOKEN is None:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not configured")
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    response = httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=10.0)
    if not response.is_success:
        raise RuntimeError(f"Telegram API error: {response.status_code} {response.text[:200]}")
```

### chat_id lookup паттерн

`TelegramSession` хранит `chat_id` (колонка `BigInteger`, indexed). Пользователь может иметь несколько сессий с одним и тем же `chat_id` (для DM — chat_id == telegram_user_id в большинстве случаев, но лучше брать актуальный из БД).

```python
from sqlmodel import Session, select
from app.models import TelegramSession

def _get_chat_id_for_user(session: Session, telegram_user_id: int) -> int | None:
    ts = session.exec(
        select(TelegramSession)
        .where(TelegramSession.telegram_user_id == telegram_user_id)
        .order_by(TelegramSession.updated_at.desc())
        .limit(1)
    ).first()
    return ts.chat_id if ts is not None else None
```

### Паттерн Session в scheduler jobs

По аналогии с `weekly_insights.py` — использовать `Session(engine)` напрямую (не через FastAPI dependency injection):

```python
from app.core.db import engine
from sqlmodel import Session, select

with Session(engine) as session:
    insights = session.exec(select(PeriodicInsight).where(...)).all()
    for insight in insights:
        # ... процессинг
        session.add(insight)
        session.commit()
```

### Тон delivery message

- Insight text (сгенерированный в story 5.1) уже calm, low-pressure, на русском
- Доставлять insight_text напрямую — **без добавления extra CTA wrapper**
- НЕ добавлять: восклицательные знаки, призывы "вернись к нам", agressive re-engagement copy
- AC2: message должно feel like reflective support, не как notification blast

### Observability паттерн

По аналогии с `_deliver_to_ops_inbox` в `ops/alerts.py` — логировать только `insight.id` и `telegram_user_id`, **не логировать insight_text** (содержит приватный контекст пользователя):

```python
logger.exception(
    "Failed to deliver insight id=%s for telegram_user_id=%s",
    insight.id,
    insight.telegram_user_id
)
```

### Что НЕ делать (anti-patterns)

- ❌ Не использовать `asyncio.run()` с `python-telegram-bot` async API из sync scheduler job
- ❌ Не доставлять insights с `status != "pending_delivery"` (уже delivered, failed, skipped)
- ❌ Не логировать содержимое `insight_text` в любых логах
- ❌ Не пытаться повторно доставить если Telegram вернул 403 (бот заблокирован) — устанавливать `delivery_failed`
- ❌ Не создавать новый `PeriodicInsight` запись при ошибке доставки — обновлять существующую

### Связь с Story 5.1 (что уже сделано)

- `PeriodicInsight` таблица создана: `backend/app/alembic/versions/a6dbabfa957b_add_periodic_insight_table.py`
- `generate_insights_for_all_users()` запускается по расписанию и создает записи со `status="pending_delivery"`
- Scheduler стартует в `backend/app/main.py` через FastAPI lifespan
- Тесты generation: `backend/tests/jobs/test_insight_generation.py`
- Job scheduler setup: `backend/app/jobs/scheduler.py` — нужно добавить второй job

### Project Structure Notes

- Новый файл: `backend/app/jobs/insight_delivery.py` (по аналогии с `backend/app/jobs/weekly_insights.py`)
- Новые тесты: `backend/tests/jobs/test_insight_delivery.py`
- Migration: `backend/app/alembic/versions/` — новый файл через autogenerate
- Изменения в существующих файлах: `models.py`, `config.py`, `scheduler.py`

### References

- [Source: epics.md#Epic-5-Story-5.2] — полные acceptance criteria
- [Source: architecture.md#Async-Boundary] — in-process scheduling acceptable for secondary periodic jobs
- [Source: architecture.md#Adapter-Boundaries] — Telegram adapter как delivery layer
- [Source: architecture.md#Recommended-Initialization-Commands] — `httpx` в dependencies
- [Source: backend/app/jobs/weekly_insights.py] — паттерн синхронных jobs с Session(engine)
- [Source: backend/app/jobs/scheduler.py] — паттерн добавления jobs в BackgroundScheduler
- [Source: backend/app/models.py#PeriodicInsight] — модель, статусы: pending_delivery, delivered, skipped, failed
- [Source: backend/app/core/config.py] — `TELEGRAM_BOT_TOKEN`, `INSIGHT_GENERATION_INTERVAL_DAYS`
- [Source: backend/app/ops/alerts.py] — паттерн observability для delivery failures
- [Source: backend/tests/jobs/test_insight_generation.py] — паттерн тестов для jobs

## Dev Agent Record

### Agent Model Used

gemini-2.0-pro-exp-02-05

### Debug Log References

### Completion Notes List

- Added `delivery_error` field to `PeriodicInsight` model in `app/models.py`.
- Generated and applied Alembic migration for the new field.
- Added `INSIGHT_DELIVERY_INTERVAL_HOURS` to `app/core/config.py`.
- Implemented `deliver_insights_for_all_users` logic in `app/jobs/insight_delivery.py` using `httpx` for proactive Telegram API calls.
- Registered the delivery job in the background scheduler in `app/jobs/scheduler.py`.
- Created comprehensive tests in `tests/jobs/test_insight_delivery.py` covering success, missing chat_id, and API error scenarios.
- Verified all 277 backend tests pass.

### File List

- `backend/app/models.py`
- `backend/app/core/config.py`
- `backend/app/jobs/insight_delivery.py`
- `backend/app/jobs/scheduler.py`
- `backend/tests/jobs/test_insight_delivery.py`
