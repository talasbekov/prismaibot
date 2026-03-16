# Story 2.3: Использование prior memory при старте новой сессии

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь, который возвращается в продукт позже,
I want чтобы бот помнил важный контекст из прошлых сессий и использовал его в новом разговоре,
so that мне не нужно каждый раз заново объяснять свою ситуацию с нуля.

## Acceptance Criteria

1. When a returning user already has stored summary artifacts or profile facts and they start a new Telegram session, the system can load relevant prior memory for that user and use it as continuity context for the new reflective session. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-23-Использование-prior-memory-при-старте-новой-сессии]
2. When prior memory is found for a returning user and the product forms the early steps of the new session, the bot takes important saved context and recurring patterns into account and does not force the user to retell already-known key elements unnecessarily. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-23-Использование-prior-memory-при-старте-новой-сессии]
3. When saved memory only covers part of the current situation or is stale, the system uses prior context as supporting input rather than as an absolute source of truth and does not assume old memory fully describes the current situation. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-23-Использование-prior-memory-при-старте-новой-сессии]
4. When a user returns after a previous useful session and the product continues the new reflective flow, continuity improves the relevance of follow-up prompts, reflections, and next-step framing, and the session feels like a continuation rather than a full reset. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-23-Использование-prior-memory-при-старте-новой-сессии]
5. When the user has no prior memory or relevant continuity data is absent, the product still works as a clean-session experience and missing memory does not break the core user flow. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-23-Использование-prior-memory-при-старте-новой-сессии]
6. When retrieval or memory loading fails for a returning user, the session continues without continuity enhancement and the user does not see a technical error or a false claim that the system remembers something. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-23-Использование-prior-memory-при-старте-новой-сессии]

## Tasks / Subtasks

- [x] Add a read-side recall seam in `memory/` for session entry continuity lookup (AC: 1, 3, 5, 6)
  - [x] Introduce a memory-focused recall helper or service under `backend/app/memory/` that assembles a bounded continuity snapshot from `SessionSummary` and active `ProfileFact` rows for one `telegram_user_id`.
  - [x] Keep recall selection conservative: prefer recent summaries plus still-active profile facts, and do not expose deleted or superseded facts.
  - [x] Return a structured recall payload that the conversation layer can use without depending on raw DB models.
- [x] Integrate recall into new-session bootstrap without making `bot/` or transport code own memory rules (AC: 1, 2, 4, 5, 6)
  - [x] Update `backend/app/conversation/session_bootstrap.py` so a newly created session can load prior continuity context before composing the first reflective response.
  - [x] Preserve the current rule that an existing `active` session continues normally; recall should apply only when the user is actually starting a fresh session after prior completed sessions.
  - [x] Keep `backend/app/bot/api.py` as a thin transport boundary; do not move continuity logic into the webhook route.
- [x] Use prior memory to improve first-turn and early-turn relevance without turning memory into absolute truth (AC: 2, 3, 4)
  - [x] Extend the first-response and early clarification seams to accept optional prior-memory context.
  - [x] Ensure recalled context changes framing and follow-up relevance, but does not replace the user’s new message as the primary source of the current situation.
  - [x] Keep room for later Story 2.4 by structuring recall output so tentative phrasing and user correction can be layered on cleanly rather than hardcoded now.
- [x] Handle no-memory and failure paths as first-class behaviors (AC: 5, 6)
  - [x] If no summaries/profile facts exist, run the current clean-session path with no degraded UX.
  - [x] If recall lookup fails, log/emit an internal signal if needed, but do not surface a user-facing error and do not claim continuity that was not actually loaded.
  - [x] Do not block the trust-critical first response on heavy recall work beyond the bounded local DB lookup required for MVP.
- [x] Keep continuity data bounded and privacy-aligned on the request path (AC: 1, 3, 5, 6)
  - [x] Reuse the durable summary/profile boundary from Story 2.2 and do not reintroduce transcript-based recall.
  - [x] Avoid copying full summary histories into `TelegramSession`; store only the minimal continuity context needed for the in-flight session.
  - [x] If recall context is persisted on the session for follow-up turns, keep it short, derived, and replaceable.
- [x] Add regression coverage for returning-user continuity behavior (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add tests for a returning user with stored summaries/profile facts starting a fresh session and receiving continuity-aware early behavior.
  - [x] Add tests proving a user with no memory still gets the existing clean-session flow.
  - [x] Add tests for stale/partial memory influence staying bounded rather than overriding the current user message.
  - [x] Add tests for retrieval failure fallback with no false continuity claims and no user-visible technical error.
  - [x] Run backend validation with `pytest`, `ruff`, and `mypy`.

## Dev Notes

- Story 2.2 is already implemented and gives the repo a real durable-memory boundary: `SessionSummary`, `ProfileFact`, transcript purge markers, and transcript-free continuity overview access. Story 2.3 should build on that read model rather than inventing a second memory store. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-2-durable-memory-without-long-term-raw-transcript-storage.md]
- Live repo reality matters more than the aspirational architecture tree. The current implementation has `backend/app/memory/service.py`, `backend/app/memory/schemas.py`, and `backend/app/conversation/session_bootstrap.py`, but no actual recall path yet.
- `session_bootstrap.py` currently creates a new `TelegramSession` whenever no `active` session exists for the same `telegram_user_id` and `chat_id`. That is the seam where returning-user continuity should be injected for fresh sessions. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- The first trust-making response is still the key product moment. Any recall logic that slows it down, overwhelms it, or sounds omniscient would violate both the architecture intent and the UX spec. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Story 2.3 should stop at continuity-aware startup and early-turn relevance. Tentative phrasing and explicit user correction behavior belong to Story 2.4, but the design here must leave a clean seam for that next step.
- Do not regress the transcript-minimization work from Story 2.2 by caching or replaying full prior messages. Summary/profile artifacts are the only durable continuity basis in MVP. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Technical-Constraints]

### Project Structure Notes

- Primary touch points should remain inside:
  - `backend/app/memory/`
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/conversation/first_response.py`
  - `backend/app/conversation/clarification.py`
  - `backend/app/memory/schemas.py`
  - `backend/tests/api/routes/test_telegram_session_entry.py`
  - `backend/tests/memory/`
- Likely implementation shape:
  - new recall-focused helper such as `backend/app/memory/recall.py` or an expanded `memory/service.py`
  - optional recall-specific schema object in `backend/app/memory/schemas.py`
  - session-bootstrap wiring to fetch and pass continuity context into the existing conversation composition functions
  - tests covering returning-user session bootstrap and memory fallback
- Avoid:
  - putting continuity selection logic in `backend/app/bot/api.py`
  - querying transcript-like fields from `TelegramSession` as the source of truth for prior memory
  - turning `shared/` or generic helpers into the owner of memory policy

### References

- Story source and acceptance criteria: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Product continuity and memory requirements: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Architecture boundary and module ownership: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- UX rules for continuity, trust, and memory correction: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)
- Prior story context: [2-2-durable-memory-without-long-term-raw-transcript-storage.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-2-durable-memory-without-long-term-raw-transcript-storage.md)
- Live session-entry seam: [session_bootstrap.py](/home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py)
- Live memory service: [service.py](/home/erda/Музыка/goals/backend/app/memory/service.py)
- Live memory schemas: [schemas.py](/home/erda/Музыка/goals/backend/app/memory/schemas.py)
- Telegram transport boundary: [api.py](/home/erda/Музыка/goals/backend/app/bot/api.py)
- Existing session-entry tests: [test_telegram_session_entry.py](/home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py)
- Existing memory tests: [test_summary.py](/home/erda/Музыка/goals/backend/tests/memory/test_summary.py)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-discovered from `/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog story in order: `2-3-using-prior-memory-at-the-start-of-a-new-session`.
- Core source context loaded from `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, research on LLM memory architecture, previous story `2-2`, and the live backend codebase.
- Live repo inspection confirmed that Story 2.2 already landed durable summary/profile storage plus transcript purge behavior, but there is still no continuity recall path for a fresh session start.
- No `project-context.md` was found in the workspace.
- No local git history was available because `/home/erda/Музыка/goals` is not a git repository root.
- The workflow step that references `_bmad/core/tasks/validate-workflow.xml` could not be executed literally because that file does not exist in the workspace. The story was therefore validated by direct checklist-style review against the create-story requirements instead of the missing task file.
- Latest technical verification used official documentation for FastAPI background tasks, SQLModel session-dependency patterns, Pydantic Settings, PostgreSQL JSON guidance, and the currently pinned `python-telegram-bot` compatibility line.
- Implemented a structured recall read model in `memory/` and wired it into fresh session bootstrap with safe fallback on lookup failure.
- During validation, Story 2.3 exposed a real model-level blocker: `telegram_session` enforced uniqueness on `(telegram_user_id, chat_id)`, which made a new session after `completed` impossible in the same Telegram chat. Fixed with a forward Alembic migration and model update.
- Validation used ephemeral local Postgres containers on ports `5433` and `5434` to get clean backend test databases without interfering with an unrelated service already bound to host `5432`.
- Validation results:
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run alembic upgrade head`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest backend/tests/memory/test_summary.py -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest backend/tests/api/routes/test_telegram_session_entry.py -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest backend/tests -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5434 ENABLE_LEGACY_WEB_ROUTES=true uv run pytest backend/tests -q`
  - `uv run ruff check backend/app backend/tests`
  - `uv run mypy backend/app backend/tests`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story 2.3 is scoped as a read-side continuity story: retrieve bounded prior memory at fresh session start, improve early-turn relevance, and keep the clean-session fallback intact.
- Guardrails explicitly prevent transcript-based recall, transport-layer memory logic, and overconfident use of stale context.
- The story is optimized for the live repo: build on the `memory/` boundary already created in Story 2.2 and inject recall through `session_bootstrap.py` plus early conversation composition seams.
- Story 2.4 is preserved as the next incremental step: this story should prepare for tentative phrasing and correction, not prematurely entangle that behavior here.
- Added `SessionRecallContext` plus `get_session_recall_context()` to assemble a bounded continuity payload from recent summaries and active profile facts.
- Wired first-turn session bootstrap to load prior continuity safely, enrich the first reflective response, and seed bounded `working_context` for follow-up turns.
- Extended first-response and clarification seams to accept optional prior-memory context while keeping the current user message as the primary ground truth.
- Added regression coverage for recall selection, returning-user session startup, fallback on recall failure, and bypassing recall on already-active sessions.
- Removed the `telegram_session` uniqueness constraint on `(telegram_user_id, chat_id)` via Alembic so multiple sessions can exist over time in one Telegram chat, which is required for returning-user continuity to work.
- Full backend validation passed in both normal and legacy-route modes.

### File List

- _bmad-output/implementation-artifacts/2-3-using-prior-memory-at-the-start-of-a-new-session.md
- backend/app/alembic/versions/f4a6b7c8d9e0_allow_multiple_sessions_per_chat.py
- backend/app/conversation/clarification.py
- backend/app/conversation/first_response.py
- backend/app/conversation/session_bootstrap.py
- backend/app/memory/__init__.py
- backend/app/memory/schemas.py
- backend/app/memory/service.py
- backend/app/models.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/memory/test_summary.py

## Change Log

- 2026-03-13: Implemented returning-user continuity recall at fresh session start, added bounded recall schemas/services and regression coverage, and removed the single-session-per-chat constraint so new sessions can start after completion in the same Telegram thread.
- 2026-03-13: Code review fixes applied — corrected `_merge_context_for_session` to trim from end of prior context instead of beginning (preserving takeaway); moved profile facts DB filter and ordering to SQL level with LIMIT 3 ordered by `updated_at` desc; fixed `ProfileFactRecord.source_session_id` to non-optional matching DB constraint; added design-intent comment for `prior_memory_context` omission in clarification turns.

## Developer Context

### Technical Requirements

- Load prior continuity only from durable summaries and active profile facts; do not use raw transcript fields as recall input. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Technical-Constraints]
- Returning-user recall must be bounded enough to fit inside the trust-sensitive request path and not degrade the first meaningful response. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Context-Analysis]
- Prior memory is support context, not a replacement for the user’s new message. The current session still needs to be grounded in what the user says now. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-23-Использование-prior-memory-при-старте-новой-сессии]
- If no memory is found or retrieval fails, the product must still behave like a normal clean-session start with no user-visible system error. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-23-Использование-prior-memory-при-старте-новой-сессии]
- Keep continuity state conservative and replaceable. If session-level caching of recall is needed, persist only a short derived context rather than a copied history of summaries.

### Architecture Compliance

- `memory/` owns summaries, profile facts, and recall logic; `conversation/` owns reflective flow orchestration. Preserve that split instead of embedding DB recall inside transport or generic helpers. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- The architecture explicitly treats Telegram ingress, memory lookup, safety evaluation, prompt assembly, and response generation as one latency-constrained request path. The recall design should stay simple enough for that path. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- The modular target tree already anticipates a `memory/recall.py` seam. Implementing Story 2.3 is the natural point to make that seam real in the live repo rather than growing `session_bootstrap.py` into a memory owner. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- `bot/` remains Telegram transport only. Any new continuity behavior should be invoked below that boundary. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

### Library / Framework Requirements

- Keep using the current backend stack from `backend/pyproject.toml`: FastAPI, SQLModel, Alembic, `pydantic-settings`, PostgreSQL via `psycopg`, and `python-telegram-bot`.
- FastAPI’s official background-task guidance remains relevant to the post-response summary handoff already used in Story 2.2; Story 2.3 should not misuse that seam for startup recall because recall is request-path context, not background enrichment. Official docs: https://fastapi.tiangolo.com/tutorial/background-tasks/
- SQLModel’s FastAPI session-dependency pattern remains the right DB access style for request-path recall in this repo. Keep recall lookup inside the existing request-scoped session rather than opening ad hoc connection patterns. Official docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Pydantic Settings still documents `BaseSettings` as the environment-backed config seam. If recall limits, feature flags, or fallback toggles are needed, keep them in `backend/app/core/config.py`. Official docs: https://docs.pydantic.dev/latest/api/pydantic_settings/
- PostgreSQL current docs still recommend `jsonb` for structured JSON storage with indexing/operator support. If recall uses structured payload aggregation or cached session continuity blobs, prefer typed payloads and `jsonb` semantics over opaque text dumps. Official docs: https://www.postgresql.org/docs/current/datatype-json.html
- The repo pins `python-telegram-bot` 21.11.1 in `uv.lock`; avoid introducing assumptions from newer incompatible major versions while touching Telegram entry behavior. Official docs: https://docs.python-telegram-bot.org/en/v21.11.1/

### File Structure Requirements

- Primary implementation files should stay within:
  - `backend/app/memory/*.py`
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/conversation/first_response.py`
  - `backend/app/conversation/clarification.py`
  - `backend/app/core/config.py` if recall tuning is added
  - `backend/tests/memory/`
  - `backend/tests/api/routes/`
- Likely files to touch:
  - `backend/app/memory/service.py`
  - `backend/app/memory/schemas.py`
  - optional new `backend/app/memory/recall.py`
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/conversation/first_response.py`
  - `backend/app/conversation/clarification.py`
  - `backend/tests/api/routes/test_telegram_session_entry.py`
  - one or more new recall-focused tests under `backend/tests/memory/`
- Avoid writing memory policy into:
  - `backend/app/bot/api.py`
  - `backend/app/api/routes/*`
  - ad hoc utilities that do not clearly belong to `memory/` or `conversation/`

### Testing Requirements

- Add or update tests for:
  - returning user with prior summaries/profile facts starting a fresh session and receiving continuity-aware early behavior
  - no-memory clean-session start behaving exactly like today
  - stale/partial memory being used as support context only
  - retrieval failure producing clean fallback without false “I remember” behavior
  - active-session continuation still bypassing fresh-session recall loading
- Reuse the backend validation toolchain from `backend/pyproject.toml`: `pytest`, `ruff`, and `mypy`.

### Previous Story Intelligence

- Story 2.2 already defined the durable-memory truth model and proved transcript minimization in the live repo. That means Story 2.3 is primarily a read-model and orchestration story, not a storage redesign story. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-2-durable-memory-without-long-term-raw-transcript-storage.md]
- `memory/service.py` already exposes `get_continuity_overview`, which is transcript-free and useful as a starting point, but it is shaped for ops visibility rather than session-entry recall. The implementation likely needs a more focused recall payload for conversation use. [Source: /home/erda/Музыка/goals/backend/app/memory/service.py]
- `session_bootstrap.py` currently sets `working_context` from the user’s first message and later from clarification/closure output. If Story 2.3 wants continuity across turns, it should decide carefully whether to compose prior memory into `working_context` at new-session start or keep it as a parallel input to response composition.
- Existing route tests already verify first-turn routing and clean-session behavior. Extend those tests rather than creating a separate transport stack for continuity.

### Git Intelligence Summary

- No commit intelligence was available because the workspace path is not a git repository root.

### Project Context Reference

- No `project-context.md` was found in the workspace. The authoritative implementation context is `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, Story 2.2, and the live backend codebase.

### Library / Framework Latest Information

- FastAPI still documents `BackgroundTasks` as the supported way to run post-response work, which remains relevant for the existing summary-generation handoff but not as a substitute for request-path recall. Official docs: https://fastapi.tiangolo.com/tutorial/background-tasks/
- SQLModel’s current FastAPI examples continue to use dependency-injected request-scoped sessions. That matches the live `bot/api.py` plus `session_bootstrap.py` boundary and is the correct place for continuity lookup. Official docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Pydantic Settings continues to expose `BaseSettings` for env-backed config, so recall limits or enable/disable flags should stay in the central settings seam. Official docs: https://docs.pydantic.dev/latest/api/pydantic_settings/
- PostgreSQL’s current JSON docs continue to favor `jsonb` for structured JSON use cases. If the implementation caches derived continuity snippets, keep the payload structured and queryable rather than as free-form serialized text. Official docs: https://www.postgresql.org/docs/current/datatype-json.html
- `python-telegram-bot` 21.11.1 remains the current pinned compatibility line in this repo, so the story should preserve existing webhook assumptions instead of pulling in newer-version transport changes. Official docs: https://docs.python-telegram-bot.org/en/v21.11.1/
