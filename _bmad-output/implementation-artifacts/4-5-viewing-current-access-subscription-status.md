# Story 4.5: Просмотр текущего access/subscription status пользователем

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user with free or paid access,
I want видеть мой текущий access or subscription status,
so that я понимаю, доступен ли мне premium и в каком состоянии находится моя подписка или покупка.

## Acceptance Criteria

1. Given у пользователя уже есть определенный access state в системе, When он запрашивает свой current status через `/status` команду, Then продукт показывает актуальный access/subscription state в понятной форме, And сообщение не требует от пользователя интерпретировать внутренние billing codes или технические статусы. [Source: epics.md#story-45]
2. Given пользователь находится в free tier И ещё не исчерпал бесплатный лимит (threshold_reached_at is None), When он смотрит свой статус, Then продукт ясно показывает, что доступ пока бесплатный и активный, And состояние consistent with configured free-usage model. [Source: epics.md#story-45]
3. Given пользователь находится в free tier И уже исчерпал бесплатный лимит (threshold_reached_at is set), When он смотрит статус, Then продукт ясно показывает, что бесплатный лимит использован, And сообщение содержит понятный следующий шаг (inline кнопка "Оформить premium ✦"). [Source: epics.md#story-45, ux-design-specification.md#premium-gate-prompt]
4. Given пользователь имеет активный paid access (access_tier="premium"), When он запрашивает статус, Then продукт показывает, что premium currently active, And status messaging не противоречит последним confirmed billing events. [Source: epics.md#story-45]
5. Given access/subscription state не может быть надежно загружен (DB error), When пользователь запрашивает статус, Then продукт сообщает о проблеме спокойно и понятно, And failure становится observable для system/operator via ops signal, And не изобретается ложный статус. [Source: epics.md#story-45, architecture.md#operational-signal-expectations]
6. Given conversation layer использует `UserAccessState.access_tier` и `threshold_reached_at` для monetization decisions, When status показывается пользователю, Then displayed state отражает те же поля из той же записи, что и paywall gate (AC: 1, 2, 3, 4 — нет расхождения между статусом и реальным поведением). [Source: epics.md#story-45, session_bootstrap.py#billing-gate]

## Tasks / Subtasks

- [x] Добавить status prompt strings в `billing/prompts.py` (AC: 1, 2, 3, 4)
  - [x] `STATUS_FREE_ACTIVE_MESSAGE: str` — Russian, calm: "Ваш доступ — бесплатный. Вы ещё в пределах бесплатного лимита."
  - [x] `STATUS_FREE_THRESHOLD_REACHED_MESSAGE: str` — Russian, calm, с указанием next step: "Бесплатный лимит использован. Оформите premium, чтобы продолжить с сохранённым контекстом."
  - [x] `STATUS_PREMIUM_MESSAGE: str` — Russian, calm: "У вас активен premium доступ. Контекст и память сохраняются между сессиями."
  - [x] `STATUS_ERROR_MESSAGE: str` — Russian, calm: "Не удалось загрузить статус доступа. Попробуйте ещё раз через минуту."

- [x] Добавить `build_status_response()` в `billing/service.py` (AC: 2, 3, 4)
  - [x] Сигнатура: `build_status_response(user_access_state: UserAccessState) -> tuple[str, list[list[InlineButton]]]`
  - [x] Если `access_tier == "premium"` → return `(STATUS_PREMIUM_MESSAGE, [])`
  - [x] Если `threshold_reached_at is None` (free, ещё eligible) → return `(STATUS_FREE_ACTIVE_MESSAGE, [])`
  - [x] Иначе (free, threshold reached) → return `(STATUS_FREE_THRESHOLD_REACHED_MESSAGE, [[InlineButton(text="Оформить premium ✦", callback_data="pay:stars")]])`
  - [x] Логика определения состояния ДОЛЖНА использовать те же поля, что и paywall gate в `session_bootstrap.py` (`access_tier` и `threshold_reached_at`) — AC 6 гарантирован структурно

- [x] Добавить routing `/status` и `_handle_status_command()` в `session_bootstrap.py` (AC: 1, 2, 3, 4, 5)
  - [x] Импортировать `build_status_response` и новые prompt constants из `billing/prompts.py`
  - [x] В `handle_session_entry`, ПОСЛЕ проверки `/start` и ПЕРЕД вызовом `_handle_message`, добавить:
    ```python
    if message.text.strip() == "/status":
        return _handle_status_command(session, message.telegram_user_id, message.chat_id)
    ```
  - [x] Добавить `_handle_status_command(session: Session, telegram_user_id: int, chat_id: int) -> TelegramWebhookResponse`:
    - Вызвать `get_user_access_state(session, telegram_user_id)` (get_or_create — новый пользователь получает "free active")
    - Вызвать `build_status_response(state)` → `(text, inline_keyboard)`
    - Return `TelegramWebhookResponse(status="ok", action="status_shown", handled=True, messages=[TelegramMessageOut(text=text)], inline_keyboard=inline_keyboard)`
    - On exception: log, rollback, попытаться записать `_get_or_create_active_session(session, telegram_user_id, chat_id)` + `record_retryable_signal(..., signal_type="billing_status_check_failed", ...)`, return error message response

- [x] Написать тесты (AC: 1, 2, 3, 4, 5, 6)
  - [x] Создать `backend/tests/billing/test_status_command.py`
  - [x] Test: новый пользователь без DB record (auto-created) отправляет `/status` → `action="status_shown"`, текст = `STATUS_FREE_ACTIVE_MESSAGE`
  - [x] Test: free user с `threshold_reached_at=None` → `action="status_shown"`, текст = `STATUS_FREE_ACTIVE_MESSAGE`, нет inline кнопок
  - [x] Test: free user с `threshold_reached_at` set → текст = `STATUS_FREE_THRESHOLD_REACHED_MESSAGE`, inline кнопка `callback_data="pay:stars"` присутствует
  - [x] Test: premium user (`access_tier="premium"`) → текст = `STATUS_PREMIUM_MESSAGE`, нет inline кнопок
  - [x] Test: DB error при загрузке access state → `action="status_error"`, текст = `STATUS_ERROR_MESSAGE`, obs signal `"billing_status_check_failed"` записан
  - [x] Test: consistency — status для premium user отображает premium (AC 6: тот же `access_tier` что и в paywall gate)
  - [x] Test: status для free user с threshold — та же запись, что блокирует `_handle_message` (regression guard: paywall gate блокирует, `/status` показывает threshold reached)
  - [x] Запустить `pytest`, `ruff check --fix`, `mypy` из `backend/`

## Dev Notes

- **`/status` — это Telegram команда, не reflective flow**: Обрабатывается до `_handle_message`, аналогично `/start`. Нет создания `TelegramSession`, нет billing gate, нет safety check. Просто load state → show status.
- **Точка вставки в `handle_session_entry`**: Текущая структура после Story 4.4:
  1. `pre_checkout_query` check
  2. `successful_payment` check
  3. `callback_query` check (pay:stars, mode selection)
  4. `_parse_message` → если `/start` → `_build_opening_prompt()`
  5. `_handle_message`

  Добавить `/status` ПОСЛЕ `/start` check, ПЕРЕД `_handle_message`:
  ```python
  if message.text.strip() == "/start":
      return _build_opening_prompt()

  if message.text.strip() == "/status":
      return _handle_status_command(session, message.telegram_user_id, message.chat_id)
  ```
- **`get_user_access_state` уже создает запись если нет**: Использовать существующую `get_user_access_state(session, telegram_user_id)` из `app.billing.service` — она вызывает `get_or_create_user_access_state()` из репозитория. Новый пользователь без записи получит fresh "free" state с `threshold_reached_at=None`. Это корректно — правильный статус "free active". **Не создавать новую функцию в репозитории — существующая достаточна.**
- **`build_status_response` логика зеркалит paywall gate**: Paywall gate в `session_bootstrap.py` (lines ~405-417) проверяет: `if _user_access_state.access_tier != "premium" and not is_free_eligible(_user_access_state)`. `is_free_eligible` возвращает `threshold_reached_at is None`. `build_status_response()` должна использовать ту же логику ветвления:
  1. `access_tier == "premium"` → STATUS_PREMIUM_MESSAGE
  2. `threshold_reached_at is None` → STATUS_FREE_ACTIVE_MESSAGE
  3. иначе → STATUS_FREE_THRESHOLD_REACHED_MESSAGE + paywall button
  Это структурно гарантирует AC 6 (нет расхождения между статусом и поведением).
- **`InlineButton` импорт в `billing/service.py`**: Уже существует `TYPE_CHECKING` блок с `from app.conversation.session_bootstrap import InlineButton`. `build_status_response` использует тот же паттерн что и `build_paywall_response` — lazy import внутри функции: `from app.conversation.session_bootstrap import InlineButton`. Следовать существующему паттерну в `service.py`.
- **Error handling в `_handle_status_command`**: При DB ошибке — нужен `chat_id` для `_get_or_create_active_session`. Именно поэтому сигнатура принимает `chat_id`. Паттерн сигнала аналогичен Story 4.3 (`_handle_payment_initiation`) — get or create session, flush, record signal. Signal type: `"billing_status_check_failed"`.
- **Не создавать новый маршрут**: `/status` обрабатывается через существующий Telegram webhook flow, не через новый FastAPI endpoint. Не трогать `billing/api.py`.
- **Tone и язык**: Все prompt strings — русский, calm, без восклицательных знаков, без технических кодов, короткие. Следовать тону `PAYMENT_SUCCESS_MESSAGE` и `PAYWALL_MESSAGE` в `billing/prompts.py`.
- **2 pre-existing test failures**: Crisis step-down тесты уже падали до Story 4.1 — не связано с billing. Не расследовать. [Source: 4-1, 4-2, 4-3, 4-4 story notes]
- **mypy**: Ожидаем `# type: ignore[call-overload]` только для `BigInteger` в models. В этой истории нет новых models, поэтому новых type: ignore не должно быть.
- **`python-telegram-bot` 21.x установлен но НЕ используется**: Не импортировать `python-telegram-bot` в `session_bootstrap.py` или `billing/service.py`. [Source: Story 4.3 dev notes]

### Project Structure Notes

- Live backend layout: `backend/app/`, не `src/goals/`
- Новые файлы НЕ нужны в billing module — только модификации существующих
- Модифицируемые файлы:
  - `backend/app/billing/prompts.py` — добавить 4 новых prompt constants
  - `backend/app/billing/service.py` — добавить `build_status_response()`
  - `backend/app/conversation/session_bootstrap.py` — добавить routing `/status` + `_handle_status_command()`
- Новый тестовый файл:
  - `backend/tests/billing/test_status_command.py`
- Не трогать:
  - `backend/app/billing/api.py` — webhook stub для будущей ЮКасса, не используется
  - `backend/app/billing/models.py` — все нужные поля уже есть
  - `backend/app/billing/repository.py` — `get_or_create_user_access_state` уже есть, нового репозиторного метода не нужно
  - `backend/app/core/config.py` — новые settings не нужны
  - Любые `memory/`, `safety/` модули

### Technical Requirements

- Status command должна читать из той же DB записи (`UserAccessState`) что и paywall gate — AC 6. [Source: epics.md#story-45, session_bootstrap.py#billing-gate]
- Failure должен быть observable (ops signal) и user-visible (calm message). [Source: architecture.md#operational-signal-expectations]
- Status response не должна создавать `TelegramSession` — это не reflective session, это информационная команда. [Source: session_bootstrap.py#_build_opening_prompt pattern]
- `billing/service.py` остается owner логики определения статуса; `session_bootstrap.py` является только вызывающей стороной. [Source: architecture.md#domain-boundaries]

### Architecture Compliance

- `billing/` owns payment state и premium access logic — `build_status_response()` идет в `service.py`. [Source: architecture.md#domain-boundaries]
- `conversation/session_bootstrap.py` вызывает billing service functions и переводит Telegram context. [Source: architecture.md#domain-boundaries]
- `snake_case` для всех полей, signal types. UTC timestamps. [Source: architecture.md#naming-patterns]
- Logging: emit `telegram_user_id` для ops tracing, никогда не в паре с conversation content. [Source: architecture.md#logging-pattern]
- Event names как domain facts: `"billing_status_check_failed"`. [Source: architecture.md#async-internal-event-naming]

### Library / Framework Requirements

- FastAPI `0.114.x`, SQLModel `0.0.21`, Pydantic v2 — новые зависимости не нужны. [Source: backend/pyproject.toml]
- Использовать `get_user_access_state` из `app.billing.service`. [Source: billing/service.py]
- Использовать `record_retryable_signal` из `app.ops.signals` для error observability. [Source: backend/app/ops/signals.py]
- Использовать `_get_or_create_active_session` из `session_bootstrap.py` в error path (уже доступна как module-level function). [Source: session_bootstrap.py]

### Testing Requirements

- Test commands (run from `backend/`):
  ```
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run alembic upgrade heads
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests/ -q
  uv run ruff check --fix app tests
  uv run mypy app tests
  ```
- Coverage: новый пользователь (auto-created free), free ниже threshold, free выше threshold + paywall button, premium, DB error + signal, consistency с paywall gate.
- Следовать паттернам тестов в `backend/tests/billing/test_paywall_gate.py` — fixture `clear_billing_tables`, прямое создание `UserAccessState` через `db.add()`.
- Использовать `patch` для simulating DB errors в error path тесте (как в `test_payment_confirmation.py`).
- Проверять, что `/status` routing (`handle_session_entry` с `message.text="/status"`) корректно вызывает `_handle_status_command` и НЕ вызывает `evaluate_incoming_message_safety` (статусная команда, не рефлексивный flow).

### References

- Story source и AC: [Source: planning-artifacts/epics.md#story-45]
- Product requirement FR25: [Source: planning-artifacts/prd.md]
- Architecture domain boundaries: [Source: planning-artifacts/architecture.md#domain-boundaries]
- Architecture operational signal expectations: [Source: planning-artifacts/architecture.md#operational-signal-expectations]
- UX feedback patterns (calm messaging tone): [Source: planning-artifacts/ux-design-specification.md#feedback-patterns]
- UX Premium Gate Prompt states: [Source: planning-artifacts/ux-design-specification.md#premium-gate-prompt]
- Live billing service (existing functions: `get_user_access_state`, `build_paywall_response`, `is_free_eligible`): [Source: backend/app/billing/service.py]
- Live billing models (UserAccessState: `access_tier`, `threshold_reached_at`): [Source: backend/app/billing/models.py]
- Live billing prompts (tone reference): [Source: backend/app/billing/prompts.py]
- Live session_bootstrap (`handle_session_entry` routing, `/start` command pattern, `_build_response`, `_get_or_create_active_session`): [Source: backend/app/conversation/session_bootstrap.py]
- Live ops signals: [Source: backend/app/ops/signals.py]
- Story 4.4 implementation notes (error handling patterns, signal recording without active session): [Source: implementation-artifacts/4-4-handling-payment-events-and-updating-access-state.md]
## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

- Story 4.5 implemented as informational command `/status`.
- Logical flow mirrors paywall gate logic (AC 6 consistency).
- Red-Green-Refactor followed: tests written first, failing on missing constants.
- Implementation completed in `prompts.py`, `service.py`, and `session_bootstrap.py`.
- Tests passed (5 out of 5 in `test_status_command.py`).
- 2 pre-existing crisis tests still failing (expected).

### Completion Notes List

- Added `STATUS_FREE_ACTIVE_MESSAGE`, `STATUS_FREE_THRESHOLD_REACHED_MESSAGE`, `STATUS_PREMIUM_MESSAGE`, `STATUS_ERROR_MESSAGE` to `billing/prompts.py`.
- Implemented `build_status_response` in `billing/service.py` to handle all access tiers and threshold states.
- Added `/status` command routing to `session_bootstrap.py`.
- Implemented `_handle_status_command` with full error handling and signal recording (`billing_status_check_failed`).
- Added comprehensive tests in `backend/tests/billing/test_status_command.py`.

### File List

- `backend/app/billing/prompts.py` (modified)
- `backend/app/billing/service.py` (modified)
- `backend/app/conversation/session_bootstrap.py` (modified)
- `backend/tests/billing/test_status_command.py` (added)

## Change Log

- Implemented `/status` command to show current access/subscription state.
- Ensured consistency between status display and actual paywall logic.
- Added operational signals for failed status checks.

