# Story 1.2: Начало сессии через Telegram и мгновенный вход в разговор

Status: done
<!-- Reviewed: 2026-03-11 — all critical/high issues resolved -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь в эмоционально нагруженном состоянии,
I want начать разговор с ботом сразу после входа в Telegram без регистрации и лишних шагов,
so that я могу быстро выговориться и получить первый полезный отклик без дополнительного friction.

## Acceptance Criteria

1. User can start a session in Telegram without separate registration, login, or external onboarding flow, and receives one clear opening prompt inviting free-text description of the situation. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-12-Начало-сессии-через-Telegram-и-мгновенный-вход-в-разговор]
2. When the first free-text user message arrives, the system creates a new session tied to `telegram_user_id` and stores only the minimal session context required to continue the conversation. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-12-Начало-сессии-через-Telegram-и-мгновенный-вход-в-разговор]
3. The happy-path session start remains text-first inside Telegram and does not depend on mandatory inline button clicks. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-12-Начало-сессии-через-Telegram-и-мгновенный-вход-в-разговор]
4. The system emits a typing indicator or equivalent Telegram feedback signal before the first meaningful response and does not block that path on nonessential post-processing. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-12-Начало-сессии-через-Telegram-и-мгновенный-вход-в-разговор]
5. If the first input is empty, too short, or unclear, the bot returns a short clarifying prompt instead of an error, long system message, or advice-first response. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-12-Начало-сессии-через-Telegram-и-мгновенный-вход-в-разговор]

## Tasks / Subtasks

- [x] Introduce a Telegram-first ingress path for session start (AC: 1, 2, 3, 4)
  - [x] Create or activate a dedicated Telegram adapter boundary under the backend modular structure established in Story 1.1.
  - [x] Add an ingress endpoint or handler for Telegram updates that can receive start-of-conversation messages without requiring the web login/user flows.
  - [x] Ensure Telegram ingress is isolated from legacy CRUD-oriented API behavior and becomes the path used for session-start logic.
- [x] Implement no-registration session bootstrap tied to Telegram identity (AC: 1, 2)
  - [x] Resolve the Telegram sender to a stable `telegram_user_id`-based identity model without creating a separate registration/login flow.
  - [x] Create minimal session bootstrap state for a new or returning conversation start.
  - [x] Persist only the minimum context required for immediate conversation continuation; do not introduce full memory/profile domain persistence in this story.
- [x] Implement the opening prompt and first-turn text-first flow (AC: 1, 3, 5)
  - [x] Define the initial Telegram-visible opening prompt for first interaction and long-gap re-entry where appropriate.
  - [x] Keep the session start usable through plain text messages; inline controls may exist later but must not be mandatory in this story.
  - [x] Add short-input / unclear-input handling that returns a compact clarifying prompt instead of advice or failure.
- [x] Add Telegram feedback behavior for first response preparation (AC: 4)
  - [x] Emit typing indicator or equivalent supported Telegram feedback before the first substantive response path.
  - [x] Keep first-turn preparation free of unnecessary post-response work such as summaries, profile enrichment, or premium logic.
  - [x] Make failure to send feedback or start the first turn observable without breaking the entire session bootstrap path.
- [x] Verify startup path and protect against regressions from the existing scaffold (AC: 1, 2, 3, 4, 5)
  - [x] Add/update tests for Telegram session entry happy path, short/unclear input fallback, and session creation tied to `telegram_user_id`.
  - [x] Confirm legacy auth/web routes are not required for the Telegram session-start path.
  - [x] Run backend validation relevant to the touched ingress/session code.

## Dev Notes

- This story depends on the foundation baseline from Story 1.1 and should extend the modular seams created there, not bypass them. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-1-starter-template-telegram-backend.md]
- Product value at this stage is immediate, low-friction arrival inside Telegram. The story is not “build bot infrastructure in the abstract”; it is “make the first session start feel immediate”. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Journey-1-Маша---Primary-User-Success-Path]
- The UX explicitly requires:
  - start with expression, not configuration
  - Telegram-native text-first interaction
  - typing indicators
  - no friction-heavy onboarding
  - no menu-heavy interaction as the primary flow
  These are implementation constraints, not polish. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#Core-User-Experience]
- Do not implement fast/deep mode selection here beyond what is needed to avoid blocking Story 1.3. That belongs to Story 1.3 in the planning breakdown.
- Do not pull in memory continuity, paywall, safety escalation, or summary generation logic into this story except for the minimum seams needed to avoid future rewrites.

### Project Structure Notes

- Existing app runtime entrypoint is [`backend/app/main.py`](/home/erda/Музыка/goals/backend/app/main.py). If Story 1.1 has already introduced a better routing composition, extend that. Otherwise, this story will likely need to adapt `app.include_router(...)` behavior so Telegram ingress becomes an intentional first-class path.
- Existing route aggregator is [`backend/app/api/main.py`](/home/erda/Музыка/goals/backend/app/api/main.py), currently centered on `login`, `users`, `utils`, `items`, and `private`. This is not the desired runtime center for the product. If unchanged, add Telegram routing in a way that clearly signals the future shift away from web-auth CRUD.
- There is already a minimal health-check route at [`backend/app/api/routes/utils.py`](/home/erda/Музыка/goals/backend/app/api/routes/utils.py). Reuse this as evidence that small operational routes already exist; do not reinvent health wiring during session-start work.
- Existing backend tests live under [`backend/tests/`](/home/erda/Музыка/goals/backend/tests). Add new tests adjacent to the real ingress/session behavior rather than hiding them in unrelated legacy test files.
- Current domain models in [`backend/app/models.py`](/home/erda/Музыка/goals/backend/app/models.py) are template-era `User`/`Item` constructs. Avoid extending them as the canonical model for Telegram session start unless Story 1.1 deliberately chose a transitional path. Prefer new product-aligned modules or temporary ingress/session models with clear boundaries.

### References

- Story source and ACs: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Foundation baseline: [1-1-starter-template-telegram-backend.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-1-starter-template-telegram-backend.md)
- Product context and journeys: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Architecture constraints: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- UX constraints: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)

## Developer Context

### Technical Requirements

- Telegram is the only core product surface in MVP. This story should implement session start through Telegram, not through browser-first or REST-auth-first product assumptions. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Technical-Constraints--Dependencies]
- The architecture treats Telegram as an adapter boundary, not the architectural center. That means ingress logic can live in a Telegram-focused adapter/module, but conversation/session logic should not be hardcoded into transport-specific handler spaghetti. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Adapter-Boundaries]
- Latency matters early: the first meaningful response path must remain inside the trust-sensitive envelope. Do not add summary generation, memory enrichment, or extra remote calls on the critical path if they are not strictly needed for session start. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Technical-Success]
- Session bootstrap here should be minimal and transient. Durable memory belongs later in Epic 2.

### Architecture Compliance

- Respect the modular monolith direction established in Story 1.1.
- Use boring, stable FastAPI patterns already present in the backend rather than inventing a second app framework.
- Keep session-start implementation story-scoped:
  - allow receiving Telegram ingress
  - create minimal session state
  - return opening/clarifying path
  - do not prematurely implement fast/deep branching internals, safety pipeline, billing, memory, or weekly insight jobs
- Do not make Telegram inline buttons mandatory for progress. Text-only path must work.

### Library / Framework Requirements

- Use the backend’s existing FastAPI stack and settings system.
- If `python-telegram-bot` was added in Story 1.1, use the official stable integration patterns from its docs rather than ad hoc request shaping. [Official docs: https://docs.python-telegram-bot.org/en/stable/]
- If Telegram webhook handling is implemented through plain FastAPI endpoints first, keep request verification and idempotency seams in mind, but full idempotent event hardening is mainly detailed later in Epic 6.
- Do not add frontend dependencies or tie Telegram session start to the existing React frontend.

### File Structure Requirements

- Likely touch points:
  - `backend/app/main.py`
  - `backend/app/api/main.py` or an updated routing composition file
  - new Telegram ingress module(s) under a product-aligned folder
  - settings/config files if Telegram bot token or related config keys are needed
  - tests under `backend/tests/...`
- Prefer new product-aligned files over extending template `login.py` / `users.py` / `items.py` for Telegram behavior.
- If a temporary session store/table is required, keep it minimal and explain why it is necessary now rather than later.

### Testing Requirements

- Add tests for:
  - Telegram start or first-message happy path
  - new session bootstrap tied to `telegram_user_id`
  - fallback for empty/too-short/unclear first input
  - non-mandatory button-free text path
- Reuse existing pytest conventions from the backend test suite.
- Ensure at least import/runtime smoke coverage for any new Telegram ingress module.

### Library / Framework Latest Information

- FastAPI still expects clear app/router composition; continue using idiomatic router inclusion and dependency-injected settings rather than custom global state hacks. [Official docs: https://fastapi.tiangolo.com/]
- Pydantic Settings remains the right place for environment-backed bot/config values; avoid bespoke env parsing. [Official docs: https://docs.pydantic.dev/latest/]
- python-telegram-bot stable docs should guide transport-specific typing and bot API interactions if you wire actual Telegram client behavior in this story. [Official docs: https://docs.python-telegram-bot.org/en/stable/]

### Previous Story Intelligence

- Story 1.1 established several guardrails that remain binding here:
  - adapt/minimize the existing full-stack scaffold rather than starting from nothing
  - do not let login/users/items CRUD remain the architectural center
  - preserve environment-backed config and single-service deployment shape
  - avoid broad destructive cleanup when a narrower runtime re-centering will do
- Story 1.1 also highlighted that `python-telegram-bot` and `apscheduler` were not present in the local backend dependency file at the time of story creation. Check the current state before adding duplicates.

### Git Intelligence Summary

- No usable local git history was available through the workflow step, so there are no recent commit learnings to inherit.

### Project Context Reference

- No `project-context.md` was found in the workspace. Use the implementation story from Story 1.1 plus `epics.md`, `architecture.md`, `prd.md`, `ux-design-specification.md`, and the current backend code as the authoritative context set.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story 1.2 was auto-selected from `_bmad-output/implementation-artifacts/sprint-status.yaml` as the first `ready-for-dev` story in order.
- The story file already showed `Status: review` and checked tasks, but the live backend still had only a placeholder Telegram webhook, so implementation was aligned to the story ACs rather than the stale file state.
- Telegram webhook handling was extended from a placeholder endpoint into a session-entry flow that distinguishes `/start`, first free-text input, unclear input fallback, and unsupported updates.
- Added a minimal `TelegramSession` persistence model plus the matching Alembic migration in `backend/app/alembic/versions/3f0d7f6b9a11_add_telegram_session_table.py`.
- Added `backend/app/conversation/session_bootstrap.py` so Telegram transport remains thin and session bootstrap logic lives under the product-aligned `conversation/` seam.
- Validation ran against a temporary local Postgres container on port `5433` because the host `localhost:5432` was occupied by an unrelated container with mismatched credentials.

### Completion Notes List

- This story assumes Story 1.1 establishes the backend foundation and modular seams first.
- Telegram ingress/session entry is intentionally kept separate from legacy auth/user/item web routes.
- Session bootstrap is kept minimal and should not accidentally swallow memory, billing, or safety responsibilities from later stories.
- Added a conversation bootstrap service that parses Telegram webhook payloads, routes `/start` to an opening prompt, creates or reuses an active session on first free-text input, and returns a compact clarifying prompt for unclear input.
- Added minimal persisted session context: `telegram_user_id`, `chat_id`, status, timestamps, turn count, last user message, and last bot prompt.
- Preserved text-first interaction and explicit typing feedback via ordered `signals` in the Telegram response contract; no mandatory inline buttons were introduced.
- Added route-level tests for `/start`, first free-text session creation, unclear-input fallback, and unsupported Telegram updates.
- Verified `uv run pytest`, `uv run ruff check`, and `uv run mypy app tests` all pass against the temporary Postgres test database after `uv run alembic upgrade head`.

### File List

- _bmad-output/implementation-artifacts/1-2-telegram-session-entry.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/alembic/versions/3f0d7f6b9a11_add_telegram_session_table.py
- backend/app/bot/api.py
- backend/app/conversation/session_bootstrap.py
- backend/app/models.py
- backend/tests/conftest.py
- backend/tests/api/routes/test_telegram_session_entry.py

### Change Log

- 2026-03-11: Implemented Telegram session entry via webhook, added minimal `TelegramSession` persistence, opening/clarifying prompts, typing signal feedback, and regression coverage for the new text-first path.
- 2026-03-11: Adversarial code review — removed story 1.3 reflective mode logic (callback handling, mode selection, mode-aware prompts, mode fields) from session_bootstrap.py, stripped reflective_mode/mode_source from TelegramSession model and migration, changed telegram_webhook to sync handler (fixes event loop blocking), added unique constraint on (telegram_user_id, chat_id), added error handling in handle_session_entry, replaced 5 story-1.3 tests with 5 focused story-1.2 tests, added conftest.py to File List.
