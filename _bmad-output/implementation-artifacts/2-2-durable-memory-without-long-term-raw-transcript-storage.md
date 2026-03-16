# Story 2.2: Сохранение durable memory без долгого хранения raw transcript

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь, который возвращается к продукту со временем,
I want чтобы система сохраняла только нужную continuity memory, а не полный сырой диалог,
so that мой контекст остается доступным без лишнего накопления чувствительных данных.

## Acceptance Criteria

1. When session summary has been created successfully after session completion and the system writes continuity memory into durable storage, it persists structured summary data plus allowed profile facts for future recall, and does not use the full raw transcript as the primary durable memory artifact. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-22-Сохранение-durable-memory-без-долгого-хранения-raw-transcript]
2. When the processing window for a session ends, raw conversational content is not retained longer than required for response generation and summary generation, and the durable storage boundary remains centered on a summary/profile model. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-22-Сохранение-durable-memory-без-долгого-хранения-raw-transcript]
3. When continuity data is stored in the persistent layer, summary artifacts and profile facts live in separate, understandable memory scopes, and are not mixed together with transient message-processing data. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-22-Сохранение-durable-memory-без-долгого-хранения-raw-transcript]
4. When operators or internal workflows access continuity data in routine operations, the access path is built around summary/profile artifacts and metadata, and does not require exposing the full session transcript. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-22-Сохранение-durable-memory-без-долгого-хранения-raw-transcript]
5. When memory artifacts are stored after a session, they are marked so they can later be updated or deleted as part of the user data lifecycle, keeping the retention model compatible with future deletion workflows. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-22-Сохранение-durable-memory-без-долгого-хранения-raw-transcript]
6. If durable memory persistence fails after session summary has already been created, the system emits an observable failure signal and a safe retry path, and does not silently fall back to indefinite transcript retention. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-22-Сохранение-durable-memory-без-долгого-хранения-raw-transcript]

## Tasks / Subtasks

- [x] Add a durable memory persistence boundary that is separate from transient Telegram session state (AC: 1, 2, 3, 5)
  - [x] Introduce product-aligned memory models for persisted session summaries and separately scoped profile facts under `backend/app/memory/` and `backend/app/models.py`.
  - [x] Use Alembic migrations to create durable memory tables or columns rather than overloading `telegram_session` as the long-term storage bucket.
  - [x] Ensure the model design explicitly distinguishes durable artifacts from short-lived processing fields like `working_context`, `last_user_message`, and `last_bot_prompt`.
- [x] Define the first durable storage contract for summary artifacts and allowed profile facts (AC: 1, 3, 4, 5)
  - [x] Keep summary artifacts structured and machine-usable, aligned with the schema direction from Story 2.1.
  - [x] Introduce a conservative profile-fact scope with clear rules about what may be promoted into durable storage versus what must remain transient.
  - [x] Add lifecycle metadata needed for future update/delete workflows, such as timestamps, user linkage, source session linkage, and retention/deletion eligibility markers.
- [x] Enforce transcript-minimization behavior instead of transcript fallback (AC: 1, 2, 6)
  - [x] Define and implement the point at which raw conversational fields stop being needed for active processing.
  - [x] Clear, redact, expire, or otherwise move transient session fields out of durable use once summary persistence succeeds, without breaking current request-path behavior.
  - [x] Explicitly prevent “save the whole transcript just in case” behavior as a persistence fallback.
- [x] Add observable failure and retry-safe handling for durable memory persistence (AC: 4, 5, 6)
  - [x] Emit an ops-visible failure signal or bounded retry state when durable persistence fails.
  - [x] Keep the persistence path compatible with future operator workflows that should see metadata and failure states without transcript exposure.
  - [x] Make the persistence step idempotent enough that a retry does not duplicate durable artifacts or corrupt lifecycle state.
- [x] Keep the live repo aligned with the planned memory architecture without pretending Story 2.1 is already implemented (AC: 1, 2, 3, 6)
  - [x] Reuse the closure and conversation seams landed in Story 1.6 where practical, but do not assume summary generation internals already exist in code just because Story 2.1 has a context file.
  - [x] Keep Telegram ingress thin and avoid pushing durable memory storage rules into `backend/app/bot/api.py`.
  - [x] Make the new memory boundary reusable for later Stories 2.3 through 2.5 instead of baking single-story assumptions into one-off helper code.
- [x] Cover durable-memory retention boundaries with tests and regressions (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add tests that verify summaries and profile facts persist into separate scopes and raw transcript fields are not treated as durable memory.
  - [x] Add tests for transcript-minimization after the processing window, including failure-path behavior where persistence retries must not retain the full transcript indefinitely.
  - [x] Add tests for lifecycle metadata and delete/update compatibility of durable memory artifacts.
  - [x] Run backend validation with `pytest`, `ruff`, and `mypy`.

## Dev Notes

- Story 2.2 depends conceptually on Story 2.1 but must be written against repo reality: `2-1` is currently `ready-for-dev`, not implemented. The developer should therefore build a durable memory boundary that can receive structured summaries, but must not assume a finished summary generator already exists in source. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-1-session-summary-generation-after-session-completion.md]
- The PRD is explicit that **summary is the durable memory artifact, raw conversation is transient processing input**. Story 2.2 is the storage-boundary story that makes that principle real in code. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Technical-Constraints]
- Architecture already names `memory/` as the owner of summaries, profile facts, and recall logic. It also separately calls out transcript minimization, deletion compatibility, and operator visibility without routine transcript exposure. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Structure--Boundaries]
- Live repo reality still matters: current durable-ish state lives only on `TelegramSession` fields such as `working_context`, `last_user_message`, and `last_bot_prompt`, which are not sufficient as long-term memory artifacts and should not be normalized into that role.
- The current `backend/app/memory/` package is still empty. This story should establish the first true durable-memory module boundary rather than extending `conversation/` forever.
- Privacy discipline is part of product correctness here, not a cleanup chore for later. If durable persistence falls back to transcript retention, the product breaks FR15/FR34 even if recall technically works.

### Project Structure Notes

- Primary touch points should remain inside:
  - `backend/app/memory/`
  - `backend/app/models.py`
  - `backend/app/alembic/versions/`
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/ops/` or a small product-aligned failure-signaling seam
  - `backend/tests/memory/`
  - `backend/tests/conversation/` and `backend/tests/api/routes/` where orchestration boundaries need regression coverage
- Prefer a clear memory module boundary:
  - `conversation/` decides when handoff happens
  - `memory/` owns durable artifact schemas, persistence, lifecycle metadata, and retry/failure semantics
  - `ops/` owns visibility signals rather than transcript inspection
- Avoid treating `TelegramSession` as the durable memory table. It is a runtime session seam, not the long-term continuity model.
- If the implementation uses structured JSON payloads, keep them explicit and typed; do not hide critical memory state in opaque blobs without schema discipline.

### References

- Story source and acceptance criteria: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Prior story context for summary-generation seam: [2-1-session-summary-generation-after-session-completion.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-1-session-summary-generation-after-session-completion.md)
- Closure seam now present in live code: [1-6-session-closure-with-takeaway-and-next-step-options.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-6-session-closure-with-takeaway-and-next-step-options.md)
- Product memory/privacy requirements: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Architecture memory boundary and retention guidance: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- Current session-state model: [models.py](/home/erda/Музыка/goals/backend/app/models.py)
- Current conversation handoff seam: [session_bootstrap.py](/home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py)
- Current empty memory package: [__init__.py](/home/erda/Музыка/goals/backend/app/memory/__init__.py)
- Existing Alembic baseline: [versions](/home/erda/Музыка/goals/backend/app/alembic/versions)
- Backend dependency policy: [pyproject.toml](/home/erda/Музыка/goals/backend/pyproject.toml)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-discovered from `_bmad-output/implementation-artifacts/sprint-status.yaml` as the first `ready-for-dev` story in order: `2-2-durable-memory-without-long-term-raw-transcript-storage`.
- Core source context loaded from `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, previous story file `2-1`, and the live backend codebase after Story 1.6 implementation.
- Live backend inspection confirmed Story 2.1 had already landed summary persistence primitives, but the durable boundary was still incomplete: no separate `ProfileFact` scope, no explicit transcript purge marker, and no structured retry payload for safe persistence recovery.
- The implementation extended the existing summary seam instead of replacing it: `ProfileFact` now lives alongside `SessionSummary`, and `TelegramSession` remains transient runtime state with explicit purge metadata.
- No `project-context.md` was found in the workspace.
- No usable local git metadata was available because `/home/erda/Музыка/goals` is not a git repository root.
- Latest framework verification used official documentation for FastAPI background-task boundaries, SQLModel request-scoped sessions, Pydantic Settings, PostgreSQL JSON data guidance, and `python-telegram-bot` compatibility.
- Added a second-stage durable memory migration to introduce `profile_fact`, lifecycle markers on `session_summary`, retry metadata on `summary_generation_signal`, and `transcript_purged_at` on `telegram_session`.
- Extended `memory/service.py` so persistence now upserts summaries and allowed profile facts together, clears transient transcript fields after the processing window, exposes transcript-free continuity overviews, and records bounded retry payloads without transcript fallback.
- Validation passed with `uv run alembic upgrade head`, `uv run ruff check app tests`, `uv run mypy app tests`, `uv run pytest tests/memory/test_summary.py tests/api/routes/test_telegram_session_entry.py -q`, and `ENABLE_LEGACY_WEB_ROUTES=true uv run pytest tests -q`.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story 2.2 is scoped as the durable-memory storage-boundary story: separate summary/profile scopes, transcript minimization, lifecycle metadata, and retry-safe persistence.
- Guardrails explicitly prevent turning `TelegramSession` into long-term memory or falling back to indefinite transcript retention when durable persistence fails.
- The story is optimized for live repo reality: create the first real `memory/` module boundary, use Alembic for schema evolution, keep Telegram routing thin, and stay compatible with future deletion workflows.
- The story also records the critical dependency nuance that `2-1` is not implemented yet, so developers must build a handoff-compatible storage layer without assuming finished summary-generation code already exists.
- Implemented separate durable scopes for `SessionSummary` and `ProfileFact`, including retention/deletion markers and transcript purge timestamps for future lifecycle workflows.
- Added conservative typed profile-fact promotion rules and a transcript-free continuity overview path for internal/operator use.
- Made durable-memory failure handling retry-safe and observable by upserting a single signal per session with attempt counts and structured retry payloads that exclude raw transcript data.
- Added regression coverage for separate scopes, transcript minimization after success and failure, lifecycle metadata, and transcript-free continuity access.
- Code review follow-up fixes landed: runtime now derives `allowed_profile_facts` at closure handoff, explicit handoff failures purge transient transcript fields, safe retry payloads include a bounded fallback summary draft, and ops continuity access is wired to a real endpoint.

### File List

- _bmad-output/implementation-artifacts/2-2-durable-memory-without-long-term-raw-transcript-storage.md
- backend/app/alembic/versions/c1d2e3f4a5b6_expand_durable_memory_boundary.py
- backend/app/core/config.py
- backend/app/conversation/session_bootstrap.py
- backend/app/memory/__init__.py
- backend/app/memory/schemas.py
- backend/app/memory/service.py
- backend/app/models.py
- backend/app/ops/signals.py
- backend/app/ops/api.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/api/routes/test_ops_routes.py
- backend/tests/conftest.py
- backend/tests/memory/test_summary.py

## Change Log

- 2026-03-12: Added a separate durable memory boundary for summaries and profile facts, lifecycle metadata and transcript purge markers, bounded retry payloads for persistence failures, and regression coverage for transcript minimization and transcript-free continuity access.
- 2026-03-12 (code-review): Fixed runtime profile-fact population, closed transcript-retention leak when background handoff fails, added bounded fallback retry payloads for pre-draft failures, and exposed transcript-free continuity access through ops API.

## Senior Developer Review (AI)

### Review Date

2026-03-12

### Reviewer

GPT-5 Codex

### Outcome

Approve

### Summary

Initial review found four material issues: runtime never populated `allowed_profile_facts`, the no-`BackgroundTasks` branch retained transcript fields, retry payloads were unsafe for pre-draft failures, and the transcript-free continuity access path existed only as an unused helper. All four issues were fixed and revalidated.

### Action Items

- [x] [high] Populate allowed profile facts from real closure/runtime context instead of test-only payload injection. [`backend/app/conversation/session_bootstrap.py`]
- [x] [high] Purge transient transcript fields when summary handoff fails before background execution starts. [`backend/app/conversation/session_bootstrap.py`]
- [x] [high] Ensure retry payload remains usable when failure happens before full summary draft generation. [`backend/app/memory/service.py`]
- [x] [medium] Wire transcript-free continuity overview into a real internal access path instead of leaving it unused. [`backend/app/ops/api.py`]

### Validation

- `uv run ruff check app tests`
- `uv run mypy app tests`
- `uv run pytest tests/memory/test_summary.py tests/api/routes/test_telegram_session_entry.py tests/api/routes/test_ops_routes.py -q`
- `ENABLE_LEGACY_WEB_ROUTES=true uv run pytest tests -q`

## Developer Context

### Technical Requirements

- Durable continuity memory must be centered on structured summary artifacts plus allowed profile facts, not on full transcript retention. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-22-Сохранение-durable-memory-без-долгого-хранения-raw-transcript]
- Raw messages are transient processing input and must age out once response and summary-generation needs are satisfied. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Technical-Constraints]
- Summary artifacts and profile facts need separate scopes. The storage model should make that distinction obvious in code and schema, not implicit in one overloaded record. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-22-Сохранение-durable-memory-без-долгого-хранения-raw-transcript]
- Durable artifacts need lifecycle metadata so Epic 6 deletion flows can delete or update them later without transcript spelunking.
- Failure handling must be retry-safe and observable. “Keep the transcript forever just in case” is explicitly the wrong fallback.
- The current `TelegramSession` fields are runtime convenience state, not durable memory design. Treat them as transient by default.

### Architecture Compliance

- Keep durable memory in `memory/`, not in `bot/` or as an accidental side-effect of `conversation/`. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Structure--Boundaries]
- Architecture explicitly requires transcript minimization, durable summary/profile retention, and operator visibility without routine transcript exposure. Story 2.2 should satisfy all three together rather than optimizing for one at the expense of the others. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Context-Analysis]
- Use a clean async/post-response seam for memory persistence handoff, but do not hardcode all persistence logic into request transport. [Inference from architecture async-enrichment guidance and live repo structure]
- The architecture names `summary.generated` and `profile.updated` as domain-style events. If the implementation adds internal signaling, prefer fact-style names and idempotent handling over command-style helpers. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Implementation-Patterns--Consistency-Rules]
- Repo reality overrides aspirational stack changes. The live backend still uses SQLModel and Alembic; Story 2.2 should extend those seams rather than forcing a persistence-stack rewrite.

### Library / Framework Requirements

- Use the current backend stack from [pyproject.toml](/home/erda/Музыка/goals/backend/pyproject.toml): FastAPI, SQLModel, Alembic, `pydantic-settings`, PostgreSQL via `psycopg`, and `python-telegram-bot`.
- SQLModel’s official FastAPI guidance still supports request-scoped sessions via dependency injection, which is the right persistence baseline for current repo patterns. Official docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Pydantic Settings remains the existing config seam. If retention windows, purge toggles, or feature flags are added, keep them in `backend/app/core/config.py` instead of ad hoc module constants. Official docs: https://docs.pydantic.dev/latest/api/pydantic_settings/
- PostgreSQL current docs continue to position `jsonb` as the structured JSON storage type with indexing/operator support; if summary/profile payloads are stored as JSON rather than fully normalized columns, prefer `jsonb` over plain `json` and keep payload structure typed at the application boundary. Official docs: https://www.postgresql.org/docs/current/datatype-json.html
- FastAPI background-task docs remain relevant for the handoff boundary from request path to post-response work, but Story 2.2 should not confuse “background” with “durably stored forever.” Official docs: https://fastapi.tiangolo.com/tutorial/background-tasks/
- The repo pins `python-telegram-bot<22.0,>=21.6`. This story should not introduce v22-only transport assumptions while working on persistence boundaries. Official docs: https://docs.python-telegram-bot.org/en/v21.11.1/

### File Structure Requirements

- Primary implementation files should stay within:
  - `backend/app/memory/*.py`
  - `backend/app/models.py`
  - `backend/app/alembic/versions/*.py`
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/core/config.py`
  - `backend/tests/memory/`
  - `backend/tests/api/routes/` and `backend/tests/conversation/` for handoff/regression coverage
- Likely files to touch:
  - `backend/app/memory/__init__.py`
  - new durable-memory service/schema/repository modules under `backend/app/memory/`
  - `backend/app/models.py`
  - one or more new Alembic migrations
  - `backend/app/conversation/session_bootstrap.py` only where the handoff boundary needs to call memory persistence
  - memory-specific tests
- Avoid pushing durable-memory retention rules into `backend/app/bot/api.py` or hiding them inside generic utilities.

### Testing Requirements

- Add or update tests for:
  - summary artifacts and profile facts persist into separate durable scopes
  - raw transcript fields are not used as the main durable memory artifact
  - transcript-minimization occurs after the processing window
  - persistence failure creates observable retry/failure behavior without indefinite transcript retention
  - lifecycle metadata supports later update/delete behavior
  - routine access paths use summary/profile metadata rather than transcript exposure
- Keep route-level coverage only where orchestration boundaries are affected; most new tests should live under a dedicated memory-focused suite.
- Reuse the backend validation toolchain from [pyproject.toml](/home/erda/Музыка/goals/backend/pyproject.toml): `pytest`, `ruff`, and `mypy`.

### Previous Story Intelligence

- Story 2.1 already framed the intended storage contract: structured summary artifact, conservative wording for uncertainty, and no transcript dump. Story 2.2 should be the persistence layer that makes those rules enforceable in the database model. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-1-session-summary-generation-after-session-completion.md]
- Story 1.6 is now implemented and gives a live closure seam plus completed-session status. That is the actual runtime handoff point available today, even though no durable memory code exists yet. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Current repo state still only stores transient conversation fields on `TelegramSession`. That is a warning sign, not a model to expand into long-term memory.
- Because `2-1` is not implemented yet, the developer should create a persistence boundary that can accept a future structured summary payload without hard-wiring itself to a temporary placeholder transcript model.

### Git Intelligence Summary

- No commit intelligence was available because the workspace path is not a git repository root.

### Project Context Reference

- No `project-context.md` was found in the workspace. The authoritative implementation context is `epics.md`, `prd.md`, `architecture.md`, `2-1-session-summary-generation-after-session-completion.md`, the implemented Story 1.6 closure seam, and the live backend codebase.

### Library / Framework Latest Information

- SQLModel’s FastAPI session-dependency pattern remains current and matches this repo’s existing request/session style. Official docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Pydantic Settings still exposes the supported `BaseSettings` path for environment-backed runtime config, which is the right place for retention-window or purge controls. Official docs: https://docs.pydantic.dev/latest/api/pydantic_settings/
- PostgreSQL current docs continue to recommend `jsonb` when structured JSON must be stored with querying/indexing support; that is the relevant persistence option if summary/profile artifacts are kept as structured payloads. Official docs: https://www.postgresql.org/docs/current/datatype-json.html
- FastAPI’s background-task docs still define the post-response boundary story 2.1 depends on, but Story 2.2 must convert that boundary into a disciplined persistence model rather than a loose background side effect. Official docs: https://fastapi.tiangolo.com/tutorial/background-tasks/
