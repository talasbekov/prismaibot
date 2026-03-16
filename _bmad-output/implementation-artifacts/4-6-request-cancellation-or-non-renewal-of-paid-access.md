# Story 4.6: Запрос cancellation или non-renewal paid access

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a paying user,
I want иметь понятный способ отменить продление или прекратить платный доступ,
so that я сохраняю контроль над подпиской и не чувствую себя запертым в оплате.

## Acceptance Criteria

1. **Given** у пользователя есть active paid access (`access_tier="premium"`), **When** он отправляет команду `/cancel`, **Then** система принимает запрос и немедленно понижает `access_tier` до `"free"`, **And** пользователь получает спокойное подтверждение с объяснением, что произошло и каковы ограничения продукта (оплата через Telegram Stars уже завершена, возврат — через поддержку Telegram), **And** ops signal `billing_cancellation_request_received` записывается для operator awareness. [Source: epics.md#story-46]
2. **Given** billing model Telegram Stars — это one-time payment, а не recurring subscription, **When** cancellation request обработан корректно, **Then** `access_tier` обновляется до `"free"` немедленно (нет периода до которого нужно ждать), **And** продукт не сообщает, что «подписка отменена» в смысле recurring billing, которого нет. [Source: epics.md#story-46, architecture.md#billing-boundary]
3. **Given** у пользователя нет active paid access (`access_tier="free"`), **When** он отправляет команду `/cancel`, **Then** продукт отвечает понятным сообщением, что активной подписки нет и отменять нечего, **And** не создаёт ложного впечатления, что отмена произошла, **And** никаких изменений в DB не делается. [Source: epics.md#story-46]
4. **Given** provider-side cancellation или refund requires separate action (Stars — one-time, нет API refund от product), **When** продукт обрабатывает запрос на отмену, **Then** пользователю явно сообщается ограничение: возврат Stars возможен только через поддержку Telegram, **And** продукт не утверждает, что возврат средств выполнен. [Source: epics.md#story-46]
5. **Given** cancellation workflow завершается с ошибкой (DB error при загрузке state или downgrade), **When** система не может надёжно завершить запрос, **Then** failure становится observable через ops signal `billing_cancellation_failed`, **And** пользователь видит спокойное сообщение об ошибке с предложением попробовать позже, **And** пользователь не остаётся в неопределённости. [Source: epics.md#story-46]
6. **Given** пользователь после `/cancel` проверяет свой статус командой `/status`, **When** access/subscription state отображается, **Then** он показывает `free` tier — согласован с последним confirmed cancellation outcome, **And** monetization behavior (paywall gate) тоже согласован с новым free state. [Source: epics.md#story-46]

## Tasks / Subtasks

- [x] Добавить cancellation prompt strings в `billing/prompts.py` (AC: 1, 3, 4, 5)
  - [x] `CANCEL_PREMIUM_SUCCESS_MESSAGE: str` — Russian, calm: объясняет, что premium отключён, Stars уже оплачены (one-time), возврат — через поддержку Telegram
  - [x] `CANCEL_NO_ACTIVE_SUBSCRIPTION_MESSAGE: str` — Russian, calm: объясняет, что нет активной подписки, отменять нечего
  - [x] `CANCEL_ERROR_MESSAGE: str` — Russian, calm: ошибка обработки, попробуйте позже

- [x] Добавить `CancellationResult` и `process_cancellation_request()` в `billing/service.py` (AC: 1, 2, 3, 4)
  - [x] `@dataclass class CancellationResult`: поля `was_premium: bool`, `message: str`, `action: str`
  - [x] Сигнатура: `process_cancellation_request(session: Session, *, telegram_user_id: int) -> CancellationResult`
  - [x] Если `state.access_tier == "premium"` → вызвать `repository.upgrade_access_tier(session, state, "free")` → вернуть `CancellationResult(was_premium=True, message=CANCEL_PREMIUM_SUCCESS_MESSAGE, action="cancellation_accepted")`
  - [x] Иначе (free tier) → вернуть `CancellationResult(was_premium=False, message=CANCEL_NO_ACTIVE_SUBSCRIPTION_MESSAGE, action="no_active_subscription")`
  - [x] **NO new repository function needed**: `upgrade_access_tier(session, state, "free")` уже существует и принимает любой tier

- [x] Добавить routing `/cancel` и `_handle_cancel_command()` в `session_bootstrap.py` (AC: 1, 3, 4, 5)
  - [x] Импортировать `process_cancellation_request` из `billing.service` и `CANCEL_ERROR_MESSAGE` из `billing.prompts`
  - [x] После `/status` routing, ПЕРЕД `_handle_message`, добавить:
    ```python
    if message.text.strip() == "/cancel":
        return _handle_cancel_command(session, message.telegram_user_id, message.chat_id)
    ```
  - [x] Добавить `_handle_cancel_command(session: Session, telegram_user_id: int, chat_id: int) -> TelegramWebhookResponse`:
    - Вызвать `process_cancellation_request(session, telegram_user_id=telegram_user_id)` → `result`
    - `session.commit()` после успешного `process_cancellation_request`
    - Если `result.was_premium == True`: после commit записать `record_retryable_signal(..., signal_type="billing_cancellation_request_received", ...)`
    - Return `TelegramWebhookResponse(status="ok", action=result.action, handled=True, messages=[TelegramMessageOut(text=result.message)])`
    - On exception: `session.rollback()`, get or create active session, record `billing_cancellation_failed` signal, return error response

- [x] Написать тесты (AC: 1, 2, 3, 5, 6)
  - [x] Создать `backend/tests/billing/test_cancel_command.py`
  - [x] Test: premium user отправляет `/cancel` → `action="cancellation_accepted"`, текст = `CANCEL_PREMIUM_SUCCESS_MESSAGE`, `UserAccessState.access_tier == "free"` в DB
  - [x] Test: premium user отправляет `/cancel` → ops signal `billing_cancellation_request_received` записан
  - [x] Test: free user (no premium) отправляет `/cancel` → `action="no_active_subscription"`, текст = `CANCEL_NO_ACTIVE_SUBSCRIPTION_MESSAGE`, никаких DB изменений
  - [x] Test: DB error → `action="cancellation_error"`, текст = `CANCEL_ERROR_MESSAGE`, signal `billing_cancellation_failed` записан
  - [x] Test: consistency — после `/cancel` premium user, `handle_session_entry` с `/status` показывает free status (AC 6 — regression guard)
  - [x] Запустить `pytest`, `ruff check --fix`, `mypy` из `backend/`

## Dev Notes

- **`/cancel` — это Telegram команда, не reflective flow**: Аналогично `/status`, обрабатывается ДО `_handle_message`. Не создаётся `TelegramSession`, нет billing gate, нет safety check. [Source: session_bootstrap.py#_handle_status_command pattern]
- **Telegram Stars — ONE-TIME PAYMENT, не subscription**: В продукте нет recurring billing. `PurchaseIntent.status == "completed"` — это всё, что есть после успешной оплаты. Нет "subscription_id", нет renewal event. Поэтому:
  - "Cancellation" = немедленное понижение `access_tier` до `"free"` в нашей DB
  - Provider-side: нет API для отзыва Stars. Пользователь должен обращаться в поддержку Telegram напрямую
  - Message ДОЛЖЕН объяснить это ограничение честно — не утверждать что Stars возвращены [Source: epics.md#story-46-AC4]
- **Точка вставки в `handle_session_entry`**: Текущая структура после Story 4.5:
  1. `pre_checkout_query` check
  2. `successful_payment` check
  3. `callback_query` check (pay:stars, mode selection)
  4. `_parse_message` → если `/start` → `_build_opening_prompt()`
  5. Если `/status` → `_handle_status_command()`
  6. `_handle_message`

  Добавить `/cancel` ПОСЛЕ `/status` check, ПЕРЕД `_handle_message`:
  ```python
  if message.text.strip() == "/status":
      return _handle_status_command(session, message.telegram_user_id, message.chat_id)

  if message.text.strip() == "/cancel":
      return _handle_cancel_command(session, message.telegram_user_id, message.chat_id)
  ```
- **`upgrade_access_tier` принимает любой tier**: `repository.upgrade_access_tier(session, state, "free")` — вызов downgrade. Существующая функция достаточна. НЕ создавать новую функцию в repository. [Source: backend/app/billing/repository.py#upgrade_access_tier]
- **`process_cancellation_request` pattern**: Следует `confirm_payment_and_upgrade` в `service.py` — возвращает dataclass с результатом, сам делает DB mutation через repository, но НЕ делает `session.commit()`. Commit делает session_bootstrap после вызова. [Source: billing/service.py#confirm_payment_and_upgrade]
- **Signal recording паттерн**: После успешного commit, если `result.was_premium`, записать signal. Сигнал НЕ должен blockit основную операцию. Следовать паттерну Story 4.4 (_handle_successful_payment post-commit signal recording). [Source: session_bootstrap.py#_handle_successful_payment]
- **Error handling**: При DB error в `process_cancellation_request` → rollback → get or create active session → flush → record `billing_cancellation_failed` signal → commit → return error response. Паттерн аналогичен `_handle_status_command`. [Source: session_bootstrap.py#_handle_status_command]
- **Tone и язык**: Все prompt strings — русский, calm, без восклицательных знаков, без технических терминов типа "access_tier", без raw Stars counts. `CANCEL_PREMIUM_SUCCESS_MESSAGE` ДОЛЖЕН честно объяснить: premium отключён + Stars оплачены once + для refund → поддержка Telegram. [Source: billing/prompts.py tone reference]
- **Не трогать**: `billing/api.py`, `billing/models.py` (нет нового поля), `billing/repository.py` (нет нового метода), любые `memory/`, `safety/` модули
- **mypy**: Как и в 4.5, не ожидается новых `# type: ignore` — нет новых моделей с BigInteger. `CancellationResult` — обычный `@dataclass`, не `SQLModel`.
- **2 pre-existing test failures**: Crisis step-down тесты всё ещё могут падать — не связано с billing. Не расследовать. [Source: story 4.1-4.5 notes]
- **`python-telegram-bot` 21.x НЕ импортировать**: В `session_bootstrap.py` и `billing/service.py` не использовать. [Source: Story 4.3 dev notes]

### Project Structure Notes

- Live backend layout: `backend/app/`, не `src/goals/`
- Новые файлы НЕ нужны в billing module — только модификации существующих
- Модифицируемые файлы:
  - `backend/app/billing/prompts.py` — добавить 3 новых prompt constants
  - `backend/app/billing/service.py` — добавить `CancellationResult` dataclass + `process_cancellation_request()`
  - `backend/app/conversation/session_bootstrap.py` — добавить routing `/cancel` + `_handle_cancel_command()`
- Новый тестовый файл:
  - `backend/tests/billing/test_cancel_command.py`
- Не трогать:
  - `backend/app/billing/api.py`
  - `backend/app/billing/models.py`
  - `backend/app/billing/repository.py`
  - `backend/app/core/config.py`

### Technical Requirements

- `process_cancellation_request` должна вызываться с тем же session объектом что и последующий commit — без промежуточных commit внутри функции. [Source: session_bootstrap.py#_handle_message pattern]
- После успешного downgrade premium → free: `UserAccessState.access_tier` в DB должен быть `"free"` — это тот же источник истины что и paywall gate и `/status` (AC 6 гарантирован структурно). [Source: session_bootstrap.py#billing-gate, epics.md#story-46-AC6]
- Failure должен быть observable (ops signal) и user-visible (calm message). [Source: architecture.md#operational-signal-expectations]
- `/cancel` не создаёт `TelegramSession` — информационная/управляющая команда, не reflective session. [Source: session_bootstrap.py#_handle_status_command pattern]

### Architecture Compliance

- `billing/` owns payment state и premium access logic — `process_cancellation_request()` идёт в `service.py`. [Source: architecture.md#domain-boundaries]
- `conversation/session_bootstrap.py` вызывает billing service functions и транслирует Telegram context. [Source: architecture.md#domain-boundaries]
- `snake_case` для всех полей, signal types. UTC timestamps. [Source: architecture.md#naming-patterns]
- Logging: emit `telegram_user_id` для ops tracing, никогда не в паре с conversation content. [Source: architecture.md#logging-pattern]
- Event names как domain facts: `"billing_cancellation_request_received"`, `"billing_cancellation_failed"`. [Source: architecture.md#async-internal-event-naming]

### Library / Framework Requirements

- FastAPI `0.114.x`, SQLModel `0.0.21`, Pydantic v2 — новые зависимости не нужны. [Source: backend/pyproject.toml]
- Использовать `repository.upgrade_access_tier(session, state, "free")` для downgrade — существующая функция. [Source: billing/repository.py]
- Использовать `get_or_create_user_access_state` через `get_user_access_state` из `app.billing.service` (внутри `process_cancellation_request`). [Source: billing/service.py]
- Использовать `record_retryable_signal` из `app.ops.signals` для observability. [Source: backend/app/ops/signals.py]
- Использовать `_get_or_create_active_session` из `session_bootstrap.py` в error path. [Source: session_bootstrap.py]

### Testing Requirements

- Test commands (run from `backend/`):
  ```
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run alembic upgrade heads
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests/ -q
  uv run ruff check --fix app tests
  uv run mypy app tests
  ```
- Coverage: premium user cancel (downgrade + signal), free user cancel (no-op + correct message), DB error (signal + error message), consistency check после cancel → /status.
- Следовать паттернам тестов в `backend/tests/billing/test_status_command.py` — fixture `clear_billing_tables`, прямое создание `UserAccessState` через `db.add()`.
- Использовать `patch` для simulating DB errors в error path тесте. [Source: test_status_command.py pattern]
- Проверять что `/cancel` routing (`handle_session_entry` с `message.text="/cancel"`) корректно вызывает `_handle_cancel_command` и НЕ вызывает `evaluate_incoming_message_safety`. [Source: session_bootstrap.py#routing pattern]
- Для consistency test: создать UserAccessState с premium, отправить `/cancel` через `handle_session_entry`, затем отправить `/status` через `handle_session_entry` → response содержит `STATUS_FREE_ACTIVE_MESSAGE`. [Source: epics.md#story-46-AC6]

### References

- Story source и AC: [Source: planning-artifacts/epics.md#story-46]
- Product requirement FR26: [Source: planning-artifacts/prd.md]
- Architecture domain boundaries: [Source: planning-artifacts/architecture.md#domain-boundaries]
- Architecture operational signal expectations: [Source: planning-artifacts/architecture.md#operational-signal-expectations]
- UX calm messaging tone: [Source: planning-artifacts/ux-design-specification.md]
- Live billing service (existing: `get_user_access_state`, `build_status_response`, `confirm_payment_and_upgrade`, `CancellationResult` pattern): [Source: backend/app/billing/service.py]
- Live billing repository (existing `upgrade_access_tier` — reuse for downgrade): [Source: backend/app/billing/repository.py]
- Live billing models (`UserAccessState.access_tier`): [Source: backend/app/billing/models.py]
- Live billing prompts (tone reference): [Source: backend/app/billing/prompts.py]
- Live session_bootstrap (`handle_session_entry` routing, `/status` command pattern as reference, `_get_or_create_active_session`, `_handle_status_command`): [Source: backend/app/conversation/session_bootstrap.py]
- Live ops signals: [Source: backend/app/ops/signals.py]
- Story 4.5 dev notes (informational command pattern, `/status` as reference for `/cancel`): [Source: implementation-artifacts/4-5-viewing-current-access-subscription-status.md]

## Dev Agent Record

### Agent Model Used

gemini-2.0-pro-exp-02-05

### Debug Log References

### Completion Notes List

- Added cancellation prompt strings to `backend/app/billing/prompts.py`.
- Implemented `process_cancellation_request` in `backend/app/billing/service.py` to handle immediate downgrade of access tier.
- Integrated `/cancel` command routing in `backend/app/conversation/session_bootstrap.py`.
- Added operational signal recording for successful cancellation and failed attempts.
- Created comprehensive tests in `backend/tests/billing/test_cancel_command.py` covering success, "no active subscription", and database error cases.
- Verified consistency between `/cancel` and `/status` commands.
- Fixed database migration and table naming issues during testing.
- Fixed `record_retryable_signal` call signature in `_handle_cancel_command`.

### File List

- `backend/app/billing/prompts.py`
- `backend/app/billing/service.py`
- `backend/app/conversation/session_bootstrap.py`
- `backend/tests/billing/test_cancel_command.py`
