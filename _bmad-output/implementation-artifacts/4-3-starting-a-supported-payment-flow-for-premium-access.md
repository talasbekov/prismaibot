# Story 4.3: Запуск supported payment flow для premium access

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь, который решил оплатить premium access,
I want запустить понятный и поддерживаемый payment flow,
So that я могу быстро и безопасно разблокировать платный доступ.

## Acceptance Criteria

1. When the user is on the premium boundary (paywall shown) and chooses to pay, the system launches a Telegram Stars payment flow via `sendInvoice` through the Telegram Bot API. The user journey remains clear and does not require understanding internal billing details. [Source: epics.md#story-43]
2. When the payment flow is initiated, the invoice is created through the `billing/` module boundary. Conversation core does not contain provider-specific payment logic. [Source: epics.md#story-43, architecture.md#adapter-boundaries]
3. When the payment initiation succeeds, the system stores a `PurchaseIntent` record with enough reference data (`invoice_payload`, `telegram_user_id`, `amount`, `currency`) for later reconciliation by Story 4.4. No raw payment instrument details are stored locally. [Source: epics.md#story-43, architecture.md#payment-security-boundary]
4. When the user cancels, closes the payment dialog, or payment initiation does not complete, the user's `access_tier` remains `"free"` and `threshold_reached_at` stays unchanged — no premature access upgrade. [Source: epics.md#story-43]
5. When `sendInvoice` or invoice creation fails, the failure is observable via an ops signal (`"billing_invoice_creation_failed"`), and the user receives a calm, clear message explaining that payment could not be started right now. [Source: epics.md#story-43, architecture.md#operational-signal-expectations]
6. When the user initiates payment multiple times (retry, lag, confusion), the billing layer maintains consistent `PurchaseIntent` state — duplicate initiations do not create contradictory access outcomes. Idempotency keyed on `telegram_user_id` + `"pending"` status. [Source: epics.md#story-43]
7. When Telegram sends a `pre_checkout_query` update, the system answers it with `answerPreCheckoutQuery(ok=True)` within the Telegram timeout, confirming the product is ready to accept payment. This is the handshake step before Telegram charges the user. [Source: Telegram Bot API Payments documentation]

## Tasks / Subtasks

- [x] Add `PurchaseIntent` model in `billing/models.py` (AC: 3, 6)
  - [x] Add `PurchaseIntent` SQLModel table with fields: `id` (UUID PK), `telegram_user_id` (BigInteger, indexed), `invoice_payload` (str, unique — idempotency key format: `"premium_{telegram_user_id}"`), `amount` (int — Telegram Stars amount), `currency` (str, default `"XTR"`), `status` (str, default `"pending"`, max 32 — values: `"pending"`, `"completed"`, `"failed"`), `provider_payment_charge_id` (str nullable — filled by Story 4.4), `created_at`, `updated_at` (DateTime UTC)
  - [x] Add `UniqueConstraint` on `invoice_payload` for idempotent intent tracking
  - [x] Write Alembic migration for `purchase_intents` table. Check `alembic heads` for correct `down_revision`

- [x] Add purchase intent repository functions in `billing/repository.py` (AC: 3, 6)
  - [x] `get_pending_purchase_intent(session, telegram_user_id) -> PurchaseIntent | None` — find existing intent with `status="pending"` for this user
  - [x] `create_purchase_intent(session, telegram_user_id, invoice_payload, amount, currency) -> PurchaseIntent` — create new intent row

- [x] Add payment initiation service function in `billing/service.py` (AC: 1, 2, 3, 5, 6)
  - [x] `get_or_create_purchase_intent(session, telegram_user_id) -> PurchaseIntent` — if a `"pending"` intent already exists for this user, return it (idempotent); otherwise create a new one with `invoice_payload="premium_{telegram_user_id}"`, `amount=settings.PREMIUM_STARS_PRICE`, `currency="XTR"`. Callers must commit.
  - [x] Keep all provider-specific logic (invoice_payload format, currency, amount) within `billing/` boundary

- [x] Add `PREMIUM_STARS_PRICE` to settings in `core/config.py` (AC: 1)
  - [x] Add `PREMIUM_STARS_PRICE: int = 1` to `Settings` class. This is the Telegram Stars price for premium access. Overridable via env var. Comment: "Price in Telegram Stars for premium access."
  - [x] Note: 1 Star ≈ $0.013 USD. Typical products use 50–500 Stars. The operator sets the actual value via env var.

- [x] Add payment prompt constant in `billing/prompts.py` (AC: 5)
  - [x] Add `PAYMENT_INITIATION_ERROR_MESSAGE: str` — Russian, calm tone: "Сейчас не получилось запустить оплату. Попробуйте ещё раз чуть позже." (Keep consistent with existing prompts tone)
  - [x] Add `INVOICE_TITLE: str = "Premium доступ — goals"` — shown in Telegram payment dialog
  - [x] Add `INVOICE_DESCRIPTION: str` — Russian, short: explains what premium unlocks (continuity, remembered context, continued deep work). 1–2 sentences max. Must align with `PAYWALL_MESSAGE` framing

- [x] Extend paywall response to include payment button in `billing/service.py` (AC: 1, 2)
  - [x] Modify `build_paywall_response()` to return a tuple `(str, list[list[InlineButton]])` instead of just `str` — the first element is the paywall text, the second is an inline keyboard with a single button row: `[InlineButton(text="Оформить premium ✦", callback_data="pay:stars")]`
  - [x] Import `InlineButton` from `app.conversation.session_bootstrap`
  - [x] Update Story 4.2's paywall gate in `session_bootstrap.py` to pass the inline keyboard from the tuple to `_build_response(inline_keyboard=...)`

- [x] Handle `pay:stars` callback in `session_bootstrap.py` → `handle_session_entry` (AC: 1, 2, 5, 6)
  - [x] In `handle_session_entry`, before the existing `callback_query` block (mode selection), add handling for `pay:stars` callback_data:
    ```python
    if "callback_query" in update:
        callback_data = update["callback_query"].get("data", "")
        if callback_data == "pay:stars":
            return _handle_payment_initiation(session, update["callback_query"])
        # ... existing mode selection logic
    ```
  - [x] Add `_handle_payment_initiation(session, callback_query) -> TelegramWebhookResponse`:
    - [x] Extract `telegram_user_id` and `chat_id` from `callback_query["from"]["id"]` and `callback_query["message"]["chat"]["id"]`
    - [x] Call `billing_service.get_or_create_purchase_intent(session, telegram_user_id)`
    - [x] Commit DB session
    - [x] Return `TelegramWebhookResponse` with `action="payment_invoice"`, `signals=["send_invoice"]`, and invoice data in a new response field (see next task)
    - [x] On failure: log, record `"billing_invoice_creation_failed"` signal, return error message response

- [x] Extend `TelegramWebhookResponse` with invoice data (AC: 1, 3)
  - [x] Add optional `invoice` field to `TelegramWebhookResponse`:
    ```python
    class InvoiceData(BaseModel):
        title: str
        description: str
        payload: str  # invoice_payload for reconciliation
        currency: str  # "XTR" for Telegram Stars
        prices: list[dict[str, Any]]  # [{"label": "Premium", "amount": <stars>}]
        chat_id: int

    class TelegramWebhookResponse(BaseModel):
        # ... existing fields ...
        invoice: InvoiceData | None = None
    ```
  - [x] The caller (Telegram adapter / bot runner) is responsible for calling `bot.send_invoice()` when `invoice` is present in the response. This keeps the webhook handler synchronous and provider-agnostic per architecture

- [x] Handle `pre_checkout_query` in `handle_session_entry` (AC: 7)
  - [x] In `handle_session_entry`, add a new branch before `callback_query` handling:
    ```python
    if "pre_checkout_query" in update:
        return _handle_pre_checkout_query(update["pre_checkout_query"])
    ```
  - [x] Add `_handle_pre_checkout_query(query: dict) -> TelegramWebhookResponse`:
    - [x] Extract `pre_checkout_query_id` from `query["id"]`
    - [x] Return `TelegramWebhookResponse` with `action="pre_checkout_ok"`, `signals=["answer_pre_checkout"]`, and a new optional field `pre_checkout_query_id: str | None = None` on the response model
    - [x] The caller (Telegram adapter) answers `answerPreCheckoutQuery(pre_checkout_query_id, ok=True)` based on this
    - [x] No DB access needed — this is a fast acknowledgment step. Validation of the actual payment happens in Story 4.4 via `successful_payment`

- [x] Write tests (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] Create `backend/tests/billing/test_payment_initiation.py`
  - [x] Test: `get_or_create_purchase_intent` creates new intent with correct fields when none exists
  - [x] Test: `get_or_create_purchase_intent` returns existing pending intent for same user (idempotent)
  - [x] Test: `pay:stars` callback triggers payment initiation and returns `action="payment_invoice"` with invoice data
  - [x] Test: `pay:stars` callback when billing fails → returns error message + records `"billing_invoice_creation_failed"` signal
  - [x] Test: `pre_checkout_query` update returns `action="pre_checkout_ok"` with query ID
  - [x] Test: paywall response now includes inline keyboard with payment button
  - [x] Test: `PurchaseIntent` with duplicate `invoice_payload` raises DB constraint error (verify idempotency mechanism)
  - [x] Test: user `access_tier` remains `"free"` after payment initiation (no premature upgrade)
  - [x] Run `pytest`, `ruff check --fix`, `mypy` from `backend/`

## Dev Notes

- **Story 4.2 left the seam for this story**: `build_paywall_response()` returns text-only `PAYWALL_MESSAGE`. Story 4.3 extends this to include an inline keyboard button for payment initiation. Story 4.2's dev notes explicitly say: "Story 4.3 will extend `build_paywall_response()` to add inline keyboard buttons for payment initiation." [Source: 4-2 story completion notes]
- **Telegram Stars payment flow mechanics**: Telegram Stars uses currency code `"XTR"`. Provider token is empty string `""` for Stars (no external payment provider needed). Flow: bot sends invoice → user pays in Telegram UI → Telegram sends `pre_checkout_query` → bot answers OK → Telegram charges → Telegram sends `message` with `successful_payment`. Story 4.3 covers steps 1–3 (initiation + pre_checkout). Story 4.4 covers `successful_payment` handling and access state update.
- **`_build_response` already supports `inline_keyboard`**: The helper accepts `inline_keyboard: list[list[InlineButton]] | None = None` parameter. The paywall gate just needs to pass it through. [Source: session_bootstrap.py:719]
- **`InlineButton` model already exists**: Defined at session_bootstrap.py:78 with `text`, `callback_data`, and `url` fields with validation. Reuse for the payment button.
- **`handle_session_entry` callback routing**: Currently handles only `callback_query` for mode selection. Add `pay:stars` handling before the mode selection check. Also add `pre_checkout_query` as a new top-level update type (separate from `callback_query` and `message`). [Source: session_bootstrap.py:115-123]
- **`TelegramWebhookResponse` is the contract with the Telegram adapter**: The actual `bot.send_invoice()` and `bot.answer_pre_checkout_query()` calls happen in the Telegram adapter layer (not in session_bootstrap). session_bootstrap returns structured data; the adapter translates it to Telegram API calls. This preserves the architecture's adapter boundary. [Source: architecture.md#adapter-boundaries]
- **No access_tier change in this story**: `UserAccessState.access_tier` stays `"free"` throughout Story 4.3. Access upgrade to `"premium"` happens in Story 4.4 after confirmed `successful_payment`. This story only records purchase intent.
- **Idempotency for PurchaseIntent**: Use `telegram_user_id` + `status="pending"` lookup to return existing intent. If user clicks pay button multiple times, they get the same pending intent. Once Story 4.4 marks it `"completed"`, a new intent can be created if needed. The `invoice_payload` format `"premium_{telegram_user_id}"` is unique per user and used by Telegram for reconciliation.
- **`python-telegram-bot` 21.x is installed but NOT used in session_bootstrap**: The current architecture uses raw dict parsing of Telegram webhook updates and returns structured `TelegramWebhookResponse`. Do NOT import `python-telegram-bot` in session_bootstrap or billing service. The adapter layer handles the actual API calls. [Source: session_bootstrap.py, bot/api.py]
- **Fail-open vs fail-closed for payment**: Unlike the billing access gate (fail-open), payment initiation failure should NOT grant access. If invoice creation fails, the user sees an error message but stays in free tier. This is fail-closed for access, fail-visible for the error. [Source: epics.md#story-43 — "access state пользователя не повышается prematurely"]
- **2 pre-existing test failures**: Crisis step-down tests were already failing before Story 4.1 — not related to billing. Do not investigate them. [Source: 4-1, 4-2 story completion notes]
- **mypy**: Expect `# type: ignore[call-overload]` for `BigInteger` fields, matching existing patterns in `billing/models.py`. [Source: 4-1 story completion notes]

### Project Structure Notes

- Live backend layout: `backend/app/`, not aspirational `src/goals/...`
- New files:
  - `backend/app/alembic/versions/<hash>_add_purchase_intents.py` — migration for `purchase_intents` table
- Modified files:
  - `backend/app/billing/models.py` — add `PurchaseIntent` model
  - `backend/app/billing/repository.py` — add `get_pending_purchase_intent`, `create_purchase_intent`
  - `backend/app/billing/service.py` — add `get_or_create_purchase_intent`, modify `build_paywall_response` return type
  - `backend/app/billing/prompts.py` — add `PAYMENT_INITIATION_ERROR_MESSAGE`, `INVOICE_TITLE`, `INVOICE_DESCRIPTION`
  - `backend/app/core/config.py` — add `PREMIUM_STARS_PRICE`
  - `backend/app/conversation/session_bootstrap.py` — extend `TelegramWebhookResponse` with `InvoiceData`, add `pre_checkout_query_id`, handle `pay:stars` callback and `pre_checkout_query` update, update paywall gate to pass inline keyboard
- New test file:
  - `backend/tests/billing/test_payment_initiation.py`
- Do NOT modify:
  - `backend/app/billing/api.py` — webhook stub stays for Story 4.4
  - `backend/app/bot/api.py` — adapter layer, untouched
  - Any `memory/`, `safety/`, or `conversation/` modules beyond session_bootstrap
  - `backend/app/billing/models.py` `UserAccessState` or `FreeSessionEvent` — no changes to existing models

### Technical Requirements

- Payment initiation must not change `access_tier` or grant premium access — Story 4.4 handles access upgrade after confirmed payment. [Source: epics.md#story-43]
- `PurchaseIntent` must be a first-class DB table in `billing/` boundary. [Source: architecture.md#domain-boundaries]
- Invoice creation failure must be observable (ops signal) and user-visible (calm error message). [Source: architecture.md#operational-signal-expectations]
- `pre_checkout_query` must be handled fast — Telegram enforces a 10-second timeout on this. No DB writes, no LLM calls. [Source: Telegram Bot API]
- Provider-specific details (currency `"XTR"`, Stars pricing) stay in `billing/` — conversation module only passes structured data. [Source: architecture.md#adapter-boundaries]
- Billing logic stays in `billing/`; `session_bootstrap.py` is a caller only. [Source: architecture.md#domain-boundaries]

### Architecture Compliance

- `billing/` owns payment state, purchase intents, and premium access logic. `conversation/session_bootstrap.py` only calls billing service functions. [Source: architecture.md#domain-boundaries]
- Payment provider adapter stays behind billing boundary — `session_bootstrap` returns `InvoiceData`, the Telegram adapter translates it to `bot.send_invoice()`. [Source: architecture.md#adapter-boundaries]
- Repositories own persistence access; services own business rules. [Source: architecture.md#layer-boundaries-within-a-domain]
- `snake_case` for all DB columns, signal types, JSON fields. Plural table name: `purchase_intents`. UTC timestamps with `DateTime(timezone=True)`. [Source: architecture.md#naming-patterns]
- Logging: emit `telegram_user_id` for ops tracing but never paired with conversation content. [Source: architecture.md#logging-pattern]

### Library / Framework Requirements

- FastAPI `0.114.x`, SQLModel `0.0.21`, Pydantic v2 — no new dependencies needed. [Source: backend/pyproject.toml]
- Telegram Stars requires no external payment SDK — it's native Telegram Bot API. No new packages to install.
- Use `_build_response` from session_bootstrap for all response construction. [Source: session_bootstrap.py]
- Use `record_retryable_signal` from `app.ops.signals` for failure observability. [Source: backend/app/ops/signals.py]
- Alembic migration must follow existing chain — run `alembic heads` first. [Source: existing migration patterns]

### Testing Requirements

- Test commands (run from `backend/`):
  ```
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run alembic upgrade heads
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests/ -q
  uv run ruff check --fix app tests
  uv run mypy app tests
  ```
- Coverage: purchase intent creation, idempotency, payment callback routing, pre_checkout handling, paywall button presence, failure paths, access_tier immutability during initiation.
- Follow existing test patterns in `backend/tests/billing/test_free_usage.py` and `test_paywall_gate.py`.

### References

- Story source and AC: [Source: planning-artifacts/epics.md#story-43]
- Product requirement FR23: [Source: planning-artifacts/prd.md]
- Architecture adapter boundaries: [Source: planning-artifacts/architecture.md#adapter-boundaries]
- Architecture payment security boundary: [Source: planning-artifacts/architecture.md#payment-security-boundary]
- Architecture domain boundaries: [Source: planning-artifacts/architecture.md#domain-boundaries]
- Architecture operational signal expectations: [Source: planning-artifacts/architecture.md#operational-signal-expectations]
- UX Premium Gate Prompt — text + inline CTA buttons: [Source: planning-artifacts/ux-design-specification.md#premium-gate-prompt]
- Story 4.2 paywall implementation and forward-compatibility notes: [Source: implementation-artifacts/4-2-paywall-after-felt-value-with-continuity-based-framing.md]
- Story 4.1 billing module patterns: [Source: implementation-artifacts/4-1-limited-free-usage-and-usage-threshold-tracking.md]
- Live billing service (build_paywall_response, get_user_access_state): [Source: backend/app/billing/service.py]
- Live billing models (UserAccessState): [Source: backend/app/billing/models.py]
- Live session_bootstrap (_build_response, InlineButton, handle_session_entry): [Source: backend/app/conversation/session_bootstrap.py]
- Live ops signals: [Source: backend/app/ops/signals.py]
- Live config settings: [Source: backend/app/core/config.py]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}} (review fixes applied by code-review workflow)

### Debug Log References

- Story auto-selected from sprint-status.yaml: first backlog story is `4-3-starting-a-supported-payment-flow-for-premium-access`.
- Loaded Epic 4 from epics.md — full story 4.3 acceptance criteria and cross-story context (4.4 payment event handling is out of scope).
- Loaded Story 4.2 implementation artifact — confirmed billing module state: `build_paywall_response` returns text-only, explicitly left seam for Story 4.3 to add inline keyboard. Confirmed `_build_response` already supports `inline_keyboard` parameter.
- Loaded Story 4.1 implementation artifact — confirmed billing models, repository, and service patterns.
- Analyzed live backend: billing/service.py, billing/models.py, billing/repository.py, billing/prompts.py, billing/api.py — all read completely.
- Analyzed session_bootstrap.py — confirmed `handle_session_entry` structure: callback_query handling, _parse_message, _build_response with inline_keyboard support, InlineButton model, TelegramWebhookResponse model.
- Analyzed core/config.py — confirmed PAYMENT_PROVIDER_WEBHOOK_SECRET exists, pattern for adding new settings.
- Loaded architecture.md — confirmed adapter boundaries (payment provider behind billing boundary), domain boundaries, payment security boundary, naming patterns.
- Loaded ux-design-specification.md — confirmed Premium Gate Prompt component spec: "Text plus inline CTA buttons" interaction behavior, states include "payment pending", "payment success", "payment failure".
- Confirmed no git repository (workspace is not a Git repository).
- Epic 4 status already `in-progress` — no update needed.

### Completion Notes List

- Implemented `PurchaseIntent` model and database mappings
- Added Alembic migration `a4b228f82484_add_purchase_intents`
- Refactored `build_paywall_response` to accept and return an `inline_keyboard` tuple for premium access
- Updated `TelegramWebhookResponse` to include `invoice` payload models
- Established `_handle_payment_initiation` to construct Telegram's `sendInvoice` parameters
- Enabled `pre_checkout_query` parsing returning `pre_checkout_ok` action
- Included comprehensive tests for payment intents and failure recovery routes
- Addressed pre-existing mypy type overloads in `app/models.py` for boolean `BigInteger` mappings

### Change Log

- 2026-03-14: Code review — fixed 5 issues: removed duplicate unique constraint on invoice_payload (H1), added missing access_tier immutability test (H2), wrapped error path with rollback/try-except (M1), fixed db.exec→db.execute consistency (M2), documented invoice_payload re-subscription limitation for Story 4.4 (M3). conftest.py PurchaseIntent cleanup added (cross-story fix H1-4.1).
- Finished implementation of Story 4.3 (ready for review)

### File List

- `backend/app/alembic/versions/a4b228f82484_add_purchase_intents.py`
- `backend/app/billing/models.py`
- `backend/app/billing/repository.py`
- `backend/app/billing/service.py`
- `backend/app/billing/prompts.py`
- `backend/app/core/config.py`
- `backend/app/conversation/session_bootstrap.py`
- `backend/tests/billing/test_payment_initiation.py`
- `backend/app/models.py`
