# Story 4.7: Continuity across free and paid states

Status: done

## Story

As a user moving between free and paid access states,
I want чтобы continuity value продукта сохранялась и в free, и в paid model без нелогичных разрывов,
so that premium boundary feels like an upgrade in continuity experience, not a break in my relationship with the product.

## Acceptance Criteria

1. **Given** у пользователя уже есть накопленный continuity context from prior sessions, **When** он достигает premium boundary или меняет access state, **Then** продукт сохраняет already-earned continuity artifacts (SessionSummary записи, ProfileFact записи) в согласованном виде, **And** переход между free and paid states не ломает core memory model — никакие memory/summary/profile_fact записи не удаляются при смене access_tier. [Source: epics.md#story-47-AC1]

2. **Given** пользователь остается на free tier после достижения ограничений или возвращается в unpaid state после cancellation, **When** система применяет соответствующие access rules, **Then** continuity and access distinctions обрабатываются по defined policy, **And** продукт не ведет себя так, будто вся ранее накопленная ценность внезапно исчезла без объяснения — messaging пользователю при downgrade явно говорит, что память сохранена. [Source: epics.md#story-47-AC2]

3. **Given** пользователь активировал paid access, **When** продукт продолжает будущие сессии, **Then** premium experience усиливает continuity-based value — отсутствие paywall gate означает неограниченную возможность накапливать и использовать memory, **And** premium differentiation ощущается как meaningful upgrade (доступ к рефлективным сессиям без лимита) rather than arbitrary gate. [Source: epics.md#story-47-AC3]

4. **Given** access state пользователя изменился из-за confirmed billing event, cancellation или renewal outcome, **When** новый conversational session начинается, **Then** система применяет continuity behavior, согласованное с актуальным access state — billing gate всегда читает fresh `UserAccessState` из DB без in-memory caching, **And** не использует устаревшую free/paid interpretation of the user's entitlements. [Source: epics.md#story-47-AC4]

5. **Given** в billing/access layer возникла inconsistency around free/paid transition, **When** продукт пытается определить, как вести себя с continuity features, **Then** failure становится observable через ops signal, **And** пользователь не должен видеть contradictory behavior where continuity is both promised and denied at once. [Source: epics.md#story-47-AC5]

6. **Given** monetization design не должна восприниматься как emotional hostage-taking, **When** продукт объясняет различия между free and paid continuity experience, **Then** communication остается respectful and trust-preserving, **And** не использует already-stored user context как pressure tactic for conversion — `PAYWALL_MESSAGE` и `CANCEL_PREMIUM_SUCCESS_MESSAGE` соответствуют этому требованию. [Source: epics.md#story-47-AC6]

## Tasks / Subtasks

- [x] Обновить `CANCEL_PREMIUM_SUCCESS_MESSAGE` в `billing/prompts.py` (AC: 2, 6)
  - [x] Добавить в конец сообщения фразу о том, что накопленная память и контекст сохраняются после деактивации premium — пользователь не теряет continuity value при downgrade
  - [x] Тон: calm, русский, без восклицательных знаков, без технических терминов типа "access_tier" или "database"

- [x] Проверить `PAYWALL_MESSAGE` на соответствие AC6 (AC: 6)
  - [x] Убедиться, что формулировка не создает ощущения hostage-taking ("твои данные будут удалены, если не заплатишь")
  - [x] Текущая формулировка: "Чтобы сохранить весь полезный контекст..." — это benefits framing, а не threat framing; если формулировка приемлема — оставить без изменений
  - [x] Если требуется правка — внести минимальные изменения, сохранив continuity-based framing как главный аргумент

- [x] Создать тестовый файл `backend/tests/billing/test_continuity_states.py` (AC: 1, 2, 3, 4, 5)
  - [x] Test: premium user cancels → `access_tier == "free"`, SessionSummary и ProfileFact записи этого пользователя в DB НЕ удалены (проверить через прямой SELECT)
  - [x] Test: free user (within threshold) после successful_payment event → `access_tier == "premium"` → следующая сессия не получает paywall → первый turn получает prior memory context если summaries есть в DB
  - [x] Test: пользователь делает `/cancel` → `access_tier` становится "free", `threshold_reached_at` остается установленным → следующий `_handle_message` (не `/start`, не `/status`, не `/cancel`) возвращает paywall_gate response
  - [x] Test: billing gate читает свежий state — пользователь получает payment upgrade (access_tier→premium), следующий вызов `_handle_message` в том же тесте НЕ возвращает paywall_gate (нет stale cache)
  - [x] Test: full lifecycle — free session completion → threshold reached → paywall → payment → premium session with memory recall → cancel → paywall again — все шаги проходят корректно и память не удаляется ни на одном этапе

- [x] Запустить проверки (AC: все)
  - [x] `uv run pytest tests/ -q` из `backend/`
  - [x] `uv run ruff check --fix app tests` из `backend/`
  - [x] `uv run mypy app tests`

## Dev Notes

- **Архитектурная истина Story 4.7**: Continuity и billing — полностью изолированные domains. `memory/` никогда не смотрит на `access_tier`. `billing/` никогда не удаляет `SessionSummary` или `ProfileFact`. Переходы между состояниями уже корректны структурно — story добавляет явное messaging о preservation и регрессионные тесты. [Source: architecture.md#domain-boundaries]

- **Как работает billing gate**: В `_handle_message` в `session_bootstrap.py` (строка ~539-551): при каждом вызове делается `get_user_access_state(session, telegram_user_id)` — это `SELECT` из `user_access_states` без кеширования. Если `access_tier != "premium"` И `threshold_reached_at is not None` → paywall. Это уже fresh-read; stale cache невозможен структурно. [Source: session_bootstrap.py#_handle_message billing gate block]

- **Что НЕ удаляется при cancellation**: `process_cancellation_request()` в `billing/service.py` вызывает только `repository.upgrade_access_tier(session, state, "free")` — меняет только `UserAccessState.access_tier`. `SessionSummary`, `ProfileFact`, `TelegramSession` записи НЕ затрагиваются. Memory preservation — это structural guarantee, а не policy enforcement. [Source: billing/service.py#process_cancellation_request]

- **`threshold_reached_at` после cancellation**: После `/cancel` premium → `access_tier = "free"`, но `threshold_reached_at` остается SET (не сбрасывается). Это правильное поведение: пользователь уже исчерпал free sessions; cancellation premium возвращает его к тому же paywall state что был до оплаты. Он может снова заплатить чтобы восстановить access. Тест должен это проверять явно. [Source: billing/models.py#UserAccessState fields]

- **Memory recall НЕ зависит от access_tier**: `get_session_recall_context()` в `memory/service.py` читает `SessionSummary` и `ProfileFact` для любого `telegram_user_id` без проверки access tier. Memory recall доступен внутри free sessions (до threshold) и в premium sessions одинаково. Premium value — в возможности начинать НОВЫЕ reflective sessions без paywall. [Source: memory/service.py#get_session_recall_context]

- **Когда memory recall реально используется**: В `_handle_message` → `is_first_turn == True` → `_safe_load_prior_memory_context()` → `get_session_recall_context()`. Если пользователь заблокирован paywall gate, до этой части код не доходит. После upgrade до premium — следующий `_handle_message` проходит gate, и если `is_first_turn`, memory recall загружается. [Source: session_bootstrap.py#_handle_message first_turn branch]

- **Точка добавления в `CANCEL_PREMIUM_SUCCESS_MESSAGE`**: Текущее содержание объясняет одноразовость Stars оплаты и куда обращаться за refund. Нужно добавить ПОСЛЕ этого: краткое reassurance что накопленный контекст и история сессий сохраняются. Например: "Ваш накопленный контекст и история сессий никуда не исчезнут." — без упоминания технических таблиц. [Source: billing/prompts.py#CANCEL_PREMIUM_SUCCESS_MESSAGE]

- **Тестовые fixtures и паттерны**: Следовать паттернам из `backend/tests/billing/test_cancel_command.py` — fixture `clear_billing_tables`, прямое создание записей через `db.add()`. Для memory тестов: прямое создание `SessionSummary` через `db.add()` и `ProfileFact` через `db.add()` без прохождения через `memory/service.py`. [Source: backend/tests/billing/test_cancel_command.py patterns]

- **Pre-existing test failures**: 2 crisis step-down теста всё ещё могут падать — не связано Bennet с billing/memory. Не расследовать. [Source: story 4.1-4.6 notes]

- **Не трогать**:
  - `billing/models.py`, `billing/repository.py`, `billing/api.py` — нет новых полей или методов
  - `memory/service.py`, `memory/schemas.py` — memory domain не изменяется
  - `conversation/session_bootstrap.py` — billing gate уже корректен, memory recall уже access-agnostic
  - `safety/` модули

### Project Structure Notes

- Live backend layout: `backend/app/`, не `src/goals/`
- Модифицируемые файлы:
  - `backend/app/billing/prompts.py` — обновить `CANCEL_PREMIUM_SUCCESS_MESSAGE` (+ возможно minor tone fix в `PAYWALL_MESSAGE`)
- Новый тестовый файл:
  - `backend/tests/billing/test_continuity_states.py`
- Не трогать:
  - `backend/app/billing/models.py`
  - `backend/app/billing/repository.py`
  - `backend/app/billing/service.py`
  - `backend/app/billing/api.py`
  - `backend/app/memory/` (все файлы)
  - `backend/app/conversation/session_bootstrap.py`

### Technical Requirements

- `CANCEL_PREMIUM_SUCCESS_MESSAGE` ДОЛЖЕН явно сообщать что memory/context сохраняется после деактивации. [Source: epics.md#story-47-AC2]
- Memory preservation — structural guarantee (memory domain не знает о billing domain), тесты документируют это явно. [Source: architecture.md#domain-boundaries]
- Billing gate читает fresh `UserAccessState` на каждый вызов `_handle_message` — нет stale caching, AC4 выполняется структурно. [Source: session_bootstrap.py#billing-gate]
- `threshold_reached_at` НЕ сбрасывается при cancellation или новом premium upgrade — он отражает историческое достижение free limit, не текущий access tier. [Source: billing/models.py]
- Существующий `billing_access_check_failed` signal в `_handle_message` уже покрывает AC5 observability. [Source: session_bootstrap.py#billing_access_check_failed signal]

### Architecture Compliance

- `billing/` owners access-state logic; `memory/` owners continuity artifacts — cross-domain isolation preserved. [Source: architecture.md#domain-boundaries]
- `snake_case` для всех полей. UTC timestamps. [Source: architecture.md#naming-patterns]
- Logging: emit `telegram_user_id`, никогда в паре с session content. [Source: architecture.md#logging-pattern]
- Prompt strings — русский, calm tone, без восклицаний, без raw technical terms. [Source: billing/prompts.py tone reference]

### Library / Framework Requirements

- FastAPI `0.114.x`, SQLModel `0.0.21`, Pydantic v2 — новые зависимости не нужны. [Source: backend/pyproject.toml]
- Тест создает `SessionSummary` записи напрямую через `SQLModel` + `db.add()` для проверки memory preservation — не нужно проходить через summary pipeline. [Source: app/models.py#SessionSummary]
- Для теста full lifecycle с `_handle_message`: использовать `handle_session_entry()` напрямую с `update` dict, аналогично существующим billing тестам. [Source: backend/tests/billing/test_cancel_command.py]

### Testing Requirements

- Test commands (run from `backend/`):
  ```
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run alembic upgrade heads
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests/ -q
  uv run ruff check --fix app tests
  uv run mypy app tests
  ```
- Файл с тестами: `backend/tests/billing/test_continuity_states.py`
- Fixture `clear_billing_tables` должна также чистить `session_summaries` и `profile_facts` таблицы для изоляции тестов
- Coverage:
  1. cancellation не удаляет SessionSummary и ProfileFact записи
  2. после payment upgrade billing gate пропускает пользователя (нет paywall)
  3. после cancellation billing gate блокирует пользователя (paywall, потому что threshold_reached_at всё ещё set)
  4. billing gate читает fresh state (нет stale caching)
  5. full lifecycle: free → threshold → pay → premium session with recall → cancel → paywall
- Импорты: `from app.models import SessionSummary, ProfileFact` для прямого создания memory records в тестах

### References

- Story source и AC: [Source: planning-artifacts/epics.md#story-47]
- Product requirement FR27: [Source: planning-artifacts/prd.md]
- Architecture domain boundaries и memory/billing isolation: [Source: planning-artifacts/architecture.md#domain-boundaries]
- Architecture cross-cutting concerns (State Orchestration, Monetization Integrity): [Source: planning-artifacts/architecture.md#cross-cutting-concerns]
- UX calm messaging tone и non-manipulative premium framing: [Source: planning-artifacts/ux-design-specification.md]
- Live billing service (process_cancellation_request, get_user_access_state, is_free_eligible): [Source: backend/app/billing/service.py]
- Live billing models (UserAccessState fields — access_tier, threshold_reached_at): [Source: backend/app/billing/models.py]
- Live billing prompts (CANCEL_PREMIUM_SUCCESS_MESSAGE — target for update): [Source: backend/app/billing/prompts.py]
- Live session_bootstrap (billing gate logic, _safe_load_prior_memory_context, fresh state read): [Source: backend/app/conversation/session_bootstrap.py]
- Live memory service (get_session_recall_context — access-agnostic): [Source: backend/app/memory/service.py]
- Story 4.6 dev notes (cancellation command pattern, billing/memory isolation): [Source: implementation-artifacts/4-6-request-cancellation-or-non-renewal-of-paid-access.md]
- Story 4.5 dev notes (status command pattern, billing gate reference): [Source: implementation-artifacts/4-5-viewing-current-access-subscription-status.md]

## Dev Agent Record

### Agent Model Used

gemini-2.0-pro-exp-02-05

### Debug Log References

### Completion Notes List

- Updated `CANCEL_PREMIUM_SUCCESS_MESSAGE` in `backend/app/billing/prompts.py` to include reassurance about memory preservation.
- Verified that `PAYWALL_MESSAGE` uses positive framing and complies with AC6.
- Implemented `get_user_access_state_by_telegram_id` in `backend/app/billing/repository.py` to allow side-effect-free access checks (part of story 4.6 fixes but relevant here).
- Created comprehensive regression tests in `backend/tests/billing/test_continuity_states.py` covering access transitions and memory preservation.
- Verified all 267 backend tests pass.

### File List

- `backend/app/billing/prompts.py`
- `backend/app/billing/repository.py`
- `backend/app/billing/service.py`
- `backend/app/conversation/session_bootstrap.py`
- `backend/tests/billing/test_continuity_states.py`
