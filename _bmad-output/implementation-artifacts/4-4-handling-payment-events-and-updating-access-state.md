# Story 4.4: Обработка payment events и обновление access state

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a paying user,
I want чтобы продукт корректно распознавал результаты оплаты и обновлял мой access state,
So that мой доступ к premium работает предсказуемо и без путаницы.

## Acceptance Criteria

1. When Telegram sends a `message` update containing `successful_payment` (after Story 4.3's invoice + pre_checkout flow), the system extracts `invoice_payload`, `telegram_payment_charge_id`, and `total_amount` from `message.successful_payment` and routes to payment confirmation handling. [Source: epics.md#story-44, Telegram Bot API Payments]
2. When the `invoice_payload` matches a `PurchaseIntent` with `status="pending"`, the system updates the intent to `status="completed"`, stores `provider_payment_charge_id` (= `telegram_payment_charge_id` for Stars), and upgrades `UserAccessState.access_tier` from `"free"` to `"premium"`. Both changes happen in a single DB transaction. [Source: epics.md#story-44, architecture.md#domain-boundaries]
3. When the same `successful_payment` is received again (Telegram retry / duplicate delivery), the system detects the intent is already `"completed"`, does NOT double-upgrade or error out, and returns success. Idempotent on `invoice_payload` + intent status check. [Source: epics.md#story-44, architecture.md#idempotency-requirements]
4. When `successful_payment` arrives but no matching `PurchaseIntent` is found (orphan payment), the system still upgrades `UserAccessState.access_tier` to `"premium"` (Telegram confirmed the charge — denying access would be incorrect) AND records an ops signal `"billing_payment_intent_not_found"` for operator investigation. [Source: architecture.md#operational-signal-expectations]
5. When the payment confirmation or access upgrade fails due to a DB error, the failure is observable via ops signal `"billing_payment_confirmation_failed"`, and the user receives a calm error message. Access state is NOT upgraded on unconfirmed transactions. [Source: epics.md#story-44, architecture.md#operational-signal-expectations]
6. When a user with `access_tier="premium"` enters a new session, the paywall gate in `_handle_message` bypasses the paywall check — premium users are never shown the paywall regardless of `threshold_reached_at`. [Source: epics.md#story-44 — "система применяет актуальный paid or unpaid status consistently"]
7. When payment confirmation succeeds, the user receives a calm, one-line Russian confirmation message. No exclamation marks, no over-emphasis. [Source: ux-design-specification.md#feedback-patterns]

## Tasks / Subtasks
  - [x] `confirm_payment_and_upgrade(session, *, invoice_payload, telegram_payment_charge_id, telegram_user_id) -> PaymentConfirmationResult` where `PaymentConfirmationResult` is a simple dataclass/NamedTuple with `success: bool`, `already_completed: bool`, `signals: list[str]`
  - [x] Logic:
    - Get or create `UserAccessState` for `telegram_user_id`
    - Look up `PurchaseIntent` by `invoice_payload`
    - If intent found with `status="pending"` → complete intent, upgrade access → `(success=True, already_completed=False, signals=[])`
    - If intent found with `status="completed"` → ensure access is premium (idempotent repair) → `(success=True, already_completed=True, signals=[])`
    - If intent NOT found → upgrade access anyway (Telegram confirmed payment), → `(success=True, already_completed=False, signals=["billing_payment_intent_not_found"])`
  - [x] Callers must commit. On exception, caller handles rollback and ops signal recording

- [x] Add confirmation prompt in `billing/prompts.py` (AC: 7)
  - [x] `PAYMENT_SUCCESS_MESSAGE: str` — Russian, calm, one-line: "Готово, premium доступ активирован. Контекст и память сохраняются между сессиями." (Align with PAYWALL_MESSAGE framing — continuity value, not feature list)
  - [x] `PAYMENT_CONFIRMATION_ERROR_MESSAGE: str` — Russian, calm: "Оплата получена, но при обновлении доступа произошла ошибка. Попробуйте написать ещё раз через минуту." (Honest about payment received, calming about error)

- [x] Handle `successful_payment` in `session_bootstrap.py` → `handle_session_entry` (AC: 1, 2, 5, 7)
  - [x] In `handle_session_entry`, add a new branch AFTER `pre_checkout_query` handling and BEFORE `callback_query` handling:
    ```python
    if "message" in update and "successful_payment" in update.get("message", {}):
        return _handle_successful_payment(session, update["message"])
    ```
  - [x] Add `_handle_successful_payment(session, message: dict) -> TelegramWebhookResponse`:
    - Extract `telegram_user_id` from `message["from"]["id"]`, `chat_id` from `message["chat"]["id"]`
    - Extract `invoice_payload`, `telegram_payment_charge_id` from `message["successful_payment"]`
    - Call `billing_service.confirm_payment_and_upgrade(session, ...)`
    - Commit DB session
    - Record any returned signals via `record_retryable_signal`
    - Return `_build_response(action="payment_confirmed", messages=[PAYMENT_SUCCESS_MESSAGE], signals=["payment_confirmed"])`
    - On exception: rollback, record `"billing_payment_confirmation_failed"` signal, return error message response

- [x] Update paywall gate in `_handle_message` to bypass for premium users (AC: 6)
  - [x] In the paywall gate block (currently at lines ~305-335 in session_bootstrap.py), BEFORE calling `is_free_eligible(state)`, check `state.access_tier == "premium"` → skip paywall entirely
  - [x] This is a one-line addition: `if state.access_tier != "premium" and not is_free_eligible(state):`
  - [x] No changes to `is_free_eligible()` itself — it stays focused on free-tier threshold logic

- [x] Write tests (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] Create `backend/tests/billing/test_payment_confirmation.py`
  - [x] Test: `confirm_payment_and_upgrade` with pending intent → intent completed, access_tier="premium"
  - [x] Test: `confirm_payment_and_upgrade` idempotent — duplicate call with completed intent → success, no error, access stays "premium"
  - [x] Test: `confirm_payment_and_upgrade` orphan payment (no intent) → access upgraded, signal "billing_payment_intent_not_found" returned
  - [x] Test: `successful_payment` message update routes to `_handle_successful_payment` and returns `action="payment_confirmed"`
  - [x] Test: `successful_payment` duplicate delivery → idempotent success, no error
  - [x] Test: DB failure during confirmation → error message returned, `"billing_payment_confirmation_failed"` signal recorded, access_tier unchanged
  - [x] Test: paywall gate bypassed when `access_tier="premium"` (user with threshold_reached_at set but premium tier → no paywall)
  - [x] Test: paywall gate still triggers for `access_tier="free"` with threshold reached (regression guard)
  - [x] Run `pytest`, `ruff check --fix`, `mypy` from `backend/`

## Dev Notes

- **Telegram Stars `successful_payment` flow**: After Story 4.3's `sendInvoice` → user pays → Telegram sends `pre_checkout_query` → bot answers OK → Telegram charges → Telegram sends a regular `message` update with `successful_payment` field inside `message`. This is NOT a separate webhook callback — it comes through the same Telegram webhook as regular messages. [Source: Telegram Bot API Payments documentation]
- **`successful_payment` update structure**:
  ```json
  {
    "message": {
      "from": {"id": 789},
      "chat": {"id": 789},
      "successful_payment": {
        "currency": "XTR",
        "total_amount": 1,
        "invoice_payload": "premium_789",
        "telegram_payment_charge_id": "charge_abc",
        "provider_payment_charge_id": ""
      }
    }
  }
  ```
  For Telegram Stars, `provider_payment_charge_id` is empty string. Use `telegram_payment_charge_id` as the charge reference stored in `PurchaseIntent.provider_payment_charge_id`. [Source: Telegram Bot API Payments]
- **`billing/api.py` webhook is NOT used for Telegram Stars**: The `/billing/webhook` endpoint with `X-Payment-Webhook-Secret` was created in Story 4.1 as a stub for future ЮKassa support. For Telegram Stars, everything goes through the Telegram webhook → `handle_session_entry`. Do NOT modify `billing/api.py` in this story. [Source: billing/api.py, Story 4.1 implementation]
- **Story 4.3 left the seam for this story**: `PurchaseIntent` model already has `status` field (values: `"pending"`, `"completed"`, `"failed"`) and `provider_payment_charge_id` (nullable). Story 4.3's dev notes explicitly say: "Story 4.4 covers `successful_payment` handling and access state update." [Source: 4-3 story completion notes]
- **Paywall gate update is required in this story**: The current paywall gate checks `is_free_eligible(state)` which returns `threshold_reached_at is None`. After premium upgrade, `threshold_reached_at` is still set (it was set when the user hit the free session limit). Without updating the gate to check `access_tier`, premium users would still see the paywall. This is a one-line condition change. [Source: session_bootstrap.py paywall gate, billing/service.py:is_free_eligible]
- **`invoice_payload` re-subscription limitation**: Story 4.3 code review documented that `invoice_payload="premium_{telegram_user_id}"` has a unique constraint. After completion, the same payload can't be reused for a new intent. This is a known limitation for Story 4.6 (cancellation/re-subscription). For Story 4.4, no action needed — just be aware. [Source: 4-3 story change log M3]
- **Orphan payment handling — trust Telegram, upgrade anyway**: If `successful_payment` arrives but no matching PurchaseIntent exists (race condition, data loss, manual testing), the user legitimately paid. Denying access would be incorrect. Upgrade access and record an ops signal for investigation. [Source: architecture.md#operational-signal-expectations, product principle: monetization integrity]
- **`_build_response` already supports all needed features**: Use existing `_build_response(action=..., messages=[...], signals=[...])` pattern. No new response model fields needed for this story. [Source: session_bootstrap.py:_build_response]
- **`record_retryable_signal` pattern**: Import from `app.ops.signals`. Requires `session_id` — for `successful_payment` handling, use a generated UUID since there's no active conversation session. Follow the same pattern as Story 4.3's error handling in `_handle_payment_initiation`. [Source: session_bootstrap.py:204-213, ops/signals.py]
- **`python-telegram-bot` 21.x is installed but NOT used in session_bootstrap**: Continue using raw dict parsing of Telegram webhook updates. Do NOT import `python-telegram-bot` in session_bootstrap or billing service. [Source: Story 4.3 dev notes]
- **2 pre-existing test failures**: Crisis step-down tests were already failing before Story 4.1 — not related to billing. Do not investigate them. [Source: 4-1, 4-2, 4-3 story completion notes]
- **mypy**: Expect `# type: ignore[call-overload]` for `BigInteger` fields, matching existing patterns in `billing/models.py`. [Source: 4-1, 4-3 story completion notes]

### Project Structure Notes

- Live backend layout: `backend/app/`, not aspirational `src/goals/...`
- No new files in billing module — only modifications to existing files
- Modified files:
  - `backend/app/billing/repository.py` — add `get_purchase_intent_by_payload`, `complete_purchase_intent`, `upgrade_access_tier`
  - `backend/app/billing/service.py` — add `confirm_payment_and_upgrade` + `PaymentConfirmationResult` type
  - `backend/app/billing/prompts.py` — add `PAYMENT_SUCCESS_MESSAGE`, `PAYMENT_CONFIRMATION_ERROR_MESSAGE`
  - `backend/app/conversation/session_bootstrap.py` — add `successful_payment` routing in `handle_session_entry`, add `_handle_successful_payment`, update paywall gate condition
- New test file:
  - `backend/tests/billing/test_payment_confirmation.py`
- Do NOT modify:
  - `backend/app/billing/api.py` — webhook stub stays for future ЮKassa, not used for Stars
  - `backend/app/billing/models.py` — PurchaseIntent and UserAccessState already have all needed fields
  - `backend/app/core/config.py` — no new settings needed
  - Any `memory/`, `safety/`, or `conversation/` modules beyond session_bootstrap
  - `backend/app/models.py` — no changes to base models

### Technical Requirements

- Payment confirmation must be idempotent on `invoice_payload` — duplicate `successful_payment` updates must not corrupt state. [Source: architecture.md#idempotency-requirements]
- Access upgrade and intent completion must happen in a single DB transaction. [Source: architecture.md#payment-security-boundary]
- Failure must be observable (ops signal) and user-visible (calm message). [Source: architecture.md#operational-signal-expectations]
- Provider-specific details (extracting fields from `successful_payment` dict) stay in `session_bootstrap` routing; billing service receives clean parameters. [Source: architecture.md#adapter-boundaries]
- Billing logic stays in `billing/`; `session_bootstrap.py` is a caller only. [Source: architecture.md#domain-boundaries]
- Unconfirmed or failed transactions must NOT change access state. [Source: epics.md#story-44]

### Architecture Compliance

- `billing/` owns payment state, purchase intents, and premium access logic. `conversation/session_bootstrap.py` only calls billing service functions and translates Telegram-specific update format. [Source: architecture.md#domain-boundaries]
- Repositories own persistence access; services own business rules. [Source: architecture.md#layer-boundaries-within-a-domain]
- `snake_case` for all DB columns, signal types, JSON fields. UTC timestamps with `DateTime(timezone=True)`. [Source: architecture.md#naming-patterns]
- Logging: emit `telegram_user_id` for ops tracing but never paired with conversation content. [Source: architecture.md#logging-pattern]
- Event names as domain facts: signal types like `"billing_payment_confirmation_failed"`, `"billing_payment_intent_not_found"`. [Source: architecture.md#async-internal-event-naming]

### Library / Framework Requirements

- FastAPI `0.114.x`, SQLModel `0.0.21`, Pydantic v2 — no new dependencies needed. [Source: backend/pyproject.toml]
- No external payment SDK needed — Telegram Stars confirmation comes through the regular Telegram webhook.
- Use `_build_response` from session_bootstrap for all response construction. [Source: session_bootstrap.py]
- Use `record_retryable_signal` from `app.ops.signals` for failure observability. [Source: backend/app/ops/signals.py]
- Use existing `get_or_create_user_access_state` from `billing/repository.py`. [Source: billing/repository.py]

### Testing Requirements

- Test commands (run from `backend/`):
  ```
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run alembic upgrade heads
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests/ -q
  uv run ruff check --fix app tests
  uv run mypy app tests
  ```
- Coverage: payment confirmation happy path, idempotency on duplicate events, orphan payment handling, DB failure path, paywall bypass for premium, paywall regression for free tier.
- Follow existing test patterns in `backend/tests/billing/test_payment_initiation.py` and `test_paywall_gate.py`.

### References

- Story source and AC: [Source: planning-artifacts/epics.md#story-44]
- Product requirements FR24, FR41: [Source: planning-artifacts/prd.md]
- Architecture idempotency requirements: [Source: planning-artifacts/architecture.md#idempotency-requirements]
- Architecture payment security boundary: [Source: planning-artifacts/architecture.md#payment-security-boundary]
- Architecture domain boundaries: [Source: planning-artifacts/architecture.md#domain-boundaries]
- Architecture operational signal expectations: [Source: planning-artifacts/architecture.md#operational-signal-expectations]
- UX feedback patterns (payment confirmation): [Source: planning-artifacts/ux-design-specification.md#feedback-patterns]
- UX premium gate prompt states: [Source: planning-artifacts/ux-design-specification.md#premium-gate-prompt]
- Story 4.3 implementation and forward-compatibility notes: [Source: implementation-artifacts/4-3-starting-a-supported-payment-flow-for-premium-access.md]
- Live billing service: [Source: backend/app/billing/service.py]
- Live billing models (UserAccessState, PurchaseIntent): [Source: backend/app/billing/models.py]
- Live billing repository: [Source: backend/app/billing/repository.py]
- Live session_bootstrap (handle_session_entry, _build_response, paywall gate): [Source: backend/app/conversation/session_bootstrap.py]
- Live ops signals: [Source: backend/app/ops/signals.py]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

- Story auto-selected from sprint-status.yaml: first backlog story is `4-4-handling-payment-events-and-updating-access-state`.
- Epic 4 status already `in-progress` — no update needed.
- Loaded Epic 4 from epics.md — full story 4.4 acceptance criteria and cross-story context (4.5 status viewing, 4.6 cancellation, 4.7 continuity are out of scope).
- Loaded Story 4.3 implementation artifact — confirmed PurchaseIntent model state: `status` field with values `"pending"`, `"completed"`, `"failed"`; `provider_payment_charge_id` nullable. Confirmed Telegram Stars flow: sendInvoice → pre_checkout → successful_payment. Confirmed invoice_payload re-subscription limitation documented in code review.
- Loaded live billing module: models.py (UserAccessState with access_tier field, PurchaseIntent with all needed fields), repository.py (6 existing functions), service.py (5 existing functions including get_or_create_purchase_intent), prompts.py (3 existing constants), api.py (webhook stub for future ЮKassa).
- Loaded session_bootstrap.py — confirmed handle_session_entry routing: pre_checkout_query → callback_query (pay:stars, mode selection) → message. Confirmed paywall gate at lines ~305-335: checks is_free_eligible but NOT access_tier. Confirmed _build_response supports messages, signals, inline_keyboard.
- Loaded architecture.md — confirmed idempotency requirements, payment security boundary, domain boundaries, adapter boundaries, operational signal expectations.
- Loaded ux-design-specification.md — confirmed feedback patterns: payment confirmation should be one line, calm, understated. Premium Gate Prompt states include "payment success".
- Loaded conftest.py — confirmed PurchaseIntent cleanup in session fixture teardown.
- Confirmed no git repository (workspace is not a Git repository).

### Completion Notes List
- Implemented `get_purchase_intent_by_payload`, `complete_purchase_intent`, and `upgrade_access_tier` in `billing/repository.py`.
- Implemented `confirm_payment_and_upgrade` in `billing/service.py` to handle normal, idempotent, and orphan payment flows with transactional boundaries.
- Added user-facing prompts `PAYMENT_SUCCESS_MESSAGE` and `PAYMENT_CONFIRMATION_ERROR_MESSAGE`.
- Updated webhook entry flow in `session_bootstrap.py` to route `successful_payment` Telegram messages natively.
- Modified the access gate logic in `_handle_message` to completely bypass the paywall for users where `access_tier == "premium"`.
- Wrote extensive tests inside `tests/billing/test_payment_confirmation_repo.py` and `tests/billing/test_payment_confirmation.py`.
- Ran linters and type verifications, passing successfully. 

### File List
- `backend/app/billing/repository.py` (modified)
- `backend/app/billing/service.py` (modified)
- `backend/app/billing/prompts.py` (modified)
- `backend/app/conversation/session_bootstrap.py` (modified)
- `backend/tests/billing/test_payment_confirmation.py` (added)
- `backend/tests/billing/test_payment_confirmation_repo.py` (added)

## Change Log
- Implemented successful payment confirmation and upgrade routing via Telegram webhook
