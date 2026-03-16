# Story 4.1: Ограниченный free usage и учет usage threshold

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь, который только начинает пользоваться продуктом,
I want получить ограниченный бесплатный доступ до paywall,
so that я могу сначала почувствовать ценность продукта, прежде чем принимать решение об оплате.

## Acceptance Criteria

1. When a new user starts their first eligible reflective session, the system records that session's completion against a per-user free-usage counter, and the user is not interrupted or paused while still within the configured free allowance. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-41-ограниченный-free-usage-и-учет-usage-threshold]
2. When a session reaches `status = "completed"` via the normal closure path, only that session counts as one unit against the free allowance, and accidental retries, duplicate events, or abnormal terminations do not falsely consume free quota. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-41]
3. When the user's free-usage counter reaches the configured threshold, the access state is updated so the user is no longer eligible for unrestricted free continuation, and the product is ready to transition to the next premium-boundary step without silent inconsistency. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-41]
4. When billing increment or threshold evaluation fails, the failure becomes observable via an ops signal, and the user does not lose access silently due to a counting error. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-41] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
5. When the free-usage model is inspected at the access-control layer, the usage and threshold state are explicit and reviewable, and billing/accounting logic does not bleed into the conversation core. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-41] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

## Tasks / Subtasks

- [x] Introduce `UserAccessState` model and `free_session_events` table for idempotent usage tracking (AC: 1, 2, 3, 5)
  - [x] Add `UserAccessState` SQLModel table in `backend/app/billing/models.py` with fields: `telegram_user_id` (BigInteger, unique index), `access_tier` (str, default `"free"`), `free_sessions_used` (int, default 0), `threshold_reached_at` (DateTime nullable), `created_at`, `updated_at`. Use `snake_case` per architecture naming rules.
  - [x] Add `FreeSessionEvent` SQLModel table in `backend/app/billing/models.py` to record which `session_id` values have already been counted (idempotency key). Fields: `id` (UUID PK), `telegram_user_id` (BigInteger, index), `session_id` (UUID, unique index — prevents double-counting), `recorded_at` (DateTime).
  - [x] Write Alembic migration under `backend/app/alembic/versions/` for both new tables. Follow the existing migration chain — check the latest head first.
- [x] Implement `billing/repository.py` for persistence access (AC: 2, 3, 5)
  - [x] `get_or_create_user_access_state(session, telegram_user_id)` — return existing or create new `UserAccessState` with `access_tier = "free"` and `free_sessions_used = 0`.
  - [x] `session_event_exists(session, session_id)` — return bool: True if `FreeSessionEvent` with this `session_id` already recorded.
  - [x] `record_free_session_event(session, telegram_user_id, session_id)` — insert `FreeSessionEvent` row.
  - [x] `increment_free_sessions_used(session, user_access_state)` — increment `free_sessions_used` by 1, update `updated_at`.
  - [x] `mark_threshold_reached(session, user_access_state)` — set `threshold_reached_at = now(UTC)`, keep `access_tier = "free"` (paywall framing is a Story 4.2 concern).
- [x] Implement `billing/service.py` for business rules (AC: 1, 2, 3, 4, 5)
  - [x] `record_eligible_session_completion(session, telegram_user_id, session_id)` — the primary entry point. Steps: (a) check `session_event_exists` for idempotency, return early if already counted; (b) call `get_or_create_user_access_state`; (c) `record_free_session_event`; (d) `increment_free_sessions_used`; (e) check if `free_sessions_used >= settings.FREE_SESSION_THRESHOLD`; (f) if threshold reached, call `mark_threshold_reached`. Wrap the entire operation in a single DB transaction so partial failure is detectable.
  - [x] `get_user_access_state(session, telegram_user_id)` — return current `UserAccessState` (or synthesized default for users with no record yet).
  - [x] `is_free_eligible(user_access_state)` — return True if `threshold_reached_at is None` (i.e., threshold not yet reached). Story 4.1 scope: only the counting side; Story 4.2 uses this to gate access.
- [x] Wire billing service into session closure path in `session_bootstrap.py` (AC: 1, 2, 4, 5)
  - [x] After `active_session.status = "completed"` is set (the closure branch, ~line 429), call `billing_service.record_eligible_session_completion(db, active_session.telegram_user_id, active_session.id)`. Import via `from app.billing.service import record_eligible_session_completion`.
  - [x] Wrap the call in a `try/except`. On failure: call `record_retryable_signal` from `app.ops.signals` with a new signal type `"billing_free_usage_record_failed"` and `retryable=True`. Do NOT re-raise — the session closure must still succeed; billing failure must not block the user or corrupt session state.
  - [x] Only call on the closure branch (`session_closure` action). Do not call on crisis-active sessions or non-completing sessions — the trigger condition is already gated by the `status = "completed"` assignment.
- [x] Add `FREE_SESSION_THRESHOLD` to app settings (AC: 3, 5)
  - [x] Add `FREE_SESSION_THRESHOLD: int = 3` to `backend/app/core/config.py` `Settings` class (or the appropriate settings model). Value 3 is the MVP default; operator can override via env var.
  - [x] Document the setting with a short inline comment explaining it is the number of completed reflective sessions before premium boundary is considered.
- [x] Write tests (AC: 1, 2, 3, 4, 5)
  - [x] Unit tests in `backend/tests/` for `billing/service.py`: test idempotency (second call with same session_id skips increment), test counter reaches threshold and marks `threshold_reached_at`, test failure path records ops signal and does not corrupt session state.
  - [x] Route-level tests in `backend/tests/api/routes/test_telegram_session_entry.py` or a dedicated `test_billing_free_usage.py`: test that a session closure triggers the free-usage path; test that a non-closing session turn does not.
  - [x] Verify that `is_free_eligible` returns True before threshold, False after.
  - [x] Run `pytest`, `ruff`, and `mypy` within `backend/`.

## Dev Notes

- The billing module exists as a stub: `backend/app/billing/api.py` contains only a `/billing/webhook` foundation seam. `billing/models.py`, `billing/service.py`, `billing/repository.py`, and `billing/events.py` do not yet exist — all must be created fresh. [Source: /home/erda/Музыка/goals/backend/app/billing/api.py]
- There is no `TelegramUser` table in the live data model. User identity is tracked solely via `telegram_user_id` (BigInteger) stored on `TelegramSession` and related records. `UserAccessState` must be keyed by `telegram_user_id` as the sole user-level anchor. [Source: /home/erda/Музыка/goals/backend/app/models.py]
- Session closure happens in `session_bootstrap.py` at the branch where `_should_close_session(active_session)` is True and `active_session.status = "completed"` is set (~line 429). This is the only correct trigger point for free-usage counting. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- The `_should_close_session` guard uses `settings.CONVERSATION_CLOSURE_MIN_TURN_COUNT` (~line 506). Crisis-active and step_down_pending sessions can still close if turn count is high enough, so the billing call must not discriminate on crisis state — the `status = "completed"` guard is sufficient.
- Session IDs (`active_session.id`, UUID) are already unique per session, making them a safe idempotency key for `FreeSessionEvent`. [Source: /home/erda/Музыка/goals/backend/app/models.py]
- For retryable failure ops signals, follow the pattern in `backend/app/ops/signals.py` and `record_retryable_signal`. Use `"billing_free_usage_record_failed"` as `signal_type`. [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py]
- SQLModel 0.0.21 is in use. Use `SQLModel, table=True` for DB models. Use `Field(sa_type=BigInteger())` for `telegram_user_id`, `Field(sa_type=DateTime(timezone=True))` for timestamps, following the pattern in `models.py`. [Source: /home/erda/Музыка/goals/backend/app/models.py]
- There is no event bus or background job machinery needed for Story 4.1. The billing call is a synchronous in-request operation (similar to how `schedule_session_summary_generation` is called in-request). [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- No project-context.md exists in this workspace — guidance is based on live seams and planning artifacts only.
- Git history unavailable (`/home/erda/Музыка/goals` is not a Git repository in this workspace).

### Project Structure Notes

- Respect the live backend layout under `backend/app/`, not the aspirational `src/goals/...` structure from planning docs.
- New files to create:
  - `backend/app/billing/models.py` — `UserAccessState` and `FreeSessionEvent` SQLModel tables
  - `backend/app/billing/repository.py` — persistence access functions
  - `backend/app/billing/service.py` — business rules for free-usage tracking
  - new Alembic migration in `backend/app/alembic/versions/`
- Files to modify:
  - `backend/app/core/config.py` — add `FREE_SESSION_THRESHOLD`
  - `backend/app/conversation/session_bootstrap.py` — wire billing call at session closure
- Test files:
  - new `backend/tests/billing/test_free_usage.py` (or `test_billing_service.py`)
  - optionally extend `backend/tests/api/routes/test_telegram_session_entry.py`
- Do NOT modify:
  - `backend/app/billing/api.py` — leave the webhook stub untouched (Story 4.4 concern)
  - anything in `conversation/`, `safety/`, or `memory/` beyond the single closure hook
- `billing/` module boundary owns all access state — conversation core must not contain free-usage business logic.

### Technical Requirements

- `UserAccessState` must be a first-class DB table, not a field on `TelegramSession`. Billing/accounting logic must remain in the `billing/` module boundary. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#domain-boundaries]
- Idempotency is mandatory: `FreeSessionEvent` with a unique constraint on `session_id` ensures that re-delivery or retry of the billing call on the same session does not double-count. Uniqueness must be enforced at the DB level, not only in application code. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-41] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#idempotency-as-a-state-integrity-rule]
- Failure handling must be observable. If `record_eligible_session_completion` raises, record a retryable signal. Do not let billing failure silently drop the usage event OR silently block session completion. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#operational-signal-expectations]
- `FREE_SESSION_THRESHOLD` must be externally configurable via environment variable so the product team can tune it without a code deploy. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Inference: configurable threshold is a product requirement]
- The access state model must remain reviewable: `free_sessions_used`, `threshold_reached_at`, and `access_tier` are all persisted fields, not derived at runtime. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-41]
- Do not gate the user's current session behind access checks in this story. Story 4.1 is purely about counting and state update. Paywall enforcement and session blocking are Story 4.2's concern.

### Architecture Compliance

- `billing/` owns all payment state and premium access per the architecture. Conversation module must not own free-usage counting logic — only trigger the billing service call. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#domain-boundaries]
- Repositories own persistence access; services own business rules. Follow the layer boundary: `billing/repository.py` does DB reads/writes, `billing/service.py` contains the counting logic and threshold evaluation. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#layer-boundaries-within-a-domain]
- Sensitive access policy: `UserAccessState` does not contain transcript content. Logging must not emit `telegram_user_id` paired with sensitive context — log only identifiers and operational signals. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#logging-pattern]
- Use dotted lowercase event names for any async internal events if introduced: e.g., `billing.free_session_recorded`, `billing.threshold_reached`. For Story 4.1 the billing call is synchronous, so no event bus is needed yet. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#asyncinternal-event-naming]
- All timestamps in UTC, stored with `DateTime(timezone=True)`. Follow existing models in `models.py`. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#date-and-time-format]
- `snake_case` for all DB columns, JSON fields, and Python identifiers. Plural table names (`user_access_states`, `free_session_events`). [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#naming-patterns]

### Library / Framework Requirements

- Stay within the current backend stack: FastAPI `0.114.x`, SQLModel `0.0.21`, Pydantic v2, Alembic `1.12.x`, python-telegram-bot `21.x`. Do not introduce new dependencies for this story. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- Use `SQLModel, table=True` pattern matching existing models in `backend/app/models.py`. Use `Field(sa_type=...)` for non-default SA column types.
- Alembic migration must follow the existing migration chain. Run `alembic heads` before generating a new revision to find the correct `down_revision`. [Source: /home/erda/Музыка/goals/backend/app/alembic/versions/]
- For `UniqueConstraint` in SQLModel, follow the `__table_args__` pattern already used in `SessionSummary` and `ProfileFact`. [Source: /home/erda/Музыка/goals/backend/app/models.py]

### File Structure Requirements

- New files:
  - `backend/app/billing/models.py`
  - `backend/app/billing/repository.py`
  - `backend/app/billing/service.py`
  - `backend/app/alembic/versions/<hash>_add_user_access_state_and_free_session_events.py`
  - `backend/tests/billing/__init__.py`
  - `backend/tests/billing/test_free_usage.py`
- Modified files:
  - `backend/app/core/config.py` (add `FREE_SESSION_THRESHOLD`)
  - `backend/app/conversation/session_bootstrap.py` (billing hook at closure)
- Untouched files (confirm before editing):
  - `backend/app/billing/api.py` — stub must remain intact
  - `backend/app/billing/__init__.py` — may add public exports if needed

### Testing Requirements

- Test idempotency: calling `record_eligible_session_completion` twice with the same `session_id` must result in `free_sessions_used == 1` (not 2).
- Test counter increments correctly from 0 to threshold and `threshold_reached_at` is set only at threshold crossing.
- Test `is_free_eligible` returns True before threshold, False after `threshold_reached_at` is set.
- Test that billing failure (e.g., DB error in billing call) causes `record_retryable_signal` to be called with `"billing_free_usage_record_failed"` and does NOT raise to the session closure path.
- Test that a session closure turn triggers the billing path; a non-closing turn (turn_count < threshold) does not.
- Preserve the full backend quality bar: `pytest`, `ruff check`, `mypy`.
- Run commands from `backend/` directory with DB env set:
  ```
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run alembic upgrade heads
  POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests/ -q
  uv run ruff check --fix app tests
  uv run mypy app tests
  ```

### References

- Story source and acceptance criteria: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#epic-4-монетизация-доступ-и-continuity-based-premium]
- Product requirement FR21: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
- Architecture domain boundaries and billing module: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#domain-boundaries]
- Architecture idempotency rule: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#idempotency-as-a-state-integrity-rule]
- Architecture naming patterns: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#naming-patterns]
- Architecture operational signal expectations: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#operational-signal-expectations]
- Live billing stub: [Source: /home/erda/Музыка/goals/backend/app/billing/api.py]
- Live session closure trigger: [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Live ops signals seam: [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py]
- Live model patterns: [Source: /home/erda/Музыка/goals/backend/app/models.py]
- Existing billing route test: [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_billing_routes.py]
- Backend dependency baseline: [Source: /home/erda/Музыка/goals/backend/pyproject.toml]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Story auto-selected from `/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog story in order: `4-1-limited-free-usage-and-usage-threshold-tracking`.
- Loaded and followed `_bmad/core/tasks/workflow.xml` with workflow config `_bmad/bmm/workflows/4-implementation/create-story/workflow.yaml`.
- Analyzed planning artifacts: `epics.md` (epic 4 section), `architecture.md` (billing domain, naming, idempotency, data architecture sections).
- Inspected live backend seams: `backend/app/billing/api.py`, `backend/app/conversation/session_bootstrap.py`, `backend/app/models.py`, `backend/app/ops/signals.py`, `backend/tests/api/routes/test_billing_routes.py`.
- Confirmed no `TelegramUser` table exists — user identity anchored solely on `telegram_user_id`.
- Confirmed session closure trigger at `active_session.status = "completed"` in `session_bootstrap.py` line ~429.
- Confirmed no git history available (workspace is not a Git repository).
- Confirmed `billing/models.py`, `billing/service.py`, `billing/repository.py` do not yet exist — all new.
- No previous epic-4 story exists to carry forward learnings.
- Epic-4 status updated from `backlog` to `in-progress` in `sprint-status.yaml`.

### Completion Notes List

- Ultimate context engine analysis completed — comprehensive developer guide created.
- Story 4.1 is intentionally scoped to tracking and counting only. It does NOT implement paywall display (Story 4.2), payment flow (Story 4.3), or payment event handling (Story 4.4).
- The main implementation risk is maintaining the billing/conversation boundary: billing logic must be called from session_bootstrap but must not live there.
- `FreeSessionEvent` with a DB-level unique constraint on `session_id` is the correct idempotency mechanism — application-level checks alone are insufficient under concurrent conditions.
- `threshold_reached_at` is set at the moment the threshold is crossed; `access_tier` remains `"free"` at this stage — access tier upgrade or paywall enforcement is deliberately deferred to Story 4.2.
- Failure path must be observable but non-blocking: session closure proceeds regardless of billing errors.
- Implementation complete: all 5 tasks checked, 11 tests pass (226 total, 2 pre-existing failures in crisis step-down tests unrelated to this story).
- Note: `record_retryable_signal` uses the `SummaryGenerationSignal` table (unique constraint on session_id) for all signal types. Billing failure signals use the same table, which is a design trade-off of the current ops infrastructure. Story 4.4+ may want to revisit this.
- mypy: 8 pre-existing errors in `app/models.py` (BigInteger Field overload — not introduced by this story); billing/models.py adds 0 new errors with `# type: ignore[call-overload]` matching the project's established pattern.
- ruff: auto-fixed 2 minor issues, final check clean.

### File List

- _bmad-output/implementation-artifacts/4-1-limited-free-usage-and-usage-threshold-tracking.md (modified)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified)
- backend/app/billing/models.py (new)
- backend/app/billing/repository.py (new)
- backend/app/billing/service.py (new)
- backend/app/alembic/versions/f1a2b3c4d5e6_add_user_access_state_and_free_session_events.py (new)
- backend/app/core/config.py (modified)
- backend/app/conversation/session_bootstrap.py (modified)
- backend/tests/billing/__init__.py (new)
- backend/tests/billing/test_free_usage.py (new)
- backend/tests/conftest.py (modified)

## Change Log

- 2026-03-14: Code review — fixed conftest.py session teardown to include PurchaseIntent cleanup (H1, cross-story with 4.3).
- 2026-03-14: Implemented Story 4.1 — free-usage tracking billing module. Created UserAccessState and FreeSessionEvent tables with Alembic migration, billing repository and service layers, wired into session closure path with non-blocking failure handling. 11 new tests added, all passing.
