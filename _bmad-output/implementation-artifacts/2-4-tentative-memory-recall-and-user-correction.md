# Story 2.4: Tentative memory recall и корректировка пользователем

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a returning user,
I want чтобы бот вспоминал прошлый контекст осторожно и позволял мне легко его скорректировать,
so that continuity feels helpful rather than creepy or overconfident.

## Acceptance Criteria

1. When the product uses prior memory in a new session and the bot references earlier context, the recall phrasing must sound tentative rather than absolute and must not create an omniscient or surveillance-like impression. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-24-Tentative-memory-recall-и-корректировка-пользователем] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
2. When the bot mentions saved prior context and the user explicitly or implicitly indicates that the memory is inaccurate, stale, or not relevant, the system accepts the correction without defensiveness and immediately yields to the user’s new framing. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-24-Tentative-memory-recall-и-корректировка-пользователем] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
3. When memory recall is partially wrong and the user continues after correcting it, the reflective flow must proceed on the updated user context and must not keep restating the incorrect prior memory as true. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-24-Tentative-memory-recall-и-корректировка-пользователем] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
4. When confidence in retrieved memory is low or the relevance to the current situation is uncertain, the system either uses more cautious phrasing or avoids surfacing that memory explicitly and limits it to internal relevance shaping. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-24-Tentative-memory-recall-и-корректировка-пользователем] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
5. When a user is sensitive to how the product “remembers” prior conversations, recall language must remain supportive, humble, and low-pressure so continuity reduces effort without increasing discomfort or tension. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-24-Tentative-memory-recall-и-корректировка-пользователем] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
6. When the session is already progressing naturally without any need for explicit memory mention, the system may still use prior memory internally to improve relevance but is not required to announce that it remembers something every time. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-24-Tentative-memory-recall-и-корректировка-пользователем] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]

## Tasks / Subtasks

- [x] Add tentative recall decisioning on top of the existing Story 2.3 recall seam instead of changing durable-memory ownership (AC: 1, 4, 6)
  - [x] Extend the conversation-layer first-turn flow so explicit memory mention is optional and triggered only when confidence/relevance is high enough for a trust-safe user-facing cue.
  - [x] Keep support for internal-only recall usage when prior memory should improve relevance silently without explicit “I remember” phrasing.
  - [x] Preserve the current clean-session fallback when no usable recall context exists.
- [x] Introduce correction-aware recall handling in the reflective flow (AC: 2, 3, 6)
  - [x] Detect explicit and implicit user correction signals after a memory-informed opening or early turn.
  - [x] Update the active session context so the corrected user framing becomes the current source of truth for subsequent turns.
  - [x] Prevent previously surfaced incorrect memory from being repeated as if still valid after correction.
- [x] Add language guardrails for tentative, non-creepy continuity behavior (AC: 1, 4, 5, 6)
  - [x] Implement phrasing rules that prefer humble wording such as partial recognition, uncertainty, or soft recall over absolute claims.
  - [x] Suppress explicit recall phrasing entirely when confidence is low, relevance is weak, or the conversation is already progressing naturally without it.
  - [x] Keep the trust-making first response emotionally soft and non-defensive even when memory is later corrected.
- [x] Keep the implementation within the existing module boundaries and data constraints (AC: 1, 3, 4, 6)
  - [x] Reuse `memory/` as the provider of bounded recall context and keep user-facing recall policy in `conversation/`.
  - [x] Do not introduce transcript-based recall, vector retrieval, or new long-term storage behavior for this story.
  - [x] Avoid moving continuity logic into Telegram transport or route handlers.
- [x] Add regression coverage for tentative recall, correction, and fallback behavior (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add tests for explicit tentative recall wording when confidence is sufficient and the cue is appropriate.
  - [x] Add tests for low-confidence or low-relevance scenarios where recall stays internal and is not surfaced explicitly.
  - [x] Add tests for user correction causing the flow to yield immediately and stop reinforcing the old memory framing.
  - [x] Add tests proving the system remains supportive rather than defensive or surveillance-like when memory is corrected.
  - [x] Run backend validation with `pytest`, `ruff`, and `mypy`.

## Dev Notes

- Story 2.3 already introduced the bounded recall path: `get_session_recall_context()` in `backend/app/memory/service.py`, first-turn recall loading in `backend/app/conversation/session_bootstrap.py`, and memory-aware first-response phrasing in `backend/app/conversation/first_response.py`. Story 2.4 should refine how that recall is surfaced and corrected, not redesign the read model. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-3-using-prior-memory-at-the-start-of-a-new-session.md] [Source: /home/erda/Музыка/goals/backend/app/memory/service.py] [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- The current implementation already merges prior recall into `working_context` on the first turn and intentionally avoids re-injecting `prior_memory_context` into each later clarification turn. That comment in `session_bootstrap.py` is the exact seam Story 2.4 should evolve. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- The first meaningful response remains the trust-making moment. Any explicit recall wording must stay emotionally soft and optional; low-confidence or weakly relevant recall should stay internal-only instead of being surfaced to the user. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Story 2.4 is where explicit tentative phrasing and correction-yield behavior should land. Story 2.3 deliberately left that work unfinished so the team could add it without entangling the basic recall path. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-24-Tentative-memory-recall-и-корректировка-пользователем]
- Do not regress the core privacy and MVP memory constraints: no transcript-based durable recall, no vector-first retrieval in the request path, and no new long-term storage for raw conversational fragments. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Technical-Constraints] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Existing tests already cover first-response behavior, returning-user recall, recall failure fallback, and active-session no-reload behavior. Extend these instead of inventing a parallel test stack. [Source: /home/erda/Музыка/goals/backend/tests/conversation/test_first_response.py] [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py]

## Developer Context

### Technical Requirements

- Treat prior memory as support context rather than truth. Explicit recall must be tentative, corrigible, and subordinate to the user’s current message. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-24-Tentative-memory-recall-и-корректировка-пользователем]
- Add explicit and implicit correction handling so that once the user reframes the situation, the flow immediately follows the new framing and stops reinforcing the old recall. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-24-Tentative-memory-recall-и-корректировка-пользователем] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Keep explicit recall optional. If confidence is low or relevance is uncertain, use memory internally for response relevance or omit the cue entirely. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-24-Tentative-memory-recall-и-корректировка-пользователем]
- Preserve the current no-memory and recall-failure fallback paths so the user never sees a technical failure or a false “I remember” claim. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-3-using-prior-memory-at-the-start-of-a-new-session.md]
- Keep the trust-making first response calm, non-defensive, and non-surveillance-like even when recall is surfaced or later corrected. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]

### Architecture Compliance

- `memory/` remains the owner of summaries, profile facts, and bounded recall payload generation. Story 2.4 should not move user-facing policy or correction logic into `memory/`. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- `conversation/` owns recall surfacing, phrasing, correction handling, and context updates during the live reflective flow. That is where this story should primarily land. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md] [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- `bot/` must stay a transport boundary. Do not solve this story by embedding memory policy into webhook or route handlers. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Keep request-path work bounded. This is a trust-sensitive latency path, so avoid turning confidence/relevance into a heavy scoring subsystem for MVP. Inference can stay lightweight and deterministic. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

### Library / Framework Requirements

- Stay on the current backend stack declared in `backend/pyproject.toml`: FastAPI, SQLModel, Alembic, `pydantic-settings`, PostgreSQL via `psycopg`, and `python-telegram-bot` `<22`. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- FastAPI’s official `BackgroundTasks` guidance remains relevant to post-response summary generation, but Story 2.4 should not move recall handling into background work because correction-sensitive memory phrasing happens on the live request path. Source: https://fastapi.tiangolo.com/tutorial/background-tasks/
- SQLModel’s FastAPI session-dependency pattern remains the correct way to access recall data in request handling; keep recall reads inside the existing request-scoped session flow. Inference from official docs plus current repo usage. Source: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Keep configuration toggles or thresholds, if any are introduced, in the existing Pydantic Settings seam rather than scattered constants. Source: https://docs.pydantic.dev/latest/api/pydantic_settings/
- The repo remains pinned to `python-telegram-bot` `>=21.6,<22.0`; avoid adding assumptions from newer major versions while touching Telegram-entry behavior. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]

### File Structure Requirements

- Primary implementation files are likely:
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/conversation/first_response.py`
  - `backend/app/conversation/clarification.py`
  - `backend/app/memory/service.py` only if the bounded recall payload needs a small extension
  - `backend/app/memory/schemas.py` only if a lightweight recall-confidence hint or similar typed field is required
- Primary test files are likely:
  - `backend/tests/api/routes/test_telegram_session_entry.py`
  - `backend/tests/conversation/test_first_response.py`
  - `backend/tests/memory/test_summary.py` if recall payload semantics need direct unit coverage
- Avoid putting Story 2.4 behavior into:
  - `backend/app/bot/api.py`
  - new transport-specific helpers
  - any transcript storage or retrieval path

### Testing Requirements

- Add tests for tentative explicit recall wording that sounds soft rather than absolute.
- Add tests for explicit correction and implicit correction where the next turn yields to the user’s new framing.
- Add tests that wrong memory, once corrected, is not repeated confidently in subsequent turns.
- Add tests for low-confidence recall suppression where continuity stays internal-only.
- Keep the existing clean-session fallback and recall-failure fallback green.
- Run the normal backend quality bar: `pytest`, `ruff`, and `mypy`.

### Previous Story Intelligence

- Story 2.3 already solved retrieval and fresh-session continuity. The unresolved part is behavioral trust: when to say memory aloud, how tentative it should sound, and how to recover cleanly when the user corrects it. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-3-using-prior-memory-at-the-start-of-a-new-session.md]
- `compose_first_trust_response_with_memory()` currently has a binary “recurring” hint via `_looks_recurring(prior_memory_context)`. Story 2.4 is the natural place to make recall phrasing more nuanced without breaking the deterministic placeholder architecture. [Source: /home/erda/Музыка/goals/backend/app/conversation/first_response.py]
- `compose_clarification_response()` already contains low-confidence logic and context-merging behavior. It is a strong candidate for correction-aware yielding and suppression of stale memory framing after the first turn. [Source: /home/erda/Музыка/goals/backend/app/conversation/clarification.py]
- The route tests already verify recall fallback and active-session behavior. Extend those paths to prove trust is preserved when memory is surfaced and then corrected. [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py]

### Git Intelligence Summary

- No git history was available from `/home/erda/Музыка/goals`, so there was no commit-level pattern analysis for this story.

### Library / Framework Latest Information

- FastAPI still positions `BackgroundTasks` as post-response work, which reinforces that recall phrasing and correction handling belong on the request path, not deferred after the user reply. Source: https://fastapi.tiangolo.com/tutorial/background-tasks/
- SQLModel’s current FastAPI guidance still centers on dependency-injected request sessions, which matches the existing `session_bootstrap.py` recall lookup shape. Source: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Pydantic Settings still documents the central settings seam for env-backed config. If a threshold for explicit recall is added, keep it there rather than scattering magic numbers. Source: https://docs.pydantic.dev/latest/api/pydantic_settings/

### Project Structure Notes

- The live repo already has the right structural seams for this story:
  - `conversation/` for first-turn and clarification behavior
  - `memory/` for recall payload generation
  - route tests for end-to-end session-entry behavior
- There is no need for a new module family. If a helper is needed, keep it small and adjacent to the current conversation logic instead of introducing a new orchestration layer.
- The only structural risk is mixing policy and data ownership. Keep recall selection/data shaping in `memory/`, but keep tentative phrasing, suppression, and correction-yield behavior in `conversation/`.

### References

- Story source and acceptance criteria: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Product requirements and memory constraints: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Architecture boundaries and module ownership: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- UX trust and memory phrasing rules: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)
- Previous story context: [2-3-using-prior-memory-at-the-start-of-a-new-session.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-3-using-prior-memory-at-the-start-of-a-new-session.md)
- Live first-turn orchestration seam: [session_bootstrap.py](/home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py)
- Live first-response phrasing seam: [first_response.py](/home/erda/Музыка/goals/backend/app/conversation/first_response.py)
- Live clarification seam: [clarification.py](/home/erda/Музыка/goals/backend/app/conversation/clarification.py)
- Live recall payload generation: [service.py](/home/erda/Музыка/goals/backend/app/memory/service.py)
- Live recall schemas: [schemas.py](/home/erda/Музыка/goals/backend/app/memory/schemas.py)
- Existing route-level behavior tests: [test_telegram_session_entry.py](/home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py)
- Existing first-response tests: [test_first_response.py](/home/erda/Музыка/goals/backend/tests/conversation/test_first_response.py)
- Existing recall payload tests: [test_summary.py](/home/erda/Музыка/goals/backend/tests/memory/test_summary.py)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-discovered from `/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog story in order: `2-4-tentative-memory-recall-and-user-correction`.
- Core context loaded from `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, previous story `2-3`, and live backend seams in `conversation/` and `memory/`.
- The create-story workflow was executed with interactive checkpoints until the user selected YOLO mode for the rest of the document.
- Party mode was invoked twice during the document creation process to review the story header/requirements and then the implementation tasks; the resulting guidance was folded into the story.
- No `project-context.md` was found in the workspace.
- No git history was available because `/home/erda/Музыка/goals` is not a git repository root.
- The workflow step that references `_bmad/core/tasks/validate-workflow.xml` could not be executed literally because that file does not exist in the workspace.
- Web verification was used only for current official framework guidance around FastAPI background tasks, SQLModel request-session usage, and Pydantic Settings. The SQLModel and Pydantic references are used as architecture guidance; the explicit implementation direction is still anchored in the local repo.
- Dev workflow auto-selected this story as the first `ready-for-dev` entry and updated sprint tracking to `in-progress` before implementation.
- Added failing tests first in `backend/tests/conversation/test_first_response.py` and `backend/tests/api/routes/test_telegram_session_entry.py` for tentative recall surfacing, low-confidence suppression, and correction-yield behavior.
- Validation used an isolated temporary Postgres container on port `5433` because `localhost:5432` is occupied by an unrelated container with incompatible credentials.
- Validation commands executed:
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run alembic upgrade head`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest tests/conversation/test_first_response.py tests/api/routes/test_telegram_session_entry.py -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest tests -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 ENABLE_LEGACY_WEB_ROUTES=true uv run pytest tests -q`
  - `uv run ruff check app tests`
  - `uv run mypy app tests`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story 2.4 is explicitly scoped as a behavioral refinement on top of Story 2.3’s recall seam, not as a new memory architecture story.
- The implementation focus is tentative recall phrasing, selective explicit recall surfacing, immediate yielding on correction, and suppression of stale memory reinforcement after correction.
- Guardrails explicitly prohibit transcript-based recall expansion, transport-layer memory policy, and overengineered confidence-scoring subsystems in MVP.
- Existing tests and live seams were identified so the dev agent can extend current behavior rather than reinventing flow boundaries.
- Added deterministic recall classification in `first_response.py` so recurring prior context is surfaced only when it is strong enough for a trust-safe tentative cue; otherwise it stays internal-only.
- Added correction-aware handling in `clarification.py` so explicit memory corrections reset the active session context to the user’s current framing and avoid repeating stale recall.
- Added regression tests covering tentative first-turn recall, suppression under weak confidence, and second-turn correction yielding.
- Full backend validation passed with isolated Postgres on port `5433`, including normal and legacy-route pytest runs, `ruff`, and `mypy`.

### File List

- _bmad-output/implementation-artifacts/2-4-tentative-memory-recall-and-user-correction.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/conversation/clarification.py
- backend/app/conversation/first_response.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/conversation/test_first_response.py

## Change Log

- 2026-03-13: Created Story 2.4 implementation guide with acceptance criteria, task decomposition, architecture guardrails, trust/UX constraints, and test expectations aligned to the live Story 2.3 recall seam.
- 2026-03-13: Implemented tentative recall surfacing, low-confidence suppression, and correction-yield handling for Story 2.4, with regression coverage in conversation and webhook tests.
