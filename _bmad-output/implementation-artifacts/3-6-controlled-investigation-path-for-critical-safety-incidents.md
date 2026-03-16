# Story 3.6: Controlled investigation path для критических safety-инцидентов

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want чтобы продукт поддерживал контролируемый path для расследования критических safety-инцидентов,
so that exceptional review остается возможным без превращения transcript access в routine operator behavior.

## Acceptance Criteria

1. When a crisis-routed session requires deeper operational review, the system provides a controlled and policy-governed investigation path, and this path is not the default mode of routine operator work. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-36-controlled-investigation-path-для-критических-safety-инцидентов] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
2. When an operator uses the investigation path for a critical incident, any access to additional context remains auditable, purpose-bound, and limited, and the product does not turn exceptional access into routine transcript visibility. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-36-controlled-investigation-path-для-критических-safety-инцидентов] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
3. When the investigation path or incident reclassification workflow fails, the failure becomes observable as a safety/ops issue, and the product does not silently lose incident traceability. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-36-controlled-investigation-path-для-критических-safety-инцидентов] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
4. When borderline or false-positive events are reviewed later, the workflow supports reclassification and learning signals that can improve safety behavior over time without removing the privacy boundary by default. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-36-controlled-investigation-path-для-критических-safety-инцидентов] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md] [Source: /home/erda/Музыка/goals/backend/app/ops/alerts.py]

## Tasks / Subtasks

- [x] Add a dedicated exceptional-access investigation model and audit trail for critical safety incidents (AC: 1, 2, 3, 4)
  - [x] Add a durable investigation record in `backend/app/models.py` linked to `OperatorAlert` and `TelegramSession` instead of overloading `OperatorAlert.payload` or `SummaryGenerationSignal`.
  - [x] Model bounded investigation metadata such as `operator_alert_id`, `session_id`, `telegram_user_id`, `reason_code`, `status`, `requested_by`, `approved_by`, `opened_at`, `closed_at`, `reclassification`, and `audit_notes`.
  - [x] Keep exceptional-access state explicit: requested, approved, opened, closed, failed, and denied should be distinguishable for later review.
- [x] Implement a controlled investigation service under the ops/operator boundary (AC: 1, 2, 3)
  - [x] Add a dedicated service seam under `backend/app/ops/` or `backend/app/operator/` that opens an investigation only after an explicit, auditable operator action.
  - [x] Require the ops auth token already used by `/api/v1/ops/*` and an explicit investigation reason code rather than silent transcript access on alert read.
  - [x] Record investigation-open and investigation-close events even if transcript retrieval or reclassification fails partway through.
- [x] Expose a minimal internal API for investigation workflow without making transcript access the default ops path (AC: 1, 2, 4)
  - [x] Add a request/open endpoint for critical-incident investigation and a close/reclassify endpoint under `backend/app/ops/api.py`.
  - [x] Keep `/api/v1/ops/alerts` transcript-free and require the separate investigation flow for any deeper context.
  - [x] Return wrapped JSON responses consistent with the project’s internal HTTP envelope style.
- [x] Define a bounded context payload for exceptional review (AC: 2, 4)
  - [x] Reuse already persisted bounded artifacts first: `OperatorAlert`, `SafetySignal`, `TelegramSession` crisis fields, and transcript-minimized memory artifacts where available.
  - [x] If deeper context must be shown, expose only the minimum required review payload for the specific incident and mark access in the audit trail.
  - [x] Do not restore routine transcript retention or add general-purpose transcript browsing to support this story.
- [x] Add reclassification and learning-signal support without collapsing privacy boundaries (AC: 3, 4)
  - [x] Allow investigation closure to store a reviewed classification, outcome, and bounded notes that can later inform safety tuning.
  - [x] Preserve original alert classification and reviewed classification separately so later analysis can distinguish model output from operator judgment.
  - [x] Make investigation failures and incomplete reviews visible as ops/safety issues rather than silently dropping them.
- [x] Add focused tests for policy gating, auditability, failure handling, and reclassification behavior (AC: 1, 2, 3, 4)
  - [x] Add unit tests for investigation lifecycle transitions and for rejecting transcript access without explicit investigation creation.
  - [x] Add route tests for ops-auth protection, request/open/close flows, wrapped responses, and transcript-free default alerts behavior.
  - [x] Add failure-path tests proving investigation traceability survives transcript-fetch or persistence failures.
  - [x] Run `pytest`, `ruff`, and `mypy`.

### Review Follow-ups (AI)

- [ ] [AI-Review][HIGH] `_verify_ops_token` returns early when `OPS_AUTH_TOKEN` is not set, making all ops endpoints — including investigation context — publicly accessible in misconfigured deployments. Decide whether to fail-closed (raise 503 if token is unconfigured) or document this as an explicit dev-only escape hatch with an env-level guard. [backend/app/ops/api.py:34-42]
- [ ] [AI-Review][MEDIUM] `context_payload` permanently stores `last_user_message` and `last_bot_prompt` from `TelegramSession` as a JSON blob in `operator_investigation`. These values survive any future transcript purge of the session because the investigation record has no independent retention lifecycle. Define a retention policy or redaction hook for `context_payload` aligned with the product's transcript-minimization rules. [backend/app/ops/investigations.py:225-231]

## Dev Notes

- Story 3.5 intentionally stopped at bounded operator alerting and a transcript-free ops inbox. Story 3.6 is the first place where exceptional deeper review is allowed, so it must add a separate investigation workflow instead of smuggling transcript access into `/api/v1/ops/alerts`. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-5-operator-alerting-without-routine-exposure-to-content.md] [Source: /home/erda/Музыка/goals/backend/app/ops/api.py]
- The live backend already has the right precursors for investigation gating:
  - `OperatorAlert` as the durable incident pointer
  - `SafetySignal` as turn-level classification history
  - `TelegramSession` crisis fields for activation/routing timestamps
  - transcript purging after summary persistence
  Story 3.6 should build on those artifacts instead of reintroducing broad transcript storage. [Source: /home/erda/Музыка/goals/backend/app/models.py] [Source: /home/erda/Музыка/goals/backend/tests/memory/test_summary.py]
- `SummaryGenerationSignal` is currently a generic retryable-failure table reused by ops and memory failure signaling. It is useful for observability, but not sufficient as the primary investigation audit model because FR40 needs explicit purpose-bound access history, not just generic retry metadata. [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md]
- The architecture and PRD are explicit that routine operator access to session content is disallowed by default and exceptional access must be policy-governed and auditable. Treat that as a hard boundary, not a copywriting preference. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
- UX constraints matter here too: the product must not make users feel like they are under routine surveillance. This means the investigation path should remain operator-only, explicit, and rare, with no spillover into normal user-facing conversation flows. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Scope discipline for Epic 3:
  - `3.5` owns bounded alert creation and delivery
  - `3.6` owns exceptional investigation access and audit trail
  - `3.7` owns graceful step-down after false positives in the user-facing flow
- No `project-context.md` exists in this workspace, so implementation guidance is anchored to the live repo and planning artifacts only.

### Project Structure Notes

- Respect the live repo layout under `backend/app/`, not the aspirational `src/goals/...` tree from the architecture document.
- Keep boundaries explicit:
  - `safety/` owns assessment and crisis classification
  - `conversation/session_bootstrap.py` owns request-path orchestration only
  - `ops/api.py` owns the restricted internal HTTP surface
  - a new `ops/investigations.py` or similar seam should own investigation lifecycle rules
  - `ops/signals.py` can continue to record failure visibility, but should not become the primary audit store
- Default ops endpoints should stay transcript-free. Any deeper review payload must be reachable only through a distinct investigation action and its own audit record.
- The current repo already uses pluralized SQLModel tables, `snake_case`, typed Pydantic/SQLModel boundaries, and wrapped JSON responses for internal ops routes. Follow those conventions for any new models and endpoints. [Source: /home/erda/Музыка/goals/backend/app/models.py] [Source: /home/erda/Музыка/goals/backend/app/ops/api.py]

### Technical Requirements

- Add a durable investigation model rather than storing access history inside `OperatorAlert.payload`. Investigation lifecycle and exceptional-access audit are their own domain concern. [Source: /home/erda/Музыка/goals/backend/app/models.py] [Inference based on: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Gate any deeper context read behind an explicit investigation request/open step with ops authentication and a required reason code. Do not let `/api/v1/ops/alerts` or `/api/v1/ops/continuity/{telegram_user_id}` become implicit transcript backdoors. [Source: /home/erda/Музыка/goals/backend/app/ops/api.py]
- Preserve original safety classification and reviewed classification separately. The system needs to learn from false positives and borderline events without overwriting the original incident trail. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md] [Source: /home/erda/Музыка/goals/backend/app/ops/alerts.py]
- Investigation failures must be operator-visible/system-visible. If transcript retrieval, persistence, or closure fails, record a bounded ops/safety signal and keep the investigation record queryable. [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Reuse transcript-minimized artifacts first. Session summaries, profile facts, safety signals, and alert metadata should satisfy most review needs before any rawer context is exposed. This is an inference from the product’s transcript-minimization rules and the existing memory pipeline. [Inference based on: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md, /home/erda/Музыка/goals/backend/tests/memory/test_summary.py]
- Keep the investigation path policy-governed and bounded by purpose. It should support incident review, reclassification, and safety learning, not generic support browsing or ad hoc curiosity-driven transcript lookup. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md]

### Architecture Compliance

- Preserve the architecture’s privacy-first operator model: exceptional access is allowed, but routine transcript visibility remains prohibited. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Keep adapter/domain boundaries intact:
  - ops endpoints authenticate and translate HTTP
  - ops investigation service enforces policy and audit rules
  - safety stays the owner of risk classification semantics
  - memory remains responsible for transcript minimization and durable continuity artifacts
- Do not couple investigation workflow to user-facing crisis message composition. The operator path is a separate operational concern from `compose_crisis_routing_response()`. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Prefer additive implementation: introduce a dedicated investigation seam and model rather than mutating existing alert payloads into an implicit workflow engine.

### Library / Framework Requirements

- Maintain compatibility with the current backend stack pinned in `backend/pyproject.toml`: FastAPI `0.114.x`, SQLModel `0.0.21`, `python-telegram-bot 21.x`, and Pydantic `2.x`. Do not turn this story into a dependency-upgrade task. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- Use typed SQLModel/Pydantic models for new investigation records and ops DTOs. The repo runs strict `mypy`, so raw untyped dict plumbing should be avoided except at narrow serialization edges. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- If you need ordered queries for new ops endpoints, prefer typed column expressions over raw SQL text where practical. That follows the code-review correction already applied in Story 3.5. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-5-operator-alerting-without-routine-exposure-to-content.md]

### File Structure Requirements

- Primary implementation files:
  - `backend/app/models.py`
  - `backend/app/ops/api.py`
- Likely new files:
  - `backend/app/ops/investigations.py`
  - optionally `backend/app/ops/schemas.py` if investigation DTOs need a separate home
  - a new Alembic migration under `backend/app/alembic/versions/`
- Likely reuse points:
  - `backend/app/ops/alerts.py`
  - `backend/app/ops/signals.py`
  - `backend/app/conversation/session_bootstrap.py` only if an investigation link or follow-up signal must be wired after alert creation
- Primary tests:
  - `backend/tests/api/routes/test_ops_routes.py`
  - `backend/tests/operator/test_alerts.py`
  - add a dedicated `backend/tests/operator/test_investigations.py`
- Avoid implementing Story 3.6 inside:
  - `backend/app/conversation/first_response.py`
  - `backend/app/conversation/clarification.py`
  - `backend/app/conversation/closure.py`
  - `backend/app/memory/` as the main owner of ops policy

### Testing Requirements

- Add unit tests for investigation lifecycle transitions: request, open, close, deny, fail.
- Add tests that default ops inbox and continuity views remain transcript-free even after investigation support is added.
- Add route tests proving deeper context cannot be accessed without a valid ops token and explicit investigation creation.
- Add tests that reviewed classification can differ from original alert classification without mutating historical source data.
- Add failure-path tests showing investigation errors remain traceable via durable records plus ops/safety signals.
- Preserve the standard backend quality bar: `pytest`, `ruff`, and `mypy`.

### Previous Story Intelligence

- Story 3.5 established a durable `OperatorAlert` row keyed by session and exposed `/api/v1/ops/alerts` as a metadata-first ops inbox. Build on that instead of creating a second parallel incident entry point. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-5-operator-alerting-without-routine-exposure-to-content.md]
- The dedupe rule in 3.5 is session-based (`uq_operator_alert_session`). That means Story 3.6 should treat one alert/session as one incident anchor and layer investigation state on top, not assume multiple alert rows per session already exist. [Source: /home/erda/Музыка/goals/backend/app/models.py]
- 3.5 also proved the repo preference for bounded metadata payloads and explicit failure signaling. Investigation work should extend that discipline rather than bypass it with open-ended transcript blobs. [Source: /home/erda/Музыка/goals/backend/tests/operator/test_alerts.py]

### Git Intelligence Summary

- Git history was unavailable because `/home/erda/Музыка/goals` is not a Git repository in this workspace, so no commit-pattern analysis could be performed.

### Latest Tech Information

- Official FastAPI release notes show the broader 0.115 series has continued beyond the repo pin, but this story should stay within the project’s pinned `0.114.x` range and avoid assuming newer helper behavior. [Source: https://fastapi.tiangolo.com/release-notes/]
- Official SQLModel release notes for `0.0.21` confirm support for UUID and cascade-delete-related features; that aligns with the existing model style in the repo and is sufficient for adding an investigation table without changing ORM strategy. [Source: https://sqlmodel.tiangolo.com/release-notes/]
- Official Pydantic changelog shows active 2.x evolution, but the repo already targets Pydantic v2 semantics. Use current `model_dump()`/typed-model patterns already present in the codebase rather than introducing compatibility shims. [Source: https://docs.pydantic.dev/changelog/]
- The `python-telegram-bot` docs confirm the library remains async-first in v21.x, but this story is primarily an internal ops workflow and should not expand Telegram delivery concerns unless the investigation path later needs a bounded operator notification follow-up. [Source: https://docs.python-telegram-bot.org/en/v21.0/]

### References

- Story source and acceptance criteria: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md]
- Product privacy and controlled-access requirements: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
- Architecture boundaries and operator visibility model: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- UX requirement that continuity and safety handling should not feel like surveillance: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Previous story context for bounded operator alerting: [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-5-operator-alerting-without-routine-exposure-to-content.md]
- Live request-path orchestrator: [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Live safety assessment seam: [Source: /home/erda/Музыка/goals/backend/app/safety/service.py]
- Live ops inbox endpoints: [Source: /home/erda/Музыка/goals/backend/app/ops/api.py]
- Live operator alert seam: [Source: /home/erda/Музыка/goals/backend/app/ops/alerts.py]
- Existing failure-signal helper: [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py]
- Existing session, safety, and alert models: [Source: /home/erda/Музыка/goals/backend/app/models.py]
- Existing ops route coverage: [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_ops_routes.py]
- Existing operator alert coverage: [Source: /home/erda/Музыка/goals/backend/tests/operator/test_alerts.py]
- Backend dependency and tooling baseline: [Source: /home/erda/Музыка/goals/backend/pyproject.toml]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-selected from `/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog story in order: `3-6-controlled-investigation-path-for-critical-safety-incidents`.
- Loaded and followed `_bmad/core/tasks/workflow.xml` with workflow config `_bmad/bmm/workflows/4-implementation/create-story/workflow.yaml`.
- Analyzed planning artifacts: `epics.md`, `architecture.md`, `prd.md`, and `ux-design-specification.md`.
- Loaded prior Epic 3 implementation context from `3-5-operator-alerting-without-routine-exposure-to-content.md`.
- Inspected live backend seams in `backend/app/conversation/session_bootstrap.py`, `backend/app/safety/service.py`, `backend/app/ops/api.py`, `backend/app/ops/alerts.py`, `backend/app/ops/signals.py`, `backend/app/models.py`, and existing ops/operator tests.
- Confirmed no `project-context.md` exists in this workspace.
- Confirmed the current workspace root is not a Git repository, so git-history intelligence from the workflow was unavailable.
- Checked official project docs for FastAPI, SQLModel, Pydantic, and python-telegram-bot to avoid embedding stale framework guidance; implementation advice remains pinned to the repo’s current dependency versions.
- Implemented `OperatorInvestigation` persistence plus Alembic migration `b8c9d0e1f2a3_add_operator_investigation_table.py`.
- Added `backend/app/ops/investigations.py` with explicit request/open, deny, close, fetch, and bounded context assembly flows.
- Extended `backend/app/ops/api.py` with transcript-gated investigation endpoints:
  - `POST /api/v1/ops/alerts/{operator_alert_id}/investigations`
  - `GET /api/v1/ops/investigations/{investigation_id}`
  - `POST /api/v1/ops/investigations/{investigation_id}/close`
- Kept `/api/v1/ops/alerts` transcript-free while moving exceptional access into the explicit investigation workflow.
- Added cleanup support for `OperatorInvestigation` in shared and telegram-route test fixtures to preserve full-suite isolation.
- Validation commands executed with explicit DB env:
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run alembic upgrade heads`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests/operator/test_investigations.py tests/api/routes/test_ops_routes.py -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests -q`
  - `uv run ruff check app tests`
  - `uv run mypy app tests`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story `3.6` is intentionally limited to exceptional investigation workflow, auditable access, bounded review context, and reclassification traceability.
- Default ops paths must remain transcript-free after this story.
- Investigation access should be explicit, token-protected, reason-coded, and durably auditable.
- Original alert classification and reviewed classification should both be preserved.
- Generic failure signaling can support observability, but a dedicated investigation record should remain the source of truth for controlled access history.
- User-facing false-positive recovery remains out of scope here and belongs in Story `3.7`.
- Implemented a dedicated `operator_investigation` table with explicit requested/opened/closed/denied/failed lifecycle states.
- Added bounded investigation context assembly that reuses alert metadata, session crisis state, safety signals, and transcript-minimized continuity artifacts before exposing any current-turn content.
- Added transcript-gated ops endpoints for opening, reading, and closing investigations without weakening the default metadata-only ops inbox.
- Added failure signaling for investigation context build failures via `operator_investigation_context_failed`.
- Preserved original alert classification separately from reviewed investigation classification and closure outcome.
- Full backend regression suite, Ruff, and mypy passed against local Postgres using `postgres/example` on `localhost:5432`.

### File List

- _bmad-output/implementation-artifacts/3-6-controlled-investigation-path-for-critical-safety-incidents.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/alembic/versions/b8c9d0e1f2a3_add_operator_investigation_table.py
- backend/app/models.py
- backend/app/ops/alerts.py
- backend/app/ops/api.py
- backend/app/ops/investigations.py
- backend/tests/api/routes/test_ops_routes.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/conftest.py
- backend/tests/operator/test_alerts.py
- backend/tests/operator/test_investigations.py

## Change Log

- 2026-03-14: Implemented auditable exceptional-access investigation workflow for critical safety incidents, including new ops endpoints, bounded context assembly, investigation persistence, migration, and full regression coverage.
- 2026-03-14: Code review fixes — fixed deny audit trail corruption (H1), added status guard in close (H2), added uniqueness check for open investigations per alert (H3), wrapped SafetySignal query in InvestigationContextError handler (M1), added Pydantic max_length validation on reviewed_classification (M2), added auth-failure and conflict-state route tests (M3/M4). Action items created for unauthenticated-token policy (H4) and context_payload retention (M5).
