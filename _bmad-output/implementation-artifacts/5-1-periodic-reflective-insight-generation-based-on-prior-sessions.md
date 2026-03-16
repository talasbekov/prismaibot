# Story 5.1: Генерация periodic reflective insight на основе prior sessions

Status: done

## Story

As a returning user,
I want чтобы продукт мог формировать периодический reflective insight на основе прошлых сессий и накопленного контекста,
So that я получаю дополнительную ценность даже вне острого момента и лучше вижу повторяющиеся паттерны.

## Acceptance Criteria

1. **Given** у пользователя есть достаточный continuity context from prior sessions, **When** система запускает periodic insight generation, **Then** продукт формирует reflective insight на основе prior summaries and retained context, **And** результат не выглядит как generic, one-size-fits-all content blast. [Source: epics.md#story-51-AC1]

2. **Given** insight строится на historical continuity data, **When** система генерирует insight content, **Then** текст отражает релевантные patterns, shifts or recurring themes from the user's prior sessions, **And** не выдумывает глубокие выводы, если накопленного материала недостаточно. [Source: epics.md#story-51-AC2]

3. **Given** accumulated context слабый, слишком редкий или низкого качества для meaningful insight, **When** periodic generation запускается, **Then** система может не генерировать full reflective insight или выдать более conservative version, **And** не создает фальшивую персонализацию на слабой evidence base. [Source: epics.md#story-51-AC3]

4. **Given** weekly/periodic insight не должен ломать trust модели продукта, **When** insight подготавливается для пользователя, **Then** language остается calm, reflective and low-pressure, **And** не превращается в manipulative retention copy или productivity-nag messaging. [Source: epics.md#story-51-AC4]

5. **Given** periodic insight generation выполняется вне основного user conversation path, **When** background generation starts or completes, **Then** этот процесс использует scheduler/job seam and asynchronous processing model, **And** не влияет на latency active conversational sessions. [Source: epics.md#story-51-AC5]

6. **Given** insight generation завершилась ошибкой или не смогла опереться на reliable continuity data, **When** система не может получить quality result, **Then** failure становится observable, **And** продукт предпочитает не сохранять слабый или misleading insight — generation skips silently if insufficient evidence. [Source: epics.md#story-51-AC6]

## Tasks / Subtasks

- [x] Создать `backend/app/jobs/` модуль (AC: 5)
  - [x] `backend/app/jobs/__init__.py` — пустой
  - [x] `backend/app/jobs/scheduler.py` — APScheduler 3.x `BackgroundScheduler` setup; `start_scheduler()` и `stop_scheduler()` функции; зарегистрировать `generate_insights_for_all_users` как IntervalTrigger job (interval=7 days по умолчанию, настраивается через env)

- [x] Добавить модель `PeriodicInsight` в `backend/app/models.py` (AC: 1, 3)
  - [x] Таблица `periodic_insight`: `id` (uuid PK), `telegram_user_id` (BigInteger, indexed), `insight_text` (str, max_length=1500), `basis_summary_count` (int), `status` ("pending_delivery" | "delivered" | "skipped"), `generation_error` (str | None, max_length=500), `created_at`, `updated_at`
  - [x] `UniqueConstraint` не нужен (пользователь может получать insight периодически, каждый раз новая запись)

- [x] Создать alembic migration для `periodic_insight` таблицы
  - [x] `uv run alembic revision --autogenerate -m "add_periodic_insight_table"` из `backend/`
  - [x] Проверить сгенерированный migration файл перед применением

- [x] Создать `backend/app/jobs/weekly_insights.py` — insight generation logic (AC: 1, 2, 3, 4, 5, 6)
  - [x] `generate_insights_for_all_users()` — entry point для scheduler; читает всех уникальных `telegram_user_id` из `session_summary` таблицы; вызывает `generate_insight_for_user()` для каждого; логирует общее количество processed/skipped/failed
  - [x] `generate_insight_for_user(telegram_user_id: int) -> None` — основная логика генерации для одного пользователя; использует `Session(engine)` как в `memory/service.py`; вызывает `memory.service.get_continuity_overview()` для получения summaries и profile_facts; применяет `_should_generate_insight()` gate; строит insight text через `_build_insight_text()`; сохраняет `PeriodicInsight` запись; при ошибке — логирует с `telegram_user_id` без session content
  - [x] `_should_generate_insight(overview: ContinuityOverview) -> bool` — возвращает False если summaries < 2 (недостаточный контекст); возвращает False если все summaries имеют `retention_scope != "durable_summary"`; иначе True
  - [x] `_build_insight_text(overview: ContinuityOverview) -> str` — строит calm, low-pressure текст на основе `key_facts`, `emotional_tensions`, `uncertainty_notes` из summaries и `fact_value` из durable_profile facts; НЕ использует raw transcript; применяет те же паттерны что и `memory/service.py` (marker-based extraction); максимум 1500 символов; русский язык, calm tone, без восклицаний
  - [x] Failure observability: при исключении в `generate_insight_for_user` — `logger.exception("Failed to generate insight for telegram_user_id=%s", telegram_user_id)` (только ID, не content)

- [x] Интегрировать scheduler в `backend/app/main.py` (AC: 5)
  - [x] Использовать FastAPI lifespan context manager (не deprecated `on_event`)
  - [x] `startup`: вызвать `jobs.scheduler.start_scheduler()`
  - [x] `shutdown`: вызвать `jobs.scheduler.stop_scheduler()`

- [x] Создать `backend/tests/jobs/` и `backend/tests/jobs/test_insight_generation.py` (AC: 1, 2, 3, 4, 6)
  - [x] `__init__.py` для папки
  - [x] Fixture `clear_insight_tables` — чистит `periodic_insight`, `session_summary`, `profile_fact`, `telegram_session` между тестами
  - [x] Test: пользователь с 2+ summaries → `generate_insight_for_user()` → `PeriodicInsight` запись создана, `status="pending_delivery"`, `basis_summary_count >= 2`, `insight_text` не пустой
  - [x] Test: пользователь с 0 summaries → функция завершается без создания `PeriodicInsight` записи (skip path)
  - [x] Test: пользователь с 1 summary → та же skip path (insufficient context)
  - [x] Test: insight text не содержит raw user messages (не попадает прямой `last_user_message` контент — только derived facts)
  - [x] Test: insight text ≤ 1500 символов

- [x] Запустить проверки (AC: все)
  - [x] `uv run alembic upgrade heads` из `backend/`
  - [x] `uv run pytest tests/ -q` из `backend/`
  - [x] `uv run ruff check --fix app tests` из `backend/`
  - [x] `uv run mypy app tests`

## Dev Agent Record

### Agent Model Used

gemini-2.0-pro-exp-02-05

### Debug Log References

### Completion Notes List

- Added `PeriodicInsight` model to `app/models.py`.
- Fixed Alembic configuration to include all models in metadata (updated `env.py`).
- Resolved Alembic head conflict by merging multiple heads.
- Implemented `jobs` module with `scheduler.py` and `weekly_insights.py`.
- Integrated background job scheduling into FastAPI using the `lifespan` context manager.
- Added comprehensive tests for periodic insight generation.
- Verified all 268 backend tests pass.

### File List

- `backend/app/models.py`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/alembic/env.py`
- `backend/app/jobs/__init__.py`
- `backend/app/jobs/scheduler.py`
- `backend/app/jobs/weekly_insights.py`
- `backend/tests/jobs/__init__.py`
- `backend/tests/jobs/test_insight_generation.py`
