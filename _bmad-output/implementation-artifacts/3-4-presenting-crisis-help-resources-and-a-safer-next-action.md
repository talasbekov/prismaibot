# Story 3.4: Показ crisis-help resources и safer next action

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь, для которого сработала crisis-aware escalation,
I want получить понятные ресурсы помощи и ближайший безопасный следующий шаг,
so that после ответа бота у меня остается реальная опора, а не только сообщение о риске.

## Acceptance Criteria

1. When a crisis or high-risk signal has already routed the session into the escalation flow, the bot presents crisis-help resources or support links suitable for the escalation scenario and frames them as a practical next help option rather than a token disclaimer. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-34-показ-crisis-help-resources-и-safer-next-action] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
2. When the crisis-aware message is completed, the reply includes a safer next action the user can understand and act on immediately or soon, with calm and low-overload phrasing. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-34-показ-crisis-help-resources-и-safer-next-action] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
3. When resources are shown in MVP, the bot uses a static curated crisis-resource list from an approved source seam and does not generate ad hoc destinations or unverified help options on the fly. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-34-показ-crisis-help-resources-и-safer-next-action] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
4. When crisis resources and the safer next step are presented in Telegram, the output remains readable, scannable, and low-burden, and does not get mixed into a long reflective content block. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-34-показ-crisis-help-resources-и-safer-next-action] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
5. When suitable crisis resources are unavailable, incomplete, or cannot be reliably retrieved, the failure becomes observable as a safety-relevant issue and the product still returns a minimally safe escalation response instead of silently omitting help resources. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-34-показ-crisis-help-resources-и-safer-next-action] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
6. When the escalation path is active but the current user context remains partially uncertain, the support guidance stays serious and protective and does not soften back into normal reflective advice merely because the latest message is ambiguous. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-34-показ-crisis-help-resources-и-safer-next-action] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]

## Tasks / Subtasks

- [x] Add a curated crisis-resource seam owned by `safety/` (AC: 1, 3, 5)
  - [x] Create a typed static source such as `backend/app/safety/crisis_links.py` that contains the MVP-approved crisis/help resources and their display metadata.
  - [x] Keep the curated list local and deterministic; do not fetch dynamic resource destinations during request handling.
  - [x] Include only the minimum fields needed for Telegram presentation and low-burden fallback behavior.
- [x] Extend crisis routing output to include actionable support guidance (AC: 1, 2, 4, 6)
  - [x] Evolve the `CrisisRoutingResponse` shape in `backend/app/safety/escalation.py` so it can carry crisis-support text plus optional resource/button payload without moving copy ownership into `conversation/`.
  - [x] Add a bounded safer-next-step line that follows the humane boundary messaging from Story 3.3 and points the user toward immediate or near-immediate safer action.
  - [x] Preserve the existing sticky `crisis_active` behavior from Story 3.2/3.3 so already-routed sessions continue to receive protective support guidance even when the latest turn is not explicit crisis text.
- [x] Package crisis resources for Telegram in a low-burden format (AC: 1, 2, 4)
  - [x] Update `backend/app/conversation/session_bootstrap.py` and its response model only as needed to pass through the new crisis-support payload.
  - [x] Keep the message short and scannable; if buttons are used, keep them minimal and semantically clear.
  - [x] Prefer a small set of explicit actions/resources over a dense multi-option keyboard or large message block.
- [x] Add failure handling for missing or invalid crisis-resource payloads (AC: 5)
  - [x] Validate the crisis-resource output before send, similar to the bounded copy validation added in Story 3.3.
  - [x] Reuse `record_retryable_signal()` for operator-visible failure signaling instead of inventing a parallel alerting subsystem.
  - [x] Return a minimal safe crisis response if the approved resource set cannot be attached correctly.
- [x] Cover the resource-delivery behavior with focused tests (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add unit tests for the curated resource seam and crisis-routing payload shape under `backend/tests/safety/`.
  - [x] Extend route tests in `backend/tests/api/routes/test_telegram_session_entry.py` to assert crisis replies include the safer next step and bounded crisis-resource presentation.
  - [x] Add failure-path tests proving resource attachment issues do not fall back to normal reflection and produce an ops-visible signal.
  - [x] Run `pytest`, `ruff`, and `mypy`.

## Dev Notes

- Story 3.3 already established humane escalation wording and deterministic crisis-copy validation. Story 3.4 should build on that seam rather than rewrite the escalation-state machine or re-own the copy in `conversation/`. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-3-humane-escalation-messaging-and-explanation-of-product-boundaries.md] [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py]
- The current crisis path returns `CrisisRoutingResponse(messages=..., action="crisis_routed")` and is invoked via `_compose_crisis_routing_response()` from `backend/app/conversation/session_bootstrap.py`. Extend this seam; do not bypass it. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py] [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py]
- `TelegramWebhookResponse` already supports `inline_keyboard`, and the repo already uses a typed `InlineButton` model. That is the natural place for bounded resource CTA if the implementation chooses buttons. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Product and UX documents are explicit that MVP crisis resources come from a static curated list and should be presented as practical next help options, not as boilerplate. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- The sticky `crisis_active` session behavior is already implemented: safe follow-up messages in an active crisis session still route through the crisis seam. Story 3.4 must preserve that behavior while adding resource delivery. [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py]
- Failure handling must stay observable via the existing retryable ops-signal pattern. Story 3.4 is not the operator-alert fan-out story; it only needs bounded failure visibility when support-resource attachment fails. [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md]
- Scope discipline matters:
  - static crisis links/resources belong here in 3.4
  - operator alert delivery belongs in 3.5
  - controlled investigation path belongs in 3.6
  - graceful step-down logic belongs in 3.7
- No `project-context.md` was found in the workspace, so implementation guidance is anchored to the live repo and planning artifacts only.

### Technical Requirements

- Keep crisis-resource policy inside `app.safety`; `conversation/` may package the final response but should not become the owner of approved crisis destinations or support wording rules.
- Reuse the existing `SafetyAssessment`, `TelegramSession.crisis_state`, `safety_classification`, and `safety_confidence` fields to decide which crisis-support variant to send. Do not introduce a separate crisis-mode persistence model for this story. [Source: /home/erda/Музыка/goals/backend/app/safety/service.py] [Source: /home/erda/Музыка/goals/backend/app/models.py]
- The approved crisis-resource list must be static, typed, and local to the codebase for MVP. No runtime network lookup, geolocation-based lookup, or LLM-generated resource selection should occur on the request path. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
- Preserve the `action == "crisis_routed"` contract in webhook responses. Resource delivery should enrich the crisis response, not invent a second routing action unless the entire test suite is updated consistently. [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py] [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py]
- Keep crisis-resource output bounded for Telegram readability. If buttons are added, each button should represent one clear action only; do not overload button semantics or build a dense keyboard. This is an inference from the current typed response model plus official `python-telegram-bot` button conventions. [Inference based on: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py, https://docs.python-telegram-bot.org/en/v21.8/telegram.inlinekeyboardbutton.html]
- Any validation for resource payloads should remain deterministic and local, matching the project’s existing approach for crisis-copy validation. This story does not need a second model call to validate help resources. [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py] [Inference based on: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

### Architecture Compliance

- Respect the live repo layout under `backend/app/`, not the aspirational structure in the architecture doc.
- Keep boundaries explicit:
  - `safety/` owns crisis detection, crisis-support policy, and approved-resource composition
  - `conversation/session_bootstrap.py` owns request-path orchestration and Telegram response packaging
  - `ops/signals.py` owns failure visibility
- Do not leak crisis-resource rules into `conversation/first_response.py`, `clarification.py`, `closure.py`, or memory-related modules.
- Preserve text-first Telegram behavior. Resources are support-oriented additions to the crisis path, not a menu system replacing the conversation.
- Failures to attach or validate crisis resources must create operator-meaningful signals rather than only logs. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

### Library / Framework Requirements

- Maintain compatibility with the current backend stack in `backend/pyproject.toml`: FastAPI `0.114.x`, Pydantic `2.x`, SQLModel `0.0.21`, and `python-telegram-bot 21.x`. Do not introduce framework upgrade work as part of Story 3.4. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- Keep response schemas as typed Pydantic models. FastAPI’s current official guidance still centers response serialization and validation around Pydantic models, which matches the existing `TelegramWebhookResponse` seam. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py] [Source: https://fastapi.tiangolo.com/tutorial/response-model/]
- If the crisis response gains structured resource items or URL buttons, model them explicitly rather than passing raw untyped dicts. Pydantic v2 remains the project’s boundary-validation tool. [Source: https://docs.pydantic.dev/latest/concepts/models/] [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- If URL buttons are used, follow `python-telegram-bot`’s one-action-per-button rule and keep the keyboard small. [Source: https://docs.python-telegram-bot.org/en/v21.8/telegram.inlinekeyboardbutton.html]

### File Structure Requirements

- Primary implementation files:
  - `backend/app/safety/escalation.py`
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/safety/__init__.py`
- Likely new file:
  - `backend/app/safety/crisis_links.py`
- Likely adjacent file for reusable failure signaling:
  - `backend/app/ops/signals.py`
- Primary tests:
  - `backend/tests/safety/test_escalation.py`
  - add a focused safety unit test file if resource helpers become substantial, for example `backend/tests/safety/test_crisis_links.py`
  - `backend/tests/api/routes/test_telegram_session_entry.py`
- Avoid implementing Story 3.4 in:
  - `backend/app/conversation/first_response.py`
  - `backend/app/conversation/clarification.py`
  - `backend/app/conversation/closure.py`
  - `backend/app/memory/`
  - any operator-facing alert delivery module intended for Story 3.5

### Testing Requirements

- Unit tests should verify the approved crisis-resource list is deterministic, bounded, and suitable for crisis routing variants.
- Unit tests should verify crisis responses still contain humane boundary language plus the new safer-next-step/resource guidance without regressing Story 3.3 protections.
- Route tests should verify crisis replies still short-circuit normal reflection, preserve `action == "crisis_routed"`, and include the expected resource/CTA payload in Telegram response format.
- Add tests for sticky `crisis_active` sessions where the latest message is safe or borderline but support guidance must remain serious and protective.
- Add failure-path tests showing that invalid or missing resource payloads produce a safe fallback response and an ops-visible retryable signal.
- Preserve the standard backend quality bar: `pytest`, `ruff`, and `mypy`.

### Project Structure Notes

- The architecture doc already names `safety/crisis_links.py` as the natural home for static crisis links. Story 3.4 is the point where that planned seam should become real in the live repo. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- The current repo already centralizes crisis response generation in `backend/app/safety/escalation.py`; extending that seam is lower-risk than scattering resource logic across route handlers. [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py]
- `session_bootstrap.py` already converts domain response pieces into `TelegramWebhookResponse`. Keep that file thin and typed; do not bury crisis-resource policy there. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- The current ops-signal helper writes into the summary signal model rather than a dedicated safety-alert model. Reuse that existing mechanism for resource-attachment failures in this story and leave broader alert routing to Story 3.5. [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py]

### References

- Story source and acceptance criteria: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md]
- Product requirements and MVP static crisis-link direction: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
- Architecture boundaries, `crisis_links` seam, and operator-visible failure expectations: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- UX rules for calm, scannable support-resource presentation: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Previous story context for humane crisis messaging: [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-3-humane-escalation-messaging-and-explanation-of-product-boundaries.md]
- Live crisis routing seam: [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py]
- Live safety assessment seam: [Source: /home/erda/Музыка/goals/backend/app/safety/service.py]
- Live request-path orchestrator and Telegram response models: [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Existing session safety fields: [Source: /home/erda/Музыка/goals/backend/app/models.py]
- Existing retryable ops-signal pattern: [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py]
- Existing crisis-routing tests: [Source: /home/erda/Музыка/goals/backend/tests/safety/test_escalation.py]
- Existing Telegram route tests for crisis flow: [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py]
- FastAPI response model docs: [Source: https://fastapi.tiangolo.com/tutorial/response-model/]
- Pydantic model docs: [Source: https://docs.pydantic.dev/latest/concepts/models/]
- python-telegram-bot inline keyboard docs: [Source: https://docs.python-telegram-bot.org/en/v21.8/telegram.inlinekeyboardbutton.html]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-selected from `/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog story in order: `3-4-presenting-crisis-help-resources-and-a-safer-next-action`.
- Loaded and followed `_bmad/core/tasks/workflow.xml` with workflow config `_bmad/bmm/workflows/4-implementation/create-story/workflow.yaml`.
- Analyzed planning artifacts: `epics.md`, `architecture.md`, `prd.md`, and `ux-design-specification.md`.
- Loaded prior Epic 3 implementation context from `3-3-humane-escalation-messaging-and-explanation-of-product-boundaries.md`.
- Inspected live backend seams in `backend/app/safety/escalation.py`, `backend/app/safety/service.py`, `backend/app/safety/__init__.py`, `backend/app/conversation/session_bootstrap.py`, `backend/app/models.py`, `backend/app/ops/signals.py`, and existing crisis-flow tests.
- Confirmed no `project-context.md` exists in this workspace.
- Confirmed the current workspace root is not a Git repository, so git-history intelligence from the workflow was unavailable.
- Performed official-docs spot checks for FastAPI response models, Pydantic models, and `python-telegram-bot` inline keyboard guidance to avoid stale implementation advice.
- Entered `#yolo` mode for the remainder of the document after the first template-output checkpoint.
- Confirmed `_bmad/core/tasks/validate-workflow.xml` is missing in this workspace, so the Step 6 checklist-validation invocation cannot be executed literally.
- Implemented the static curated crisis-resource seam in `backend/app/safety/crisis_links.py`.
- Extended `CrisisRoutingResponse` with approved resources and URL-button payloads, keeping crisis-policy ownership inside `app.safety`.
- Updated `TelegramWebhookResponse` button typing to support either callback buttons or URL buttons with one explicit action per button.
- Reused the existing `safety_routing_failed` path so missing or invalid resource payloads still return a bounded safe response and create an operator-visible retryable signal.
- Created the `app` Postgres database inside the local `accessportal-db-1` container using `postgres/example` and applied Alembic migrations with `uv run alembic upgrade heads` for test execution.
- Validation commands executed with explicit DB env:
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests/safety/test_crisis_links.py tests/safety/test_escalation.py tests/api/routes/test_telegram_session_entry.py -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run ruff check app tests`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run mypy app tests`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story `3.4` is intentionally limited to static crisis-help resources and a clearer safer-next-step payload on top of the already-existing crisis escalation path.
- Static curated resources belong in `safety/`, not in general conversation handlers.
- Resource delivery must remain low-burden and scannable in Telegram; avoid long reflective blocks and overloaded keyboards.
- Failure to attach approved resources must not silently degrade into ordinary reflection.
- Operator alert fan-out remains out of scope for this story and belongs in Story `3.5`.
- Added three approved crisis resources with URL destinations for 988, 988 chat, and local-support discovery, keeping the list static and bounded to three items.
- Preserved `action == "crisis_routed"` while enriching crisis replies with safer-next-step copy and inline URL buttons.
- Kept sticky `crisis_active` routing intact for safe and borderline follow-up turns by keeping the softer crisis variant within the existing readability guardrail.
- Full regression suite, targeted safety tests, Ruff, and mypy passed against the local migrated Postgres test database.

### File List

- _bmad-output/implementation-artifacts/3-4-presenting-crisis-help-resources-and-a-safer-next-action.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/safety/escalation.py
- backend/app/safety/__init__.py
- backend/app/safety/crisis_links.py
- backend/app/conversation/session_bootstrap.py
- backend/tests/safety/test_crisis_links.py
- backend/tests/safety/test_escalation.py
- backend/tests/api/routes/test_telegram_session_entry.py

## Change Log

- 2026-03-14: Implemented static curated crisis resources, crisis URL-button delivery, deterministic resource validation/fallback behavior, and regression coverage for crisis resource presentation and failure handling.
- 2026-03-14: Code review fixes — added reverse button→resource URL validation (H1), removed dead `_NEXT_STEP_MARKERS` entry `"следующему шагу"` (H3), extracted `MAX_CRISIS_RESOURCE_COUNT` constant shared between `crisis_links.py` and `escalation.py` (M1), added button-label→resource-label parity check (M3), rewrote `test_crisis_links.py` to cover all 8 validation branches and use `pytest.raises` (H2, M2).
