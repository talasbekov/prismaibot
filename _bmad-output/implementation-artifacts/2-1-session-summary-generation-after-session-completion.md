# Story 2.1: Генерация session summary после завершения сессии

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь, который завершил reflective session,
I want чтобы продукт создавал краткое структурированное summary моей сессии,
so that в будущем разговор может продолжиться с учетом уже разобранного контекста.

## Acceptance Criteria

1. When the product detects a suitable closure point and the final user-facing response has already been sent, it starts session-summary generation as a post-response process and does not block the reply path. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-21-Генерация-session-summary-после-завершения-сессии]
2. When the durable summary artifact is produced, it preserves key facts, main emotional tensions, and relevant next-step context from the session without becoming a raw transcript dump or long freeform retelling. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-21-Генерация-session-summary-после-завершения-сессии]
3. When session summary is created for continuity, it follows a predictable structured schema that is suitable for later machine use in session recall. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-21-Генерация-session-summary-после-завершения-сессии]
4. When the session contains noise, contradictions, or unresolved details, the summary uses cautious wording for uncertain points and does not lock ambiguous conclusions in as facts. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-21-Генерация-session-summary-после-завершения-сессии]
5. If the generation pipeline fails fully or partially and the system cannot persist the summary, the already completed user session still remains intact and the system emits a retry or failure signal rather than silently losing the work. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-21-Генерация-session-summary-после-завершения-сессии]
6. When the product stores summary as a durable memory artifact in a privacy-sensitive domain, it keeps only continuity-relevant information and does not retain unnecessary raw message fragments without explicit need. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-21-Генерация-session-summary-после-завершения-сессии]

## Tasks / Subtasks

- [x] Add an explicit post-closure summary orchestration seam that runs after the final Telegram reply is already assembled and returned (AC: 1, 5)
  - [x] Keep `/api/v1/telegram/webhook` thin in `backend/app/bot/api.py`; the route should still delegate to `conversation/` and should not become the summary pipeline itself.
  - [x] Extend `backend/app/conversation/session_bootstrap.py` or an adjacent orchestrator so closure can trigger a summary job/hand-off after user-visible completion.
  - [x] Use a request-safe async seam that does not delay the final response path and leaves room for later extraction into `jobs/` without rewriting the domain logic.
- [x] Define a typed session-summary contract optimized for continuity rather than transcript replay (AC: 2, 3, 4, 6)
  - [x] Introduce product-aligned summary schemas under `backend/app/memory/` or `backend/app/schemas/` for key facts, emotional tensions, uncertainty notes, and next-step context.
  - [x] Reuse closure-stage understanding from Story 1.6 and accumulated session context from Stories 1.4-1.5 instead of reconstructing everything from raw user prose alone.
  - [x] Make uncertainty explicit in schema fields or wording rules so unresolved points stay tentative.
- [x] Persist durable summary artifacts with observable failure handling (AC: 1, 3, 5, 6)
  - [x] Add product-aligned persistence for summaries, including migration(s) if new tables or fields are required.
  - [x] Keep durable summary storage separate from transient message-processing state so Epic 2 can grow into summary/profile memory rather than transcript retention.
  - [x] Emit a visible retry/failure signal on persistence or generation failure using an existing ops-compatible seam instead of silent logging only.
- [x] Enforce privacy and retention guardrails in the first memory artifact (AC: 2, 4, 6)
  - [x] Store only continuity-relevant material; do not persist raw message dumps as the durable artifact.
  - [x] Ensure the summary format avoids invented certainty, diagnosis-like phrasing, and over-specific claims not grounded in the completed session.
  - [x] Keep the implementation compatible with later deletion and retention workflows from Epic 6.
- [x] Cover summary generation with backend tests and regressions (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add unit tests for summary schema generation, including noisy/contradictory sessions and uncertainty handling.
  - [x] Add route or orchestration tests proving the final Telegram reply completes even when summary generation is scheduled or when summary persistence fails.
  - [x] Add persistence tests for summary artifact creation and retry/failure signaling.
  - [x] Run backend validation with `pytest`, `ruff`, and `mypy`.

## Dev Notes

- Story 2.1 is the first durable-memory story. It should attach to the session-completion seam created by Epic 1 rather than inventing a separate "memory mode" or a second Telegram runtime path. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-6-session-closure-with-takeaway-and-next-step-options.md]
- The PRD makes summary correctness a top technical success criterion. A wrong summary damages future continuity and therefore the product’s trust and monetization model, so conservative generation matters more than maximal detail. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Technical-Success]
- Architecture explicitly requires asynchronous post-response enrichment for summary/profile updates so memory work does not block the trust-sensitive conversational reply path. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Infrastructure--Deployment]
- Raw transcript minimization is not optional. Epic 2 is designed around durable summary artifacts plus later profile facts, not around retaining full conversations for convenience. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Technical-Constraints]
- UX already warns against treating the session ending as "just a generated summary". Story 2.1 therefore must treat the user-facing closure and the machine-oriented durable artifact as related but different outputs. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#Executive-Summary]
- Live repo reality matters: `backend/app/memory/__init__.py` is still empty, there is no summary implementation yet, and current Telegram session state lives in `backend/app/models.py` and `backend/app/conversation/session_bootstrap.py`. This story should establish the first real memory seam instead of scattering summary logic across unrelated modules.

### Project Structure Notes

- Primary touch points should remain inside:
  - `backend/app/bot/api.py`
  - `backend/app/conversation/session_bootstrap.py`
  - new modules under `backend/app/memory/`
  - `backend/app/models.py` and `backend/app/alembic/versions/` if durable summary persistence is introduced
  - `backend/app/ops/` or a small product-aligned signaling seam if failure visibility is added
  - `backend/tests/api/routes/`, `backend/tests/conversation/`, and likely new `backend/tests/memory/`
- Keep transport, conversation, and memory boundaries clear:
  - `bot/` should accept and return Telegram payloads
  - `conversation/` should decide when the session is complete and hand off summary work
  - `memory/` should own summary schema, generation, and persistence
- The architecture document proposes a larger future structure, but the live backend still uses `backend/app/...` with SQLModel-based models. Extend the real structure incrementally; do not force a repo-wide reorganization in Story 2.1.
- If new persistence is required, use the existing Alembic flow already present in `backend/app/alembic/` rather than introducing ad hoc schema bootstrapping.

### References

- Story source and acceptance criteria: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Product requirements and memory/privacy constraints: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Architecture async-enrichment and module-boundary guidance: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- UX distinction between closure and generated summary: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)
- Immediate handoff from closure story: [1-6-session-closure-with-takeaway-and-next-step-options.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-6-session-closure-with-takeaway-and-next-step-options.md)
- Live Telegram ingress seam: [api.py](/home/erda/Музыка/goals/backend/app/bot/api.py)
- Live session orchestration seam: [session_bootstrap.py](/home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py)
- Current model and persistence baseline: [models.py](/home/erda/Музыка/goals/backend/app/models.py)
- Current runtime settings seam: [config.py](/home/erda/Музыка/goals/backend/app/core/config.py)
- Backend dependency policy: [pyproject.toml](/home/erda/Музыка/goals/backend/pyproject.toml)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-discovered from `_bmad-output/implementation-artifacts/sprint-status.yaml` as the first `ready-for-dev` story in order: `2-1-session-summary-generation-after-session-completion`.
- Core source context loaded from `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, and the completed/ready Epic 1 stories, especially Story 1.6.
- Live backend inspection confirmed the current product runtime already has `bot/`, `conversation/`, `ops/`, and an empty `memory/` seam under `backend/app/`.
- No `project-context.md` was found in the workspace.
- No usable local git history was available because `/home/erda/Музыка/goals` is not a git repository root.
- Latest framework verification used official documentation for FastAPI background tasks, SQLModel request-scoped sessions, Pydantic Settings, and `python-telegram-bot` version compatibility.
- Added a post-response summary handoff from `conversation/session_bootstrap.py` into a new `memory` seam using FastAPI `BackgroundTasks`, while keeping the Telegram route thin.
- Added durable `session_summary` storage plus `summary_generation_signal` failure visibility with an Alembic migration and SQLModel models.
- Full validation passed after migration: `uv run ruff check app tests`, `uv run mypy app tests`, `uv run pytest tests/memory/test_summary.py tests/api/routes/test_telegram_session_entry.py -q`, `ENABLE_LEGACY_WEB_ROUTES=true uv run pytest tests -q`.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story 2.1 is scoped as post-response summary generation for continuity, not as profile-fact promotion, future-session recall, billing, or safety escalation.
- Guardrails emphasize typed summary artifacts, conservative wording for uncertainty, transcript minimization, and observable failure handling.
- The story is optimized for the live repo shape: strengthen `conversation/` handoff into a new `memory/` seam, keep the Telegram route thin, and use Alembic plus SQLModel for durable artifacts if persistence is added.
- Because there is no local git metadata, commit-intelligence guidance is unavailable; current code inspection replaces it.
- Implemented `SessionSummaryPayload`/`SessionSummaryDraft` contracts and a summary builder that stores only structured continuity material: takeaway, key facts, emotional tensions, uncertainty notes, and next-step context.
- Added `SessionSummary` persistence and `SummaryGenerationSignal` retry/failure records so completed sessions survive summary-generation errors without silent loss.
- Extended Telegram session-entry tests with closure-summary persistence, background scheduling, and failure-signal coverage, and added dedicated memory tests for schema behavior and transcript minimization.

### File List

- _bmad-output/implementation-artifacts/2-1-session-summary-generation-after-session-completion.md
- backend/app/alembic/versions/6f7c4d21a8b9_add_session_summary_and_failure_signal_tables.py
- backend/app/bot/api.py
- backend/app/conversation/session_bootstrap.py
- backend/app/memory/__init__.py
- backend/app/memory/schemas.py
- backend/app/memory/service.py
- backend/app/models.py
- backend/app/ops/signals.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/conftest.py
- backend/tests/memory/test_summary.py

## Change Log

- 2026-03-12: Added post-response session-summary generation, durable summary persistence, observable failure signaling, Alembic migration, and backend regression coverage for Epic 2 Story 2.1.
- 2026-03-12 (code-review): Fixed H1 — record failure signal when background_tasks is None; H2 — replaced English "tentative" with Russian "условный"; H3 — added takeaway[:1000] truncation guard. Fixed M1 — removed clarification.py from File List (no Story 2.1 changes); M2 — aligned _LOW_CONFIDENCE_MARKERS with clarification.py marker set; M3 — added upsert update-path test; M4 — added resolve_summary_signal to ops/signals.py.

## Developer Context

### Technical Requirements

- Summary generation must happen only after the user-facing closure is already completed. The durable summary artifact is a post-response continuity object, not part of the interactive chat turn itself. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-21-Генерация-session-summary-после-завершения-сессии]
- The artifact must stay compact and structured: key facts, main emotional tensions, and next-step context are in scope; transcript replay is out of scope. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-21-Генерация-session-summary-после-завершения-сессии]
- Memory correctness outranks completeness. If a point is uncertain, the durable artifact should encode that uncertainty rather than fabricate a stable fact. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Technical-Success]
- Summary generation must not degrade the main latency target or destabilize the completed session. NFR2 explicitly forbids blocking the primary reply path. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Non-Functional-Requirements]
- The product remains non-medical. Durable summary text must avoid diagnosis-like labels, treatment framing, or claims that sound stronger than what the conversation actually established. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Compliance--Regulatory]
- Privacy scope is narrow by design. Raw conversational fragments should not be kept as the durable memory artifact unless a clearly justified processing need exists. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Technical-Constraints]

### Architecture Compliance

- Keep Telegram transport in `bot/`, completion/hand-off logic in `conversation/`, and durable summary generation in `memory/`; do not let one module absorb all three responsibilities. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Structure--Boundaries]
- Treat summary generation as asynchronous post-response enrichment, consistent with the architecture’s async boundary rules. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Infrastructure--Deployment]
- The architecture prefers summary/profile storage as the durable memory boundary. Story 2.1 should reinforce that model and avoid normalizing transcript retention for convenience. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Context-Analysis]
- Failure handling should be observable. Architecture explicitly calls out summary/profile update failures as operator-visible signals, not just logs nobody checks. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Infrastructure--Deployment]
- Repo reality overrides aspirational stack drift when they conflict. The architecture text prefers SQLAlchemy 2 directly, but the live repo currently uses SQLModel; implement Story 2.1 against the working codebase rather than bundling an ORM migration into a memory story.

### Library / Framework Requirements

- Use the current backend stack from [pyproject.toml](/home/erda/Музыка/goals/backend/pyproject.toml): FastAPI, SQLModel, Alembic, `pydantic-settings`, and `python-telegram-bot`.
- FastAPI’s official background-task guidance is the relevant baseline for "do not block the main response path"; if the task grows too heavy or reliability-sensitive, keep the seam extractable rather than baking long-running work into the request handler forever. Official docs: https://fastapi.tiangolo.com/tutorial/background-tasks/
- SQLModel’s official FastAPI guidance still supports one session per request via dependency injection, which fits the current repo’s `SessionDep` pattern when handing off or persisting summary artifacts. Official docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Pydantic Settings remains the environment-backed settings mechanism already used in `backend/app/core/config.py`. If summary generation needs limits, toggles, or retention windows, keep them in the settings seam rather than module-level constants. Official docs: https://docs.pydantic.dev/latest/api/pydantic_settings/
- The repo pins `python-telegram-bot<22.0,>=21.6`. Stable upstream docs are on the v22 line, so do not introduce v22-only APIs or assumptions while implementing Story 2.1 unless dependency policy changes first. Official docs: https://docs.python-telegram-bot.org/en/v21.11.1/

### File Structure Requirements

- Primary implementation files should stay within:
  - `backend/app/bot/api.py`
  - `backend/app/conversation/session_bootstrap.py`
  - new `backend/app/memory/*.py` modules
  - `backend/app/models.py`
  - `backend/app/alembic/versions/*.py`
  - `backend/app/core/config.py`
  - `backend/tests/api/routes/`
  - `backend/tests/conversation/`
  - likely new `backend/tests/memory/`
- Likely files to touch:
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/memory/__init__.py`
  - one or more new summary-specific modules under `backend/app/memory/`
  - `backend/app/models.py`
  - a new Alembic migration for summary persistence if durable storage is introduced in this story
  - Telegram route and memory/orchestration tests
- Avoid placing summary policy in legacy auth/users/items modules or hiding summary generation inside generic utility files.

### Testing Requirements

- Add or update tests for:
  - summary generation starts only after closure and does not block the main Telegram reply path
  - structured summary schema contains facts, emotional tensions, next-step context, and uncertainty handling
  - contradictory/noisy sessions produce tentative summary wording rather than false certainty
  - persistence failure emits a visible retry/failure path without corrupting the completed session
  - transcript minimization rules prevent raw-message-dump durable artifacts
- Keep route-level coverage on `/api/v1/telegram/webhook` and add focused memory tests for schema generation and persistence.
- Reuse the backend validation toolchain from [pyproject.toml](/home/erda/Музыка/goals/backend/pyproject.toml): `pytest`, `ruff`, and `mypy`.

### Previous Story Intelligence

- Story 1.6 already established a closure-stage structure and explicitly warned that Epic 2 should reuse closure-stage understanding instead of re-deriving summary data from scratch. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-6-session-closure-with-takeaway-and-next-step-options.md]
- Stories 1.4 and 1.5 already maintain a progressively updated reflective understanding in `session_bootstrap.py` and related conversation helpers. Story 2.1 should build on that state, not bypass it. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- The current repo already stores `working_context`, `last_user_message`, and `last_bot_prompt` on `TelegramSession`. That is enough to prototype a first summary seam, but not enough to justify keeping full transcript history as durable memory. [Source: /home/erda/Музыка/goals/backend/app/models.py]
- `backend/app/memory/` exists but is currently empty. That makes Story 2.1 the right place to create the first true memory module boundary rather than extending `conversation/` indefinitely.

### Git Intelligence Summary

- No commit intelligence was available because the workspace path is not a git repository root.

### Project Context Reference

- No `project-context.md` was found in the workspace. The authoritative implementation context is `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, Story 1.6, and the live backend codebase.

### Library / Framework Latest Information

- FastAPI officially documents `BackgroundTasks` for work that should run after returning a response, which aligns with Story 2.1’s post-response summary trigger requirement. For heavier work, keep the seam extractable rather than coupling long-running generation permanently to the request lifecycle. Official docs: https://fastapi.tiangolo.com/tutorial/background-tasks/
- SQLModel’s FastAPI tutorial continues to document request-scoped session injection as the normal persistence pattern, which matches the current `SessionDep` approach in `backend/app/api/deps.py`. Official docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Pydantic Settings still exposes `BaseSettings` as the supported config entry point in current docs, which matches the live `Settings` model already used in `backend/app/core/config.py`. Official docs: https://docs.pydantic.dev/latest/api/pydantic_settings/
- `python-telegram-bot` maintains 21.11.1 docs for the currently pinned compatibility line. Use that line as the implementation ceiling unless the project deliberately upgrades to v22+. Official docs: https://docs.python-telegram-bot.org/en/v21.11.1/
