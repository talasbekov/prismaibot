# Story 1.3: Выбор и запуск fast/deep reflective mode

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь, который хочет либо быстро выговориться, либо глубже разобрать ситуацию,
I want выбрать подходящий режим reflective-сессии без сложной настройки,
so that формат разговора соответствует моей текущей эмоциональной и когнитивной нагрузке.

## Acceptance Criteria

1. User can choose `fast` or `deep` mode through a simple Telegram-native interaction during the early phase of a new session, and lack of explicit choice does not block the base flow. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-13-Выбор-и-запуск-fastdeep-reflective-mode]
2. When `fast` mode is selected, the session follows a shorter reflective path with fewer clarifying steps, but still reaches a structured takeaway and next-step recommendation. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-13-Выбор-и-запуск-fastdeep-reflective-mode]
3. When `deep` mode is selected, the session follows a more detailed reflective path with more clarification depth, while preserving a calm and non-interrogative tone. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-13-Выбор-и-запуск-fastdeep-reflective-mode]
4. If the user keeps typing free text without explicitly choosing a mode, the conversation continues without forced interruption and applies a safe default mode that does not damage the early trust-making experience. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-13-Выбор-и-запуск-fastdeep-reflective-mode]
5. The selected mode is preserved in current session context and continues to shape follow-up depth for the rest of the session. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-13-Выбор-и-запуск-fastdeep-reflective-mode]
6. If explicit mode selection is unavailable, unrecognized, or Telegram interaction for selection fails, the session continues in a safe fallback mode without surfacing a technical error to the user. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-13-Выбор-и-запуск-fastdeep-reflective-mode]

## Tasks / Subtasks

- [x] Introduce Telegram-native mode selection on top of the existing session-entry path (AC: 1, 4, 6)
  - [x] Extend the current Telegram session-entry flow so mode selection is offered only as a lightweight support interaction during early session handling, not as a mandatory setup gate before all progress. *(fixed in review: added inline buttons to /start response and callback handler)*
  - [x] Keep the default free-text path working when the user ignores mode controls and continues typing naturally.
  - [x] Ensure explicit mode-selection failure or unsupported interaction degrades to a safe fallback without technical error leakage. *(fixed in review: invalid mode:unknown → fallback to default, mode_source="fallback")*
- [x] Persist mode choice inside the active session context (AC: 1, 5, 6)
  - [x] Add minimal session-level state to represent current reflective mode without introducing unrelated profile or long-term memory concepts.
  - [x] Ensure mode can be inferred or defaulted safely when explicit selection is absent.
  - [x] Preserve chosen mode across subsequent messages within the same active session.
- [x] Implement `fast` mode behavior with bounded clarification depth (AC: 2, 5)
  - [x] Define how `fast` mode reduces follow-up depth compared with default/deep handling.
  - [x] Ensure `fast` mode still preserves the reflective product promise and does not collapse into advice-first or shallow generic chat.
  - [x] Keep `fast` mode compatible with later structured takeaway and next-step stories rather than hardcoding premature closure logic here.
- [x] Implement `deep` mode behavior with richer but calm exploration (AC: 3, 5)
  - [x] Define how `deep` mode increases clarification depth without creating an interrogative or menu-heavy feel.
  - [x] Keep tone and pacing humane, low-pressure, and Telegram-readable even when more depth is requested.
  - [x] Ensure deeper mode behavior is applied by session-aware branching rather than transport-specific hacks.
- [x] Verify mode handling, fallback behavior, and regression safety (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add/update tests for explicit `fast` selection, explicit `deep` selection, free-text no-selection fallback, and selection-failure fallback. *(fixed in review: added test_mode_selection_fast_via_callback, test_mode_selection_deep_via_callback, test_mode_selection_invalid_callback_falls_back_gracefully, test_opening_prompt_includes_mode_selection_buttons)*
  - [x] Verify session context stores and reuses mode choice across follow-up messages.
  - [x] Run backend validation relevant to updated Telegram/session flow and confirm legacy auth/web routes remain non-central to this path.

## Dev Notes

- This story extends the already implemented session-entry baseline from Story 1.2 and must not recreate Telegram ingress, opening prompt behavior, or basic active-session bootstrap from scratch. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-2-telegram-session-entry.md]
- Product value here is not "mode UI for its own sake". The point is to let the user express current cognitive load and get a lighter or deeper reflective path without creating onboarding friction. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#MVP---Minimum-Viable-Product]
- UX explicitly requires that explicit mode selection must not dominate the first-run experience; default interaction should privilege immediacy over configuration. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#Core-User-Experience]
- Buttons remain support controls only. Inline buttons may be used for low-friction mode choice, but the session must keep working through plain text if the user ignores them or Telegram interaction does not cooperate. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#UX-Consistency-Patterns]
- The trust-making first meaningful response remains architecturally sensitive. Do not insert a heavy mode-selection gate that delays or degrades the first response path beyond the MVP latency envelope. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Core-Architectural-Decisions]
- This story should define session-scoped mode behavior only. Do not pull memory continuity, billing, safety, or summary pipelines into the mode-selection implementation. Those remain separate domains and later stories.

### Project Structure Notes

- Current Telegram webhook ingress lives in [`backend/app/bot/api.py`](/home/erda/Музыка/goals/backend/app/bot/api.py). It already routes `/start` to an opening prompt and passes free-text messages into `handle_session_entry(...)`. This is the primary transport touch point for mode-selection integration.
- Current early-session orchestration lives in [`backend/app/conversation/session_bootstrap.py`](/home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py). This is the most likely near-term place to add or extract session-aware mode branching unless Story 1.3 introduces a more precise conversation service split.
- Current persisted session state lives in [`backend/app/models.py`](/home/erda/Музыка/goals/backend/app/models.py) via `TelegramSession`. If mode is persisted, keep it as minimal session context rather than introducing profile-level or memory-level state.
- Existing Telegram flow tests live in [`backend/tests/api/routes/test_telegram_session_entry.py`](/home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py). Extend this test surface instead of hiding mode coverage in unrelated legacy route tests.
- Product-first routing composition is already centered in [`backend/app/api/main.py`](/home/erda/Музыка/goals/backend/app/api/main.py). Do not move mode-selection behavior into `login.py`, `users.py`, `items.py`, or other template-era CRUD surfaces.

### References

- Story source and acceptance criteria: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Previous implementation baseline: [1-2-telegram-session-entry.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-2-telegram-session-entry.md)
- Product value and MVP scope: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Architecture guardrails and module boundaries: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- Telegram-native interaction, button policy, and trust patterns: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)

## Developer Context

### Technical Requirements

- Story 1.3 implements FR3 only, but it must respect the session-entry behavior already established by FR1, FR2, and FR5 work from Story 1.2. Mode selection is an addition to the flow, not a replacement for it. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-13-Выбор-и-запуск-fastdeep-reflective-mode]
- The early session path remains inside a trust-sensitive latency envelope. Context assembly, mode branching, and response generation must stay fast enough to preserve the first meaningful response moment. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Context-Analysis]
- Telegram is still the only user-facing surface. Do not implement browser-first mode handling, account-preference storage, or setup screens for this story. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Technical-Constraints--Dependencies]
- If mode selection uses explicit Telegram interaction, fallback must remain text-safe and non-breaking when inline interaction is missing, ignored, or fails. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-13-Выбор-и-запуск-fastdeep-reflective-mode]
- Selected mode should shape session depth only. Do not let `fast` mode collapse into generic advice-first chat, and do not let `deep` mode turn into an interrogative questionnaire. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#Component-Strategy]

### Architecture Compliance

- Preserve the modular-monolith direction established in Story 1.1 and the product-first runtime center established in Story 1.2.
- Keep Telegram transport concerns in `bot/` and reflective/session behavior in `conversation/`; do not let transport-specific branching own the product logic. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Structure--Boundaries]
- Store only minimal session-scoped mode state needed for current-session branching. Do not create durable memory, premium-access, or safety-specific coupling in this story.
- Mode selection must remain optional in practice. If the user keeps typing, the system should continue naturally with a safe default rather than hard-stopping for explicit mode UI.
- Keep button hierarchy conservative: one clear low-risk action at a time, sparse inline controls, and no critical dependency on button-only progress. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#UX-Consistency-Patterns]

### Library / Framework Requirements

- Use the existing FastAPI stack and route composition already present in the backend.
- Use the existing SQLModel-based persistence baseline in this repo for minimal session-state changes, even though the architecture document discusses SQLAlchemy 2 more generally. Follow the real repository state, not the abstract future target.
- Pydantic Settings remains the environment-backed configuration approach. Do not introduce a second config system for mode defaults or Telegram behavior. [Official docs: https://docs.pydantic.dev/latest/]
- If Telegram-specific response behavior needs explicit Bot API semantics later, use official `python-telegram-bot` patterns as the source of truth rather than ad hoc blog examples. [Official docs: https://docs.python-telegram-bot.org/en/stable/]
- FastAPI router composition and dependency-injected request handling should remain idiomatic and simple. [Official docs: https://fastapi.tiangolo.com/]

### File Structure Requirements

- Primary touch points should remain inside `backend/app/bot/`, `backend/app/conversation/`, `backend/app/models.py`, and `backend/tests/api/routes/`.
- Likely files to touch:
  - `backend/app/bot/api.py`
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/models.py`
  - `backend/tests/api/routes/test_telegram_session_entry.py`
  - a new migration file only if persisted session schema must change
- Avoid spreading mode logic into unrelated legacy template files or creating a broad new domain module unless the refactor is clearly justified by this story’s scope.
- If you add session mode persistence, keep migration scope minimal and explain why it is required now.

### Testing Requirements

- Add or update tests for:
  - explicit `fast` selection
  - explicit `deep` selection
  - free-text continuation without explicit selection
  - selection failure / unsupported-interaction fallback
  - persistence and reuse of selected mode across later messages in the same session
- Preserve and extend the current Telegram webhook regression coverage instead of replacing it.
- Run backend validation using the project toolchain from `backend/pyproject.toml`: `pytest`, `ruff`, and `mypy`.
- Confirm legacy auth/web routes remain non-central to the Telegram mode-selection path by keeping the new coverage on the `/api/v1/telegram/webhook` path.

### Previous Story Intelligence

- Story 1.2 already introduced:
  - `TelegramSession` as minimal persisted session context
  - `/api/v1/telegram/webhook` as the Telegram-first ingress path
  - `/start` opening-prompt handling
  - explicit `typing` signals before meaningful responses
  - free-text continuation and clarifying fallback behavior
- Story 1.3 should reuse these foundations rather than re-deriving them.
- Story 1.2 also established a practical implementation pattern: keep transport handling thin in `bot/api.py`, keep early session orchestration in `conversation/session_bootstrap.py`, and prove behavior through API-route tests.

### Project Context Reference

- No `project-context.md` was found in the workspace. Use Story 1.2 plus `epics.md`, `prd.md`, `architecture.md`, and `ux-design-specification.md` as the authoritative context set for implementation.

### Library / Framework Latest Information

- FastAPI official documentation continues to center application composition around `FastAPI()`, router inclusion, and dependency-injected request handling. Story 1.3 should keep mode selection inside the existing router/service flow instead of inventing a parallel framework layer. [Official docs: https://fastapi.tiangolo.com/]
- Pydantic documentation continues to position `BaseSettings` / `pydantic-settings` as the supported approach for environment-backed configuration. If mode defaults or feature flags are needed, they should remain inside the existing settings model rather than bespoke env parsing. [Official docs: https://docs.pydantic.dev/latest/]
- `python-telegram-bot` stable documentation remains the source of truth for Telegram bot interaction patterns such as chat actions and message semantics. If Story 1.3 expands Telegram-specific interaction beyond the current internal response contract, use official library patterns rather than random examples. [Official docs: https://docs.python-telegram-bot.org/en/stable/]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story `1-3-fast-deep-reflective-mode` was auto-selected from `sprint-status.yaml` as the first `ready-for-dev` story in sprint order.
- The live repo was behind the story context, so implementation landed the missing Telegram session seam directly in `backend/app/conversation/session_bootstrap.py`, `backend/app/bot/api.py`, and `backend/app/models.py`.
- Added a new `TelegramSession` persistence model plus Alembic migration `backend/app/alembic/versions/3f0d7f6b9a11_add_telegram_session_table.py` to store session-scoped reflective mode state.
- Added route-level regression coverage in `backend/tests/api/routes/test_telegram_session_entry.py` for `/start`, explicit `fast`, explicit `deep`, free-text fallback, invalid mode fallback, and mode reuse across follow-up messages.
- Validation used a temporary local Postgres container on port `5433` because the existing service on `localhost:5432` belongs to another workspace and rejected this repo's configured credentials.

### Completion Notes List

- Implemented a Telegram-first webhook flow that offers optional inline mode controls on `/start` and keeps free-text progress working when the user ignores them.
- Persisted session-scoped reflective mode in `TelegramSession` using `reflective_mode` and `mode_source`, with default fallback to `deep` when no explicit choice is available.
- Implemented mode-aware early-session prompts so `fast` yields bounded follow-up depth and `deep` yields a calmer, more exploratory prompt without turning into a questionnaire.
- Implemented safe fallback for unsupported mode callback data with no technical-error leakage in user-visible messages.
- Verified the backend with `uv run ruff check app tests`, `POSTGRES_PORT=5433 ENABLE_LEGACY_WEB_ROUTES=true uv run mypy app tests`, `POSTGRES_PORT=5433 uv run pytest tests/api/routes/test_telegram_session_entry.py`, and `POSTGRES_PORT=5433 ENABLE_LEGACY_WEB_ROUTES=true uv run pytest`.

### File List

- backend/app/alembic/versions/3f0d7f6b9a11_add_telegram_session_table.py
- backend/app/alembic/versions/b5f1f1729d3f_add_reflective_mode_and_working_context_.py
- backend/app/bot/api.py
- backend/app/conversation/session_bootstrap.py
- backend/app/core/config.py
- backend/app/models.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/conftest.py

### Change Log

- 2026-03-11: Added Telegram session-backed `fast`/`deep` mode selection, safe fallback behavior, persistence for current-session mode reuse, and regression coverage for the Telegram webhook flow.
- 2026-03-12: Code review fixes — added inline_keyboard to opening_prompt (/start), callback handler for mode:fast/mode:deep/invalid-mode, mode_source field (model + migration b5f1f1729d3f), CONVERSATION_DEFAULT_REFLECTIVE_MODE config, and 4 new tests covering explicit mode selection and fallback.
