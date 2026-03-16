# Story 1.6: Завершение сессии с takeaway и next-step options

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь, который прошел через reflective conversation,
I want получить ясное завершение с кратким takeaway и несколькими следующими шагами,
so that я выхожу из сессии с большей ясностью и понимаю, что делать дальше.

## Acceptance Criteria

1. When the product detects that the current reflective exchange has reached a suitable closure point, it returns an end-of-session takeaway that briefly reflects the core of the situation and stays calm, clear, and grounded in the session context. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-16-Завершение-сессии-с-takeaway-и-next-step-options]
2. When the final session response is generated, the user receives 1 to 3 realistic next-step options or recommendations that fit the analyzed situation and do not feel judgmental, inflated, or generic. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-16-Завершение-сессии-с-takeaway-и-next-step-options]
3. The final message creates a sense of closure and orientation rather than an abrupt stop, and it must do more than emit a generic summary without actionable guidance. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-16-Завершение-сессии-с-takeaway-и-next-step-options]
4. If uncertainty remains at the end of the session, the bot may acknowledge that ambiguity directly while still offering a safe, understandable immediate next move instead of pretending certainty it does not have. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-16-Завершение-сессии-с-takeaway-и-next-step-options]
5. In `fast` mode, the closure stays concise and low-burden, and the user does not need extra long interaction to extract value from the ending. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-16-Завершение-сессии-с-takeaway-и-next-step-options]
6. In `deep` mode, the closure may reflect deeper work, but it must remain Telegram-readable and must not degrade into a wall of text. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-16-Завершение-сессии-с-takeaway-и-next-step-options]

## Tasks / Subtasks

- [x] Add an explicit closure-stage conversation component that consumes the structured session state rather than improvising a raw final reply in the webhook path (AC: 1, 2, 3, 4)
  - [x] Extend `backend/app/conversation/` with a reusable closure builder or orchestrator step that takes the current session mode, latest clarified understanding, and any intermediate reflective breakdown.
  - [x] Keep Telegram transport thin in `backend/app/bot/api.py`; do not encode takeaway/next-step policy directly in the route handler.
  - [x] Ensure the closure seam is compatible with later summary generation in Epic 2 so Story 2.1 can reuse session-end structure instead of re-deriving it from raw text.
- [x] Define the end-of-session output contract for takeaway plus next-step options (AC: 1, 2, 3, 4)
  - [x] Produce a short takeaway that names the central tension, pattern, or clarified situation in grounded language.
  - [x] Generate 1 to 3 next-step options, keeping them realistic, low-pressure, and situationally specific.
  - [x] Add an explicit low-confidence branch where the bot admits uncertainty but still offers a safe next move.
- [x] Make closure mode-aware without forking the product into two unrelated behaviors (AC: 5, 6)
  - [x] In `fast` mode, keep the closing structure compact: takeaway plus a very small set of options.
  - [x] In `deep` mode, allow a slightly richer closing synthesis while preserving Telegram chunking and scanability.
  - [x] Reuse the same closure primitives in both modes so later stories do not have to maintain separate formatting stacks.
- [x] Preserve UX trust rules established earlier in Epic 1 (AC: 1, 2, 3, 4, 5, 6)
  - [x] Keep the closing tone non-medical, non-judgmental, and collaborative rather than authoritative.
  - [x] Avoid ending the session with a cold generated recap or advice-first directive.
  - [x] Make the ending feel like orientation and soft landing, not system termination.
- [x] Keep output Telegram-readable and operationally bounded (AC: 2, 3, 5, 6)
  - [x] Break longer closure content into readable chunks if needed rather than returning one dense paragraph.
  - [x] Limit next-step count to at most three, and keep each option short enough to scan inside chat.
  - [x] Preserve typing-signal behavior if the current Telegram response path already emits it.
- [x] Cover closure behavior with tests and regressions (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add route or conversation-level tests for a normal session closure that returns a concise takeaway and bounded next steps.
  - [x] Add tests for uncertainty-aware closure, `fast` mode compactness, and `deep` mode readability.
  - [x] Add a regression test that rejects wall-of-text closure output or more than three next-step options.
  - [x] Run backend validation with `pytest`, `ruff`, and `mypy`.

## Dev Notes

- Story 1.6 is the closure layer for Epic 1. It should consume the reflective understanding produced by Stories 1.4 and 1.5 instead of reopening clarification or inventing a separate mini-flow at the very end. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-5-clarification-and-breakdown-of-facts-emotions-and-interpretations.md]
- UX treats session closure as a soft landing: the user should leave with orientation, relief, and a manageable next move, not with a cold summary dump. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#Component-Strategy]
- FR9 and FR10 are narrow but trust-sensitive. The quality bar is not "some advice exists"; it is "the final message feels grounded in this specific session and leaves the user steadier than before." [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Guided-Reflection-Experience]
- Story 2.1 will later need a structured summary after session completion. If Story 1.6 produces a coherent closure object or closure-stage structure now, Epic 2 can build on that seam instead of reconstructing the session ending from scratch.
- Current repo reality still matters: Telegram ingress is thin, and the conversation seam remains concentrated in `backend/app/conversation/session_bootstrap.py`. The implementation should strengthen `conversation/` as the home of closure policy rather than stretching route logic further.
- Product tone remains explicitly non-medical. The closing takeaway must not sound like diagnosis, therapy homework, or moral verdict. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Compliance--Regulatory]

### Project Structure Notes

- Primary touch points should remain inside:
  - `backend/app/bot/api.py`
  - `backend/app/conversation/session_bootstrap.py`
  - new or expanded closure helpers under `backend/app/conversation/`
  - `backend/app/models.py` only if session persistence needs extra closure-state fields
  - `backend/tests/api/routes/` for Telegram route regressions
- Prefer adding reusable closure logic under `backend/app/conversation/` instead of burying formatting rules in `backend/app/bot/api.py` or generic utilities.
- The architecture document proposes a more expanded modular monolith than the live repo currently has. For this story, follow the live repo shape and move it incrementally toward clearer `conversation/` ownership rather than forcing a broad restructuring inside one implementation story.
- If persistence changes are needed, use the existing SQLModel plus Alembic flow already present in the repo rather than introducing a new persistence abstraction mid-epic.

### References

- Story source and acceptance criteria: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Previous story context and handoff expectations: [1-5-clarification-and-breakdown-of-facts-emotions-and-interpretations.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-5-clarification-and-breakdown-of-facts-emotions-and-interpretations.md)
- Trust-making and mode-selection foundations: [1-4-first-trust-making-response-with-situation-reflection.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-4-first-trust-making-response-with-situation-reflection.md), [1-3-fast-deep-reflective-mode.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-3-fast-deep-reflective-mode.md)
- Product scope, FR9/FR10, and non-medical constraints: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Architecture boundaries and module ownership: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- UX closure, readability, and component rules: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)
- Live ingress seam: [api.py](/home/erda/Музыка/goals/backend/app/bot/api.py)
- Live conversation seam: [session_bootstrap.py](/home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py)
- Current settings seam: [config.py](/home/erda/Музыка/goals/backend/app/core/config.py)
- Backend dependency policy: [pyproject.toml](/home/erda/Музыка/goals/backend/pyproject.toml)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-discovered from `_bmad-output/implementation-artifacts/sprint-status.yaml` as the first `backlog` story in order: `1-6-session-closure-with-takeaway-and-next-step-options`.
- Core source context loaded from `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, and prior implementation stories through `1-5`.
- Live backend inspection confirmed Telegram ingress is routed through `backend/app/bot/api.py` and closure logic should extend the existing `backend/app/conversation/session_bootstrap.py` seam rather than bypass it.
- No `project-context.md` was found in the workspace.
- No usable local git metadata was available because `/home/erda/Музыка/goals` is not a git repository root.
- Latest framework verification used official documentation for FastAPI router composition, Pydantic Settings, `python-telegram-bot`, and SQLModel session dependency patterns.
- Implemented a dedicated closure composer in `backend/app/conversation/closure.py` and routed third-turn session completion through `session_bootstrap.py` using the existing `TelegramSession` seam.
- Used an isolated temporary Postgres container on port `5433` for migrations and validation because the host `localhost:5432` does not accept this repo's configured test credentials.
- Validation runs completed with:
  - `POSTGRES_PORT=5433 uv run pytest tests/conversation/test_closure.py tests/api/routes/test_telegram_session_entry.py`
  - `POSTGRES_PORT=5433 ENABLE_LEGACY_WEB_ROUTES=true uv run pytest`
  - `POSTGRES_PORT=5433 uv run ruff check app tests`
  - `POSTGRES_PORT=5433 uv run mypy app tests`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story 1.6 is scoped as closure-stage orchestration for takeaway and next-step generation, not as new ingress, memory persistence, billing, or crisis-routing work.
- Guardrails emphasize calm closure, bounded next-step count, explicit uncertainty handling, Telegram readability, and mode-aware synthesis without duplicated formatting stacks.
- The story is optimized for the live backend shape: extend `conversation/`, keep the webhook route thin, and add Telegram-specific tests where they are currently missing.
- Added a reusable closure-stage response builder that returns a grounded takeaway plus bounded next-step options and keeps a structured seam for future summary generation.
- Updated `session_bootstrap.py` to complete sessions through the closure path after enough reflective context is gathered, while preserving typing signals and thin route transport.
- Added targeted closure tests and route-level Telegram regressions covering normal closure, low-confidence closure, `fast` compactness, `deep` readability, bounded next steps, and completed-session state.
- Kept legacy conversation behaviors green by refining vague-marker handling in first response logic and context-priority selection in clarification logic.
- Full backend validation passed: 101 pytest tests, `ruff check app tests`, and `mypy app tests`.

### File List

- _bmad-output/implementation-artifacts/1-6-session-closure-with-takeaway-and-next-step-options.md
- backend/app/conversation/_text_utils.py
- backend/app/conversation/closure.py
- backend/app/conversation/session_bootstrap.py
- backend/app/conversation/clarification.py
- backend/app/conversation/first_response.py
- backend/app/core/config.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/conversation/test_closure.py

## Change Log

- 2026-03-12: Implemented closure-stage conversation orchestration with mode-aware takeaway and next-step generation, session completion state, Telegram regression coverage, and full backend validation on an isolated Postgres test database.
- 2026-03-12: Code review fixes — removed open question from low-confidence takeaway (UX bug: session marked completed immediately after closure), added deep mode wall-of-text regression test, extracted shared `normalize_spaces` utility to `_text_utils.py`, added fast+low_confidence unit test, added route-level low-confidence closure regression test.

## Developer Context

### Technical Requirements

- The closing response must produce both orientation and actionability: a short takeaway plus 1 to 3 next-step options. Either half on its own is insufficient for FR9 and FR10. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-16-Завершение-сессии-с-takeaway-и-next-step-options]
- Closure is still part of the trust-sensitive reflective flow. It must stay calm, specific, and grounded in the session rather than switching into generic assistant mode or life-coach cliches. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Guided-Reflection-Experience]
- If the session remains ambiguous, the bot should acknowledge that uncertainty directly and still offer a safe immediate next move. This prevents false certainty at exactly the moment the user is deciding what to do next. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-16-Завершение-сессии-с-takeaway-и-next-step-options]
- `fast` mode closure must be compact and low-burden; `deep` mode may be richer but still must remain scanable in Telegram. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-16-Завершение-сессии-с-takeaway-и-next-step-options]
- UX explicitly treats long dense replies as a product and accessibility failure. Closure output should therefore favor chunked, readable message units over one long paragraph. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#Responsive-Design--Accessibility]

### Architecture Compliance

- Keep Telegram transport in `bot/` and closure policy in `conversation/`; the webhook route should delegate rather than become the final-message decision engine. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Structure--Boundaries]
- Stay inside the normal reflective path. Story 1.6 should not pull in crisis escalation, summary jobs, premium gating, or billing behavior unless the existing flow already routes there.
- Preserve a clean handoff for Epic 2. A structured closure result today can later feed summary generation, memory persistence, and repeat-session recall without re-parsing user-facing prose.
- The architecture document prefers SQLAlchemy 2 conceptually, but the live repo uses SQLModel. Implement against the real codebase and avoid forcing ORM migration in a closure story.

### Library / Framework Requirements

- Use the current backend stack from [pyproject.toml](/home/erda/Музыка/goals/backend/pyproject.toml): FastAPI, SQLModel, Alembic, `pydantic-settings`, and `python-telegram-bot`.
- FastAPI’s official larger-app guidance still centers `APIRouter` composition with `include_router()`, which matches keeping Telegram routing thin and pushing business logic downward into `conversation/`. Official docs: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- Pydantic Settings remains the supported environment-backed settings mechanism. If closure mode thresholds or output limits need configuration, keep them in `backend/app/core/config.py` rather than as module-local constants. Official docs: https://docs.pydantic.dev/latest/api/pydantic_settings/
- The repo pins `python-telegram-bot<22.0,>=21.6`. Stable upstream docs are newer, so avoid accidentally introducing APIs that require a v22-only upgrade unless dependency policy changes first. Official docs: https://docs.python-telegram-bot.org/en/stable/
- SQLModel guidance still supports one session per request via dependency injection, which fits the current backend style if closure needs persisted session updates. Official docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/

### File Structure Requirements

- Primary implementation files should stay within:
  - `backend/app/bot/api.py`
  - `backend/app/conversation/session_bootstrap.py`
  - new conversation helpers under `backend/app/conversation/`
  - `backend/app/core/config.py`
  - `backend/tests/api/routes/`
- Likely files to touch:
  - `backend/app/conversation/session_bootstrap.py`
  - one or more new `backend/app/conversation/` modules for closure formatting or stage orchestration
  - `backend/app/bot/api.py` only if the route contract changes minimally
  - `backend/tests/api/routes/test_telegram_session_entry.py` or equivalent Telegram-specific route tests
  - an Alembic migration only if closure state truly requires persistence changes
- Avoid spreading closure policy into legacy auth, items, or user-management modules.

### Testing Requirements

- Add or update tests for:
  - normal reflective closure with one concise takeaway and bounded next-step list
  - `fast` mode compact ending
  - `deep` mode richer but still readable ending
  - uncertainty-aware closure that admits ambiguity and still gives a safe next move
  - regression against more than three options
  - regression against wall-of-text closure output
- Keep route-level coverage on `/api/v1/telegram/webhook` and add conversation-level tests if the closure component is extracted from the route seam.
- Reuse the backend validation toolchain from [pyproject.toml](/home/erda/Музыка/goals/backend/pyproject.toml): `pytest`, `ruff`, and `mypy`.

### Previous Story Intelligence

- Story 1.5 already framed the session as a structured clarification flow that separates facts, emotions, and interpretations. Story 1.6 should use that structured understanding as input instead of flattening everything into a generic wrap-up. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-5-clarification-and-breakdown-of-facts-emotions-and-interpretations.md]
- Story 1.4 established the reflection-first tone. The final takeaway should preserve that tone right through the end rather than becoming blunt advice or system summary. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-4-first-trust-making-response-with-situation-reflection.md]
- Story 1.3 made `fast` and `deep` meaningful session states. Story 1.6 is where those states must visibly change the shape of closure, not just the opening. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-3-fast-deep-reflective-mode.md]
- The current repo remains behind the full planned conversation architecture. Treat Story 1.6 as another convergence step that strengthens the conversation seam instead of assuming all prior planned modules already exist exactly as documented.

### Git Intelligence Summary

- No commit intelligence was available because the workspace path is not a git repository root.

### Project Context Reference

- No `project-context.md` was found in the workspace. The authoritative implementation context is `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, prior Epic 1 story files, and the live backend codebase.

### Library / Framework Latest Information

- FastAPI still documents router composition through `APIRouter` and `include_router()` for larger apps, which supports keeping transport composition separate from closure policy. Official docs: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- Pydantic Settings still documents `BaseSettings` as the environment-backed config mechanism, which matches the existing `backend/app/core/config.py` seam. Official docs: https://docs.pydantic.dev/latest/api/pydantic_settings/
- Stable `python-telegram-bot` documentation remains current upstream, but this repo is pinned below v22. Use the current project dependency policy as the implementation ceiling unless the dependency is upgraded intentionally. Official docs: https://docs.python-telegram-bot.org/en/stable/
- SQLModel still documents request-scoped session injection through FastAPI dependencies. If closure persists additional session-end state, stay aligned with that existing request/session pattern. Official docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
