# Story 4.2: Paywall после felt value с continuity-based framing

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь, который уже получил пользу от первых сессий,
I want увидеть paywall в понятный и ненавязчивый момент,
So that я понимаю, за что именно предлагается платить и не чувствую, что меня прервали слишком рано.

## Acceptance Criteria

1. When the user has reached the configured free-usage threshold (`threshold_reached_at is not None` on their `UserAccessState`) and sends a new message outside of an active crisis session, the product shows the premium boundary/paywall message instead of continuing the reflective conversation. [Source: epics.md#story-42]
2. When the paywall message is shown in Telegram, it frames premium access around continuity, remembered context, and reduced emotional setup cost — not around a raw message-limit count or session number. [Source: epics.md#story-42, ux-design-specification.md#premium-boundary-pattern]
3. When the paywall message is sent, it remains calm, respectful, and readable, and does not use a manipulative or cold monetization tone. [Source: epics.md#story-42, ux-design-specification.md#premium-gate-prompt]
4. When the paywall is shown, the user understands what is limited in free mode and what value paid access unlocks — sufficient for an informed choice. [Source: epics.md#story-42]
5. When the user is in an active crisis session (`crisis_state in ("crisis_active", "step_down_pending")`), the paywall check is bypassed entirely and crisis routing continues normally. [Source: epics.md#story-42 — access limits must never interrupt safety flows]
6. When the paywall check or access state load fails, the failure becomes observable via an ops signal, and the system falls through to normal conversation flow (fail-open, not fail-closed). [Source: epics.md#story-42, architecture.md#operational-signal-expectations]
7. When paywall rendering or access-state transition is contradictory, the user does not receive conflicting messages about whether their access is free or paid. [Source: epics.md#story-42]

## Tasks / Subtasks

- [x] Create `billing/prompts.py` with paywall message constant (AC: 2, 3, 4)
  - [x] Create `backend/app/billing/prompts.py`. Add `PAYWALL_MESSAGE: str` constant written in Russian. Tone and content requirements:
    - Acknowledge prior sessions without citing a raw number ("Вы уже несколько раз работали с этим инструментом")
    - Explain what premium unlocks: preserved context between sessions, reduced emotional setup cost, continued momentum
    - Include placeholder CTA text without payment links (Story 4.3 will wire the button): end with "Чтобы продолжить — оформите premium доступ."
    - Do NOT use manipulative framing ("вы потеряете всё"), cold gating language, or session-count metrics
    - Style: `Continuity Premium` framing from UX spec — calm, warm, informative

- [x] Add `build_paywall_response()` to `billing/service.py` (AC: 2, 3)
  - [x] Import `PAYWALL_MESSAGE` from `app.billing.prompts`
  - [x] Add function: `def build_paywall_response(user_access_state: UserAccessState) -> str: return PAYWALL_MESSAGE`
  - [x] Keep function signature accepting `user_access_state` so Story 4.3 can extend it with user-specific context (e.g., active subscription state)

- [x] Add billing gate check in `_handle_message` in `session_bootstrap.py` (AC: 1, 5, 6, 7)
  - [x] Extend existing import: `from app.billing.service import record_eligible_session_completion, get_user_access_state, is_free_eligible, build_paywall_response`
  - [x] In `_handle_message`, immediately after `active_session = _get_or_create_active_session(...)` and BEFORE the safety evaluation block, insert the billing gate:
    ```python
    # Billing gate: skip for crisis sessions, check eligibility for normal flow
    if active_session.crisis_state not in ("crisis_active", "step_down_pending"):
        try:
            _user_access_state = get_user_access_state(session, active_session.telegram_user_id)
            if not is_free_eligible(_user_access_state):
                paywall_text = build_paywall_response(_user_access_state)
                _save_session(session, active_session)
                return _build_response(
                    action="paywall_gate",
                    session_record=active_session,
                    message_texts=[paywall_text],
                    extra_signals=("typing", "paywall_shown"),
                )
        except Exception:
            logger.exception(
                "Billing access check failed for telegram_user_id=%s",
                active_session.telegram_user_id,
            )
            record_retryable_signal(
                session,
                session_id=active_session.id,
                telegram_user_id=active_session.telegram_user_id,
                signal_type="billing_access_check_failed",
                error_type="BillingAccessCheckError",
                error_message="Billing eligibility check failed; falling through to normal flow.",
                suggested_action="review_billing_access_check_failure",
                retry_payload={},
                failure_stage="billing",
            )
            # Fail-open: prefer granting access on uncertainty over incorrectly blocking the user
    ```
  - [x] Confirm `record_retryable_signal` is already imported (it is — used in safety error handling). No new imports needed for ops signals.

- [x] Write tests (AC: 1, 5, 6)
  - [x] Create `backend/tests/billing/test_paywall_gate.py` (or extend `test_free_usage.py`)
  - [x] Test: user with `threshold_reached_at` set sends a message → response `action == "paywall_gate"` and `"paywall_shown"` in signals
  - [x] Test: user with `threshold_reached_at` set + `crisis_state="crisis_active"` → paywall bypassed, response is NOT `"paywall_gate"`
  - [x] Test: user with `threshold_reached_at = None` → paywall not shown, normal flow proceeds
  - [x] Test: `get_user_access_state` raises → `"billing_access_check_failed"` signal recorded, response is NOT `"paywall_gate"` (fall-through)
  - [x] Test: `PAYWALL_MESSAGE` does not contain standalone digit strings representing session counts (regex check as a contract guard)
  - [x] Run `pytest`, `ruff check --fix`, `mypy` from `backend/`

## Dev Notes

- **Existing billing seam — use, don't rewrite**: `billing/service.py` already has `get_user_access_state(session, telegram_user_id)` and `is_free_eligible(user_access_state)` from Story 4.1. Import and call them directly. [Source: backend/app/billing/service.py]
- **Existing import in session_bootstrap**: `from app.billing.service import record_eligible_session_completion` is already at the top of the file. Extend this single import line to add the new symbols. [Source: backend/app/conversation/session_bootstrap.py]
- **Placement of billing gate — before safety eval, after session load**: `active_session.crisis_state` is loaded from DB in `_get_or_create_active_session`, so crisis state is known before any LLM call. Placing the gate here skips the expensive safety evaluation for paywall users while still honoring crisis bypass. [Source: session_bootstrap.py structure — `_get_or_create_active_session` precedes `evaluate_incoming_message_safety`]
- **Crisis bypass guard**: `crisis_state in ("crisis_active", "step_down_pending")` matches the existing guard used later in `_handle_message` for `should_route_to_crisis`. Use the same literals. [Source: session_bootstrap.py ~line 230]
- **Fail-open policy**: When `get_user_access_state` raises, log, record signal, and fall through to normal conversation. Paywall must never become an unintended access blocker due to a billing infrastructure failure. Billing uncertainty resolves in the user's favor. [Source: epics.md#story-42]
- **`_build_response` and `_save_session`**: Use these existing helpers for the early return. Pattern matches the crisis routing early returns already in the file (e.g., `safety_check_error` branch). Do NOT call `session.commit()` directly. [Source: session_bootstrap.py ~line 676 and safety error branches]
- **No DB changes**: No new tables, no Alembic migration. `UserAccessState.threshold_reached_at` from Story 4.1 is the sole signal. [Source: backend/app/billing/models.py]
- **No payment links in this story**: The paywall message is text-only. Story 4.3 will extend `build_paywall_response()` to add inline keyboard buttons for payment initiation. Signature is designed to be forward-compatible. [Source: epics.md#story-43]
- **Signal observability**: `"paywall_shown"` in `extra_signals` gives downstream observability into paywall impressions without needing a dedicated table. `"billing_access_check_failed"` follows existing signal naming patterns. [Source: backend/app/ops/signals.py, architecture.md#operational-signal-expectations]
- **User identity**: Get `telegram_user_id` from `active_session.telegram_user_id`. There is no `TelegramUser` table. [Source: 4-1 story dev notes, backend/app/models.py]
- **2 pre-existing test failures**: crisis step-down tests were already failing before Story 4.1 — not related to billing. Do not investigate them. [Source: 4-1 story completion notes]
- **mypy**: Expect the same `# type: ignore[call-overload]` pattern if touching `BigInteger` fields — but Story 4.2 adds no new models, so this should not arise.

### Project Structure Notes

- Live backend layout: `backend/app/`, not aspirational `src/goals/...`
- New file:
  - `backend/app/billing/prompts.py` — `PAYWALL_MESSAGE` constant
- Modified files:
  - `backend/app/billing/service.py` — add `build_paywall_response()`
  - `backend/app/conversation/session_bootstrap.py` — billing gate in `_handle_message`, extended import
- Test file:
  - `backend/tests/billing/test_paywall_gate.py` (new, or extend `test_free_usage.py`)
- Do NOT modify:
  - `backend/app/billing/models.py` — no schema changes
  - `backend/app/billing/repository.py` — no new queries
  - `backend/app/billing/api.py` — leave webhook stub for Story 4.4
  - Any `memory/`, `safety/`, or other modules

### Technical Requirements

- Paywall check must be bypassed for crisis sessions — safety is always prioritized over billing. [Source: epics.md#story-42]
- Access business logic stays in `billing/`; `session_bootstrap.py` only calls into it. [Source: architecture.md#domain-boundaries]
- Billing check failure must be observable (ops signal) and non-blocking (fail-open). [Source: architecture.md#operational-signal-expectations]
- Paywall message must NOT mention raw session counts — frame around continuity value. [Source: ux-design-specification.md#premium-boundary-pattern]
- Paywall message language: Russian. [Source: config.yaml — document_output_language: Русский]

### Architecture Compliance

- `billing/` owns access state and premium boundary; `conversation/session_bootstrap.py` is a caller only. [Source: architecture.md#domain-boundaries]
- No DB access added to session_bootstrap beyond what already exists. [Source: architecture.md#layer-boundaries-within-a-domain]
- `snake_case` for all signal_type strings. UTC timestamps. [Source: architecture.md#naming-patterns]
- Logging: emit `telegram_user_id` for ops tracing but never paired with conversation content. [Source: architecture.md#logging-pattern]

### Library / Framework Requirements

- FastAPI `0.114.x`, SQLModel `0.0.21`, Pydantic v2 — no new dependencies. [Source: backend/pyproject.toml]
- Use `_build_response` from session_bootstrap — no parallel response builders. [Source: session_bootstrap.py]
- Use `record_retryable_signal` from `app.ops.signals` for all ops observability. [Source: backend/app/ops/signals.py]

### Testing Requirements

- Test commands (run from `backend/`):
  ```
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests/ -q
  uv run ruff check --fix app tests
  uv run mypy app tests
  ```
- Gate condition coverage: threshold reached → paywall; threshold reached + crisis → no paywall; threshold not reached → no paywall; billing failure → fall-through.
- Paywall message contract: no raw digit-only session-count strings in `PAYWALL_MESSAGE`.

### References

- Story source and AC: [Source: planning-artifacts/epics.md#epic-4-story-42]
- UX Premium Gate Prompt component spec: [Source: planning-artifacts/ux-design-specification.md#premium-gate-prompt]
- UX Premium Boundary Pattern rules: [Source: planning-artifacts/ux-design-specification.md#premium-boundary-pattern]
- UX Continuity Premium framing: [Source: planning-artifacts/ux-design-specification.md#conversational-style-direction]
- Architecture domain boundaries: [Source: planning-artifacts/architecture.md#domain-boundaries]
- Architecture operational signal expectations: [Source: planning-artifacts/architecture.md#operational-signal-expectations]
- Existing billing service (is_free_eligible, get_user_access_state): [Source: backend/app/billing/service.py]
- Live `_handle_message` function: [Source: backend/app/conversation/session_bootstrap.py]
- Live ops signals: [Source: backend/app/ops/signals.py]
- Story 4.1 learnings and billing module patterns: [Source: implementation-artifacts/4-1-limited-free-usage-and-usage-threshold-tracking.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Story auto-selected from sprint-status.yaml: first backlog story is `4-2-paywall-after-felt-value-with-continuity-based-framing`.
- Loaded Epic 4 from epics.md — full story 4.2 acceptance criteria and cross-story context (4.3 payment flow is out of scope for this story).
- Loaded Story 4.1 implementation artifact — confirmed billing module state: UserAccessState, FreeSessionEvent, service.py with get_user_access_state and is_free_eligible, config FREE_SESSION_THRESHOLD=3.
- Analyzed live backend: billing/service.py, billing/models.py, billing/repository.py — no changes needed to models or repository.
- Analyzed session_bootstrap.py — confirmed _handle_message structure, _get_or_create_active_session placement, crisis routing guards, _build_response and _save_session helpers, existing billing import.
- Loaded ux-design-specification.md — Premium Gate Prompt component, Premium Boundary Pattern rules, Continuity Premium framing language.
- Confirmed: no new DB tables or Alembic migration needed.
- Confirmed: fail-open policy is correct per epics spec ("failure becomes observable, user must not get contradictory messages").
- Confirmed: paywall message must be Russian, continuity-framed, no raw session counts.

### Completion Notes List

- Implemented standard paywall response logic with continuity-framed language. No exact numbers or countdowns included.
- Connected the billing paywall gate in `session_bootstrap.py`. Gate is performed immediately after assigning `active_session.last_user_message` ensuring the state correctly records user input, but before any LLM evaluation takes place.
- Assured safety priority: The paywall check verifies the session's internal `crisis_state` before looking at free usages, skipping the gate if safety routing applies.
- Successfully verified tests logic. Fixed a minor attribute issue with `SummaryGenerationSignal` tests and correctly imported all symbols.
- Passing `ruff` lints and pre-existing known `mypy` typing errors. 
- **[Review fix]** Added non-hostile fallback line to PAYWALL_MESSAGE per UX spec Premium Gate Prompt and Premium Boundary Pattern rules.
- **[Review fix]** Added `mock_safety.assert_not_called()` assertion in paywall trigger test to verify safety evaluation is skipped.
- **[Review fix]** All Tasks/Subtasks checkboxes marked [x].
- **[Review fix]** Added blank line separator after billing gate block for readability.

### File List

- `backend/app/billing/prompts.py` (New)
- `backend/app/billing/service.py` (Modified)
- `backend/app/conversation/session_bootstrap.py` (Modified)
- `backend/tests/billing/test_paywall_gate.py` (New)

## Change Log

- 2026-03-14: Implemented Story 4.2. Introduced continuity-framed PAYWALL_MESSAGE. Added billing access gate checking inside the session bootstrap pipeline, successfully prioritizing emergency flows and operating a fail-open pattern. Written all required tests achieving full implementation.
- 2026-03-14: Code review fixes — added fallback path to PAYWALL_MESSAGE, verified safety eval not called on paywall, marked all tasks [x], improved code readability.
