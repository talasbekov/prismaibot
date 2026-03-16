# Story 3.5: Operator alerting без routine exposure к содержимому

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want получать alerts по crisis-routed sessions без постоянного доступа к полному содержимому переписки,
so that я могу реагировать на safety-relevant events without turning the product into a surveillance system.

## Acceptance Criteria

1. When the system routes a user session into the crisis-aware escalation flow, an operator alert is created and sent to a defined operational channel, and the alert includes enough signal-level information for response without requiring transcript access by default. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-35-operator-alerting-без-routine-exposure-к-содержимому] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
2. When the founder/operator receives a crisis alert, the default alert payload does not include the full raw transcript and routine visibility remains limited to metadata, risk classification, timestamps, and minimally necessary operational context. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-35-operator-alerting-без-routine-exposure-к-содержимому] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
3. When multiple crisis-routed sessions occur or an existing crisis session is routed again, alerts remain individually traceable and the operator can distinguish a new alert event from a retry or repeated delivery attempt instead of receiving an undifferentiated duplicate stream. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-35-operator-alerting-без-routine-exposure-к-содержимому] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
4. When alert delivery to the operational channel fails, the failure becomes system-visible as a separate delivery incident and the underlying crisis event is not silently lost. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-35-operator-alerting-без-routine-exposure-к-содержимому] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
5. When the product builds routine monitoring around crisis events, the design preserves the privacy boundary by supporting reaction through signal-level alerting rather than making sensitive content reading the default operational behavior. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-35-operator-alerting-без-routine-exposure-к-содержимому] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
6. When alerting is triggered for a false positive or borderline case, the alert framing preserves the current risk classification so later review or reclassification is possible without overstating every event as equally severe. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-35-operator-alerting-без-routine-exposure-к-содержимому] [Source: /home/erda/Музыка/goals/backend/app/safety/service.py]

## Tasks / Subtasks

- [x] Add a durable operator-alert model and privacy-safe payload contract for crisis-routed sessions (AC: 1, 2, 3, 5, 6)
  - [x] Add a dedicated persisted alert record in `backend/app/models.py` for crisis/operator notifications instead of overloading `SummaryGenerationSignal`.
  - [x] Model bounded alert fields such as `session_id`, `telegram_user_id`, `classification`, `trigger_category`, `confidence`, delivery status, dedupe/retry identifiers, and timestamps.
  - [x] Exclude full raw transcript, `last_user_message`, and other routine sensitive content from the default alert schema.
- [x] Implement alert creation and delivery flow on top of the existing crisis-routing path (AC: 1, 3, 4, 6)
  - [x] Add an alerting seam under `backend/app/operator/` or `backend/app/safety/` that creates the durable alert record after confirmed crisis routing.
  - [x] Attempt delivery to a defined MVP operational channel using bounded metadata only, while keeping the persisted alert as the source of truth.
  - [x] Track `created`, `delivery_attempted`, `delivered`, and `delivery_failed` style states so new alerts and retries remain distinguishable.
- [x] Prevent alert storms for repeated crisis turns while preserving traceability (AC: 3, 6)
  - [x] Reuse `TelegramSession.crisis_state`, `crisis_activated_at`, `crisis_last_routed_at`, and current safety assessment fields to decide whether to create a new alert event or a retry/update for an existing one.
  - [x] Ensure repeated crisis messages in an already active crisis session do not create an unbounded duplicate stream in the operator channel.
  - [x] Preserve classification and confidence in the alert record so borderline or false-positive events can be reviewed later without rewriting history.
- [x] Make alert-delivery failures operator-visible/system-visible without dropping the underlying event (AC: 4)
  - [x] Persist the alert record before attempting external delivery.
  - [x] Record delivery failure state and reuse the existing retryable signal pattern only for delivery failure observability, not as the primary crisis-alert data model.
  - [x] Keep failure handling bounded and deterministic; if the channel delivery fails, the durable alert record must still remain queryable.
- [x] Add focused tests for privacy boundary, dedupe behavior, and delivery failure handling (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add unit tests for alert payload construction and dedupe/state-transition logic under `backend/tests/operator/` or `backend/tests/safety/`.
  - [x] Extend route-level crisis tests in `backend/tests/api/routes/test_telegram_session_entry.py` to assert alert creation happens on crisis routing without leaking transcript content.
  - [x] Add failure-path tests proving delivery failure is visible while the crisis event remains durably recorded.
  - [x] Run `pytest`, `ruff`, and `mypy`.

## Dev Notes

- Story 3.4 already established the crisis-resource delivery seam and kept crisis-policy ownership in `app.safety`. Story 3.5 should build on the same crisis-routing path and add operator alerting after a confirmed crisis route, without re-owning the crisis decision in `conversation/`. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-4-presenting-crisis-help-resources-and-a-safer-next-action.md] [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- The live repo already persists bounded safety facts in `SafetySignal` and crisis-state fields on `TelegramSession`. Those are the natural source inputs for an operator alert payload; do not introduce transcript-heavy alert construction. [Source: /home/erda/Музыка/goals/backend/app/models.py] [Source: /home/erda/Музыка/goals/backend/app/safety/service.py]
- `record_retryable_signal()` in `backend/app/ops/signals.py` is suitable for delivery-failure observability, but it is not a good primary storage model for crisis alerts because it writes into `SummaryGenerationSignal`. Story 3.5 should introduce a dedicated alert record instead of overloading summary-failure semantics. [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py] [Source: /home/erda/Музыка/goals/backend/app/models.py]
- The crisis path in `session_bootstrap.py` already distinguishes `newly_activated` from continued `crisis_active` routing. Reuse that distinction to prevent alert storms on repeated crisis turns and to make retries or follow-up notifications traceable. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Product and architecture artifacts are explicit that operator visibility should remain signal-level by default and avoid routine access to sensitive session content. This story should reinforce that privacy boundary rather than creating a backdoor ops transcript surface. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Scope discipline matters:
  - alert creation and delivery belong here in `3.5`
  - controlled deeper investigation belongs in `3.6`
  - graceful step-down after false positive belongs in `3.7`
- No `project-context.md` was found in the workspace, so implementation guidance is anchored to the live repo and planning artifacts only.

### Technical Requirements

- Keep alert-trigger ownership downstream of confirmed crisis routing. `conversation/session_bootstrap.py` may call the alerting seam after `crisis_routed`, but the operator-alert policy and payload construction should live in `operator/` or a dedicated `safety` alerting module. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Use only bounded metadata for the default alert payload: `session_id`, `telegram_user_id`, `classification`, `trigger_category`, `confidence`, timestamps, alert status, and delivery-attempt metadata. Do not include `TelegramSession.last_user_message`, full transcript fragments, or rendered crisis-copy content by default. [Source: /home/erda/Музыка/goals/backend/app/models.py] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
- Persist the crisis alert record before attempting channel delivery so failed notifications do not erase the underlying safety event. This is an inference from the story AC plus the architecture requirement that critical failures remain observable. [Inference based on: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md, /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Reuse `SafetySignal`, `TelegramSession.crisis_state`, `crisis_activated_at`, `crisis_last_routed_at`, `safety_classification`, `safety_trigger_category`, and `safety_confidence` to drive dedupe and severity framing. Do not add a second crisis-classification pipeline for alerting. [Source: /home/erda/Музыка/goals/backend/app/models.py] [Source: /home/erda/Музыка/goals/backend/app/safety/service.py]
- Treat alert delivery failures as a distinct delivery incident. If `record_retryable_signal()` is reused, it should capture delivery failure observability only, while the durable crisis alert remains the source of truth. [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py]
- Preserve risk nuance in alerts. Borderline or medium-confidence safety events should remain labeled as such in the alert record so later review and reclassification are possible without overstating severity. [Source: /home/erda/Музыка/goals/backend/app/safety/service.py] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md]

### Architecture Compliance

- Respect the live repo layout under `backend/app/`, not the aspirational `src/goals/...` tree from the architecture document.
- Keep boundaries explicit:
  - `safety/` owns safety assessment and crisis-routing policy
  - `conversation/session_bootstrap.py` owns request-path orchestration
  - `operator/` or a dedicated alerting seam owns operator-alert persistence and delivery
  - `ops/signals.py` owns bounded failure visibility
- Do not leak routine transcript access into the alerting model. Story `3.5` should strengthen the privacy boundary, not soften it.
- Avoid coupling operator alert creation to Telegram user-facing response composition. The user reply and operator alert may be triggered by the same crisis route, but they should remain separate concerns.
- Failures in alert delivery must produce operator-meaningful/system-meaningful signals rather than only logs. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

### Library / Framework Requirements

- Maintain compatibility with the current backend stack in `backend/pyproject.toml`: FastAPI `0.114.x`, Pydantic `2.x`, SQLModel `0.0.21`, and `python-telegram-bot 21.x`. Do not turn this story into framework-upgrade work. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- Keep alert payload schemas and delivery DTOs as typed Pydantic or SQLModel models rather than raw dicts. This matches the repo’s current typed-boundary style and strict mypy configuration. [Source: /home/erda/Музыка/goals/backend/pyproject.toml] [Source: /home/erda/Музыка/goals/backend/app/models.py]
- If Telegram is chosen as the MVP operator notification channel, keep any button/payload shape compatible with the existing `python-telegram-bot` 21.x conventions already used in user-facing crisis resources. This is an inference from the current dependency set and live crisis response structure. [Inference based on: /home/erda/Музыка/goals/backend/pyproject.toml, /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Keep SQLModel persistence simple and explicit. A dedicated alert table is preferable to overloading existing summary-failure tables with unrelated meaning. [Source: /home/erda/Музыка/goals/backend/app/models.py]

### File Structure Requirements

- Primary implementation files:
  - `backend/app/models.py`
  - `backend/app/conversation/session_bootstrap.py`
- Likely new files:
  - `backend/app/operator/alerts.py`
  - optionally `backend/app/operator/__init__.py` updates if the module is new or incomplete
- Likely adjacent reuse point:
  - `backend/app/ops/signals.py`
- Primary tests:
  - `backend/tests/api/routes/test_telegram_session_entry.py`
  - `backend/tests/operator/test_alerts.py`
  - or a focused safety/operator test module if the team keeps alerting near `safety/`
- Avoid implementing Story 3.5 in:
  - `backend/app/conversation/first_response.py`
  - `backend/app/conversation/clarification.py`
  - `backend/app/conversation/closure.py`
  - `backend/app/memory/`
  - any transcript-inspection workflow intended for Story `3.6`

### Testing Requirements

- Unit tests should verify the default operator alert payload contains bounded metadata only and excludes routine transcript content.
- Unit tests should verify dedupe/state-transition behavior for:
  - first crisis activation
  - repeated crisis routing in the same active session
  - delivery retry or repeated send attempts
- Route tests should verify a confirmed crisis route creates a durable alert record without breaking the existing `crisis_routed` user response contract.
- Add failure-path tests showing delivery failure leaves the underlying alert persisted and records a separate delivery incident/signal.
- Add tests for borderline or medium-confidence routing so alert framing preserves classification nuance rather than labeling all alerts as highest severity.
- Preserve the standard backend quality bar: `pytest`, `ruff`, and `mypy`.

### Project Structure Notes

- The architecture document prefers a small `operator/` internal surface and explicitly separates operational visibility from routine transcript exposure. A dedicated alerting module under `backend/app/operator/` fits that direction better than burying the logic inside generic `ops/signals.py`. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- The live repo does not yet have a dedicated crisis-alert persistence model. That is a real gap between architecture intent and current code, and Story `3.5` is the right place to close it. [Source: /home/erda/Музыка/goals/backend/app/models.py]
- `session_bootstrap.py` already acts as the request-path orchestrator; keep it thin by calling a dedicated alerting seam instead of embedding alert construction, dedupe rules, and delivery code directly in the route flow. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Existing `SafetySignal` rows are useful as crisis evidence and classification history, but they are not a substitute for an operator-facing alert lifecycle. Treat them as source inputs, not as the full operator-alert model. [Source: /home/erda/Музыка/goals/backend/app/models.py]

### References

- Story source and acceptance criteria: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md]
- Product privacy and operator-boundary requirements: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
- Architecture boundaries and operator visibility model: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- UX requirement that safety-sensitive operations should not feel like surveillance: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Previous story context for crisis routing and resource delivery: [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-4-presenting-crisis-help-resources-and-a-safer-next-action.md]
- Live request-path orchestrator: [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Live safety assessment seam: [Source: /home/erda/Музыка/goals/backend/app/safety/service.py]
- Live crisis-copy/resource seam: [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py]
- Existing session and signal models: [Source: /home/erda/Музыка/goals/backend/app/models.py]
- Existing retryable failure-signal helper: [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py]
- Backend dependency and tooling baseline: [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- Existing crisis route tests: [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-selected from `/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog story in order: `3-5-operator-alerting-without-routine-exposure-to-content`.
- Loaded and followed `_bmad/core/tasks/workflow.xml` with workflow config `_bmad/bmm/workflows/4-implementation/create-story/workflow.yaml`.
- Analyzed planning artifacts: `epics.md`, `architecture.md`, `prd.md`, and `ux-design-specification.md`.
- Loaded prior Epic 3 implementation context from `3-4-presenting-crisis-help-resources-and-a-safer-next-action.md` and supporting `3-3` context.
- Inspected live backend seams in `backend/app/conversation/session_bootstrap.py`, `backend/app/safety/service.py`, `backend/app/safety/escalation.py`, `backend/app/ops/signals.py`, `backend/app/models.py`, and existing crisis route tests.
- Confirmed no `project-context.md` exists in this workspace.
- Confirmed the current workspace root is not a Git repository, so git-history intelligence from the workflow was unavailable.
- Triggered party-mode during the first checkpoint and used the synthesized contributions of SM, Architect, and Dev personas to sharpen scope, dedupe requirements, and privacy boundaries for Story `3.5`.
- Entered `#yolo` mode for the remainder of the document after the second checkpoint to complete the story without further pause.
- No reliable additional framework-specific constraints were required beyond the repo’s pinned dependency set, so implementation guidance is anchored primarily to the live codebase and project artifacts.
- Implemented durable `OperatorAlert` persistence in `backend/app/models.py` with bounded metadata payload, delivery state, dedupe key, attempt count, and timestamps.
- Added `backend/app/ops/alerts.py` as the operator-alert lifecycle seam with bounded payload creation, session-level dedupe, inbox delivery, and retryable failure signaling.
- Wired crisis routing in `backend/app/conversation/session_bootstrap.py` to create operator alerts after confirmed crisis routing without breaking the existing user-facing `crisis_routed` contract.
- Added `/api/v1/ops/alerts` in `backend/app/ops/api.py` to expose a token-protected transcript-free ops inbox view over durable operator alerts.
- Added Alembic migration `a7f9c3d2b4e1_add_operator_alert_table.py` and applied `uv run alembic upgrade heads` against the local Postgres runtime using `POSTGRES_PASSWORD=example`.
- Added new unit and route coverage in `backend/tests/operator/test_alerts.py`, `backend/tests/api/routes/test_telegram_session_entry.py`, and `backend/tests/api/routes/test_ops_routes.py`.
- Validation commands executed with explicit DB env:
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run alembic upgrade heads`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest backend/tests/operator/test_alerts.py backend/tests/api/routes/test_telegram_session_entry.py backend/tests/api/routes/test_ops_routes.py -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest backend/tests -q`
  - `uv run ruff check backend/app backend/tests`
  - `uv run mypy backend/app backend/tests`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story `3.5` is intentionally limited to crisis-operator alert creation, bounded payload delivery, dedupe/traceability, and delivery-failure observability.
- Default operator alerts should remain metadata-first and must not expose full raw transcript content.
- A dedicated durable alert model is preferable to overloading `SummaryGenerationSignal`, which is currently summary-failure oriented.
- Persist the alert before channel delivery so notification failures do not silently erase the underlying safety event.
- Reuse existing crisis-state and safety-classification fields to avoid inventing a second safety interpretation pipeline.
- Deep transcript access and controlled investigation remain out of scope for this story and belong in Story `3.6`.
- Added a minimal MVP operational channel as a durable `ops` inbox plus authenticated `/ops/alerts` read path.
- Delivery failures now leave the alert record queryable and emit `operator_alert_delivery_failed` through the existing retryable signal mechanism.
- Repeated crisis routing for the same session updates a single durable alert lifecycle instead of flooding the operator channel with unbounded duplicates.
- Full regression, focused alerting tests, Ruff, and mypy passed against the local Postgres runtime (`postgres/example` on `localhost:5432`).

### File List

- _bmad-output/implementation-artifacts/3-5-operator-alerting-without-routine-exposure-to-content.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/alembic/versions/a7f9c3d2b4e1_add_operator_alert_table.py
- backend/app/conversation/session_bootstrap.py
- backend/app/models.py
- backend/app/ops/alerts.py
- backend/app/ops/api.py
- backend/tests/api/routes/test_ops_routes.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/conftest.py
- backend/tests/operator/test_alerts.py

## Change Log

- 2026-03-14: Implemented durable operator-alert persistence, transcript-free ops inbox exposure, crisis-route alert wiring, dedupe on repeated crisis routing, and visible delivery-failure handling for Story `3.5`.
- 2026-03-14: Code review fixes: H2 — added IntegrityError handling for concurrent alert creation race condition; M1 — corrected mislabeled signal_type from `operator_alert_delivery_failed` to `operator_alert_creation_failed` in outer session_bootstrap catch; M2 — replaced raw SQL `text("created_at DESC")` with typed `OperatorAlert.created_at.desc()`; M3 — added route-level test for borderline crisis routing preserving classification nuance in alert (AC6); M5 — unified delivery timestamps via single `delivered_now` variable.
