# Story 2.5: Conservative memory promotion и safe handling sensitive context

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь, который делится личным и чувствительным контекстом,
I want чтобы продукт сохранял в durable memory только действительно полезные и безопасные элементы,
so that continuity remains trustworthy and does not overstore risky or intimate details.

## Acceptance Criteria

1. When a session summary draft and candidate profile facts are produced after session closure, only the parts that are useful for future relevance and safe for durable continuity are promoted into persistent memory, and not every session detail is stored long-term. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-25-Conservative-memory-promotion-и-safe-handling-sensitive-context] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
2. When session content contains highly sensitive, crisis-related, or otherwise high-risk material, the promotion flow either keeps that material out of standard durable memory or routes it through a more limited handling path, and the product must not later reuse that material as normal continuity context by default. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-25-Conservative-memory-promotion-и-safe-handling-sensitive-context] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
3. When a candidate memory artifact is based on weak evidence, uncertainty, or interpretation that is not strong enough to trust durably, that candidate is not persisted as a durable fact without stronger confidence and ambiguous inferences stay outside trusted profile memory. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-25-Conservative-memory-promotion-и-safe-handling-sensitive-context] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
4. When a new profile fact is promoted, it is stored in a typed and reviewable structure whose origin remains compatible with later correction, deletion, downgrade, or replacement. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-25-Conservative-memory-promotion-и-safe-handling-sensitive-context] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
5. When previously promoted memory later becomes wrong, stale, or no longer appropriate, the memory model supports update, downgrade, or removal from recall use rather than treating durable memory as irreversible. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-25-Conservative-memory-promotion-и-safe-handling-sensitive-context] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
6. When promotion-rule evaluation or persistence cannot complete reliably, the default behavior stays conservative: the system stores less memory rather than over-storing sensitive or low-confidence content. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-25-Conservative-memory-promotion-и-safe-handling-sensitive-context] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

## Tasks / Subtasks

- [x] Add an explicit memory-promotion decision layer ahead of durable persistence (AC: 1, 2, 3, 6)
  - [x] Split raw summary/profile candidates from promoted durable artifacts instead of treating `allowed_profile_facts` as automatically eligible for storage.
  - [x] Introduce deterministic promotion rules that can reject, downgrade, or suppress candidates based on sensitivity, uncertainty, and usefulness-for-continuity.
  - [x] Keep failure behavior conservative so promotion-rule errors do not result in best-effort over-storage.
- [x] Refine durable summary shaping so standard memory stays useful without carrying unsafe detail (AC: 1, 2, 3, 6)
  - [x] Review `build_session_summary()` so high-risk or overly intimate content is excluded or generalized before durable persistence.
  - [x] Preserve summary usefulness for future relevance while avoiding transcript-like or crisis-detail retention.
  - [x] Ensure uncertainty markers continue to block durable overclaiming rather than merely annotating unsafe content.
- [x] Make promoted profile facts typed, reviewable, and lifecycle-safe (AC: 2, 4, 5)
  - [x] Reuse or extend the existing `ProfileFact` lifecycle fields (`confidence`, `deleted_at`, `superseded_at`, `source_session_id`) so promoted facts remain correctable and removable.
  - [x] Add only the minimum additional schema/model metadata needed to distinguish normal durable facts from downgraded or restricted candidates.
  - [x] Keep profile facts bounded to the current typed fact taxonomy unless there is a strong need to expand it with architecture-consistent names.
- [x] Keep continuity recall aligned with conservative promotion rules (AC: 2, 4, 5)
  - [x] Ensure `get_session_recall_context()` and continuity overview paths surface only active, promotion-approved artifacts.
  - [x] Prevent sensitive or downgraded memory from re-entering normal recall just because it was seen in an earlier session.
  - [x] Preserve support for later correction, downgrade, or removal without breaking existing recall behavior for safe facts.
- [x] Add regression coverage for safe promotion, downgrade, and conservative failure paths (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add unit tests around summary/profile promotion decisions, especially high-risk, ambiguous, and low-confidence inputs.
  - [x] Add tests proving rejected or downgraded candidates do not appear in continuity overview or recall context.
  - [x] Add tests proving superseded or removed facts drop out of future recall use.
  - [x] Add tests proving rule-evaluation or persistence failures default to “store less” behavior.
  - [x] Run the normal backend quality bar: `pytest`, `ruff`, and `mypy`.

## Dev Notes

- The current memory seam already separates transient session state from durable artifacts: `SessionSummaryPayload` is created at closure in `backend/app/conversation/session_bootstrap.py`, then `build_session_summary()` and `persist_session_summary()` in `backend/app/memory/service.py` turn it into `SessionSummary` and `ProfileFact` records. Story 2.5 should harden that seam, not move memory policy into `conversation/` or transport code. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py] [Source: /home/erda/Музыка/goals/backend/app/memory/service.py]
- Right now `derive_allowed_profile_facts()` and `_sanitize_profile_facts()` are conservative but still heuristic and mostly key-based. Story 2.5 should add an explicit promotion decision stage so sensitive or weakly supported candidates are rejected or downgraded before `_upsert_profile_facts()` runs. [Source: /home/erda/Музыка/goals/backend/app/memory/service.py]
- The existing model already has partial lifecycle hooks for reversibility: `ProfileFact.deleted_at`, `ProfileFact.superseded_at`, `ProfileFact.confidence`, and `source_session_id`. Prefer building on those fields before adding new tables or a broad review system. [Source: /home/erda/Музыка/goals/backend/app/models.py]
- `get_session_recall_context()` and `get_continuity_overview()` already filter deleted or superseded facts. Story 2.5 should keep recall strictly aligned with promotion-safe artifacts so restricted or downgraded memory cannot leak back into later sessions. [Source: /home/erda/Музыка/goals/backend/app/memory/service.py] [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_ops_routes.py]
- Product and architecture docs are explicit that raw transcripts are transient, summary/profile artifacts are the durable memory layer, and high-risk content requires limited promotion or separate handling. This story is the enforcement point for that promise. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- UX rules also matter here: continuity must feel helpful, tentative, and non-invasive. Over-promoting intimate or crisis-heavy details would create exactly the “creepy memory” failure mode the product is trying to avoid. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]

## Developer Context

### Technical Requirements

- Add a promotion-policy layer between candidate generation and persistence so “candidate fact” and “durable fact” are no longer the same thing. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-25-Conservative-memory-promotion-и-safe-handling-sensitive-context]
- Keep durable memory biased toward low-risk continuity cues such as recurring context, communication preferences, or work/relationship patterns, and biased away from intimate specifics, crisis detail, or weak inference. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Treat uncertainty as a persistence guardrail, not as a note that magically makes unsafe storage acceptable. If evidence is weak, do not promote it durably. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-25-Conservative-memory-promotion-и-safe-handling-sensitive-context]
- Keep the failure mode conservative. If rule evaluation or persistence-path safety cannot be determined, prefer saving less profile memory and keeping summaries generalized rather than risking over-storage. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Preserve later correction paths. Promotion decisions cannot make facts effectively immutable; later stories and operator/privacy flows rely on downgrade, replacement, and deletion remaining possible. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-25-Conservative-memory-promotion-и-safe-handling-sensitive-context]

### Architecture Compliance

- `conversation/` should continue to assemble the bounded `SessionSummaryPayload`, but durable-memory promotion policy belongs in `memory/`. Do not move persistence rules into route handlers, Telegram adapters, or first-response logic. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md] [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Keep the system as a modular monolith with repositories/services inside the memory domain. If a helper is added, keep it adjacent to `backend/app/memory/service.py` rather than creating a cross-cutting “policy” module outside domain ownership. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Do not introduce transcript retention, vector retrieval, or a new surveillance-style memory archive. MVP memory remains summary-plus-typed-facts only. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Internal ops surfaces should continue to expose transcript-free continuity views only. Any new metadata added for promotion safety must remain compatible with the existing wrapped internal API style and privacy posture. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md] [Source: /home/erda/Музыка/goals/backend/app/ops/api.py]

### Library / Framework Requirements

- Stay on the current backend stack declared in `backend/pyproject.toml`: FastAPI, SQLModel, Alembic, `pydantic-settings`, PostgreSQL via `psycopg`, and `python-telegram-bot` `<22`. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- FastAPI’s official Background Tasks guidance still supports keeping summary generation post-response, which means Story 2.5 should harden the memory work inside that background seam rather than moving it back onto the main trust-critical response path. Source: https://fastapi.tiangolo.com/tutorial/background-tasks/
- SQLModel’s official FastAPI session-dependency pattern still fits the current request-scoped DB access model; keep promotion/persistence work inside the existing session flow and transactional boundaries. Inference from official docs plus current repo usage. Source: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- If new promotion thresholds or toggles are introduced, place them in the existing Pydantic Settings seam instead of scattering constants across the memory module. Source: https://docs.pydantic.dev/latest/api/pydantic_settings/
- Avoid adopting assumptions from newer major Telegram bot versions while touching session-entry handoff; the repo remains pinned to `python-telegram-bot` `>=21.6,<22.0`. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]

### File Structure Requirements

- Primary implementation files are likely:
  - `backend/app/memory/service.py`
  - `backend/app/memory/schemas.py`
  - `backend/app/models.py` if promotion metadata or lifecycle state needs to be extended
  - `backend/app/conversation/session_bootstrap.py` only if the summary payload shape must carry explicit promotion candidates or bounded safety hints
- Primary test files are likely:
  - `backend/tests/memory/test_summary.py`
  - `backend/tests/api/routes/test_ops_routes.py`
  - `backend/tests/api/routes/test_telegram_session_entry.py` if closure-to-summary handoff behavior changes
- Avoid solving this story in:
  - `backend/app/bot/` transport code
  - new raw transcript storage paths
  - any generic global helper layer outside the memory domain

### Testing Requirements

- Add tests for high-risk or crisis-adjacent session content proving that standard durable profile memory stays empty or downgraded.
- Add tests for uncertain or weakly supported facts proving they are not promoted durably.
- Add tests for reviewable lifecycle behavior, including superseding or removing previously promoted facts and verifying they disappear from recall.
- Add tests for continuity overview and recall context so only promotion-approved artifacts surface.
- Add tests for conservative fallback when promotion rule evaluation or persistence safety fails.
- Run the normal backend quality bar: `pytest`, `ruff`, and `mypy`.

### Previous Story Intelligence

- Story 2.1 established post-session summary generation as a separate continuity artifact rather than part of the live reply path. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-1-session-summary-generation-after-session-completion.md]
- Story 2.2 expanded the durable memory boundary with `SessionSummary`, `ProfileFact`, and summary-failure signaling, plus transcript purging. Story 2.5 should refine what gets promoted into that boundary rather than redesigning the storage model from scratch. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-2-durable-memory-without-long-term-raw-transcript-storage.md] [Source: /home/erda/Музыка/goals/backend/app/models.py]
- Story 2.3 and Story 2.4 made recall useful and trust-safe on the read side. Story 2.5 is the write-side complement: if promotion is too permissive, those recall improvements become unsafe later. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-3-using-prior-memory-at-the-start-of-a-new-session.md] [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-4-tentative-memory-recall-and-user-correction.md]
- Existing tests already validate transcript purging, durable summary creation, recall filtering, and deleted fact exclusion. Extend those patterns instead of introducing a parallel test stack. [Source: /home/erda/Музыка/goals/backend/tests/memory/test_summary.py] [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_ops_routes.py]

### Git Intelligence Summary

- No git history was available from `/home/erda/Музыка/goals`, so there was no commit-level pattern analysis for this story.

### Library / Framework Latest Information

- FastAPI’s current official docs still treat `BackgroundTasks` as the standard post-response mechanism, which supports keeping summary generation and promotion evaluation out of the first response latency path. Source: https://fastapi.tiangolo.com/tutorial/background-tasks/
- SQLModel’s current FastAPI tutorial still centers on dependency-injected request sessions, which matches the existing session-scoped persistence and recall access patterns used by the repo. Source: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Pydantic Settings continues to document a central env-backed settings seam, so any promotion-policy thresholds or flags should stay there rather than becoming hard-coded policy constants scattered through the service layer. Source: https://docs.pydantic.dev/latest/api/pydantic_settings/

### Project Structure Notes

- The current repo already has the right structural seams for this story:
  - `conversation/` for bounded payload handoff
  - `memory/` for promotion decisions, durable persistence, and recall shaping
  - `ops/` for transcript-free continuity inspection
- There is no need for a new subsystem. The likely implementation is a policy refinement inside `memory/service.py`, with small schema/model support if the current fact lifecycle metadata is not quite enough.
- The main structural risk is letting “candidate” memory leak directly into “durable” memory again. Keep that boundary explicit in code and tests.

### References

- Story source and acceptance criteria: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Product requirements and privacy constraints: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Architecture boundaries and memory ownership: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- UX continuity, memory humility, and trust rules: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)
- Current memory service seam: [service.py](/home/erda/Музыка/goals/backend/app/memory/service.py)
- Current memory schemas: [schemas.py](/home/erda/Музыка/goals/backend/app/memory/schemas.py)
- Current conversation-to-memory handoff: [session_bootstrap.py](/home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py)
- Current durable models: [models.py](/home/erda/Музыка/goals/backend/app/models.py)
- Current memory regression tests: [test_summary.py](/home/erda/Музыка/goals/backend/tests/memory/test_summary.py)
- Current ops continuity tests: [test_ops_routes.py](/home/erda/Музыка/goals/backend/tests/api/routes/test_ops_routes.py)
- Previous story context: [2-4-tentative-memory-recall-and-user-correction.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/2-4-tentative-memory-recall-and-user-correction.md)
- Official FastAPI Background Tasks docs: https://fastapi.tiangolo.com/tutorial/background-tasks/
- Official SQLModel FastAPI session dependency docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Official Pydantic Settings docs: https://docs.pydantic.dev/latest/api/pydantic_settings/

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-discovered from `/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog story in order: `2-5-conservative-memory-promotion-and-safe-handling-of-sensitive-context`.
- Core context loaded from `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, previous story `2-4`, and the live memory/conversation seams in the backend repo.
- No `project-context.md` was found in the workspace.
- No git history was available because `/home/erda/Музыка/goals` is not a git repository root.
- The workflow step that references `_bmad/core/tasks/validate-workflow.xml` could not be executed literally because that file does not exist in the workspace.
- Web verification was used only for current official framework guidance around FastAPI background tasks, SQLModel request-session usage, and Pydantic Settings. The implementation direction remains anchored in the local repo.
- Added red-phase coverage in `backend/tests/memory/test_summary.py`, `backend/tests/api/routes/test_ops_routes.py`, and `backend/tests/api/routes/test_telegram_session_entry.py` for sensitive summary shaping, restricted profile facts, recall/ops filtering, and conservative promotion-failure behavior.
- Implemented a promotion-policy layer in `backend/app/memory/service.py` that separates candidate facts from persisted durable artifacts and fails closed on promotion-rule exceptions.
- Extended `ProfileFactInput` in `backend/app/memory/schemas.py` with `retention_scope` so the service can persist `durable_profile` vs `restricted_profile` facts without introducing a new table or migration.
- Validation used an isolated Postgres container on port `5433` (`goals-test-db`) because the local service on `5432` belongs to another project and rejects the repo’s default credentials.
- Validation commands executed:
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run alembic upgrade head`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest tests/memory/test_summary.py tests/api/routes/test_ops_routes.py tests/api/routes/test_telegram_session_entry.py -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest tests -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 ENABLE_LEGACY_WEB_ROUTES=true uv run pytest tests -q`
  - `uv run ruff check app tests`
  - `uv run mypy app tests`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story 2.5 is the write-side guardrail for the continuity system: it narrows what is allowed into durable memory so later recall remains useful and safe.
- The implementation focus is an explicit promotion-policy layer, durable-summary shaping for privacy safety, reviewable fact lifecycle handling, and conservative failure behavior.
- Guardrails explicitly prohibit transcript retention, vector-first retrieval, transport-layer memory policy, and broad new operator-review infrastructure for MVP.
- Existing models and tests already contain lifecycle seams (`confidence`, `deleted_at`, `superseded_at`, transcript purging, recall filtering); the dev agent should extend them instead of inventing parallel storage paths.
- Added deterministic promotion logic that downgrades high-risk and low-confidence profile facts to `restricted_profile` so they remain reviewable and deletable but stay out of standard recall and ops continuity views.
- Added high-risk summary shaping plus recall-safe summary reuse so sensitive or ambiguous content does not leak into later continuity while keeping the closure contract intact.
- Added regression coverage for restricted memory behavior, uncertain recurring-pattern suppression, ops filtering, integration-level sensitive-session closure behavior, and conservative fallback when promotion evaluation fails.
- Full backend validation passed with isolated Postgres on port `5433`, including standard and legacy-route pytest runs, `ruff`, and `mypy`.

### File List

- _bmad-output/implementation-artifacts/2-5-conservative-memory-promotion-and-safe-handling-of-sensitive-context.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/memory/schemas.py
- backend/app/memory/service.py
- backend/tests/memory/test_summary.py
- backend/tests/api/routes/test_ops_routes.py
- backend/tests/api/routes/test_telegram_session_entry.py

## Change Log

- 2026-03-13: Created Story 2.5 implementation guide with acceptance criteria, task decomposition, architecture guardrails, continuity-safety constraints, and test expectations aligned to the live memory persistence seam.
- 2026-03-13: Implemented conservative memory promotion, restricted-profile handling, recall/ops filtering, and regression coverage for sensitive and low-confidence continuity paths.
