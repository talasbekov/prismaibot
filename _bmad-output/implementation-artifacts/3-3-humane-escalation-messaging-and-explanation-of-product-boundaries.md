# Story 3.3: Humane escalation messaging и объяснение границ продукта

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь в кризисном или потенциально опасном состоянии,
I want чтобы продукт отвечал бережно, серьезно и честно о своих границах,
so that я не чувствую отвержения и понимаю, что мне нужна более подходящая форма помощи.

## Acceptance Criteria

1. When a session is already routed into `crisis_active` mode, the escalation reply starts by acknowledging the seriousness of the user's state in a calm, humane tone and does not read like a cold refusal, legal disclaimer dump, or abrupt system rejection. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-33-humane-escalation-messaging-и-объяснение-границ-продукта] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
2. When the bot explains the product boundary in a crisis-aware path, it clearly states that the product is not a sufficient form of help for this situation without using diagnostic language, moral judgment, or shaming tone. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-33-humane-escalation-messaging-и-объяснение-границ-продукта] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
3. When escalation messaging replaces the ordinary reflective continuation in Telegram, the text remains readable, direct, and emotionally supportive instead of turning into a long overloaded block that increases cognitive burden under stress. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-33-humane-escalation-messaging-и-объяснение-границ-продукта] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
4. When the crisis trigger is active, the message ends by steering the user toward a safer support path and framing safety plus the immediate next step, rather than centering the wording on the product "refusing to help". [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-33-humane-escalation-messaging-и-объяснение-границ-продукта] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
5. When the risk signal may be ambiguous or partially uncertain, the escalation wording stays soft enough not to intensify shame, fear, or resistance and does not lock the conversation into a stronger crisis interpretation than the current context justifies. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-33-humane-escalation-messaging-и-объяснение-границ-продукта] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
6. When escalation-copy generation fails or produces disallowed unsafe phrasing, the unsafe output is blocked before send and the failure becomes observable as a safety-critical messaging issue rather than silently leaking unsafe wording to the user. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-33-humane-escalation-messaging-и-объяснение-границ-продукта] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

## Tasks / Subtasks

- [x] Replace the current placeholder crisis copy with a bounded humane escalation messaging seam in `safety/` (AC: 1, 2, 3, 4, 5)
  - [x] Extend `backend/app/safety/escalation.py` so crisis responses are generated from explicit message variants instead of the current minimal routing placeholder.
  - [x] Keep the response owned by `safety/` and consumed through `compose_crisis_routing_response()` from `session_bootstrap.py`; do not move escalation copy into `conversation/first_response.py`, `clarification.py`, or `closure.py`.
  - [x] Preserve the existing routing behavior from Story 3.2: this story upgrades the wording and boundary explanation, not the state machine or crisis activation logic.
- [x] Encode product-boundary language that is honest but non-clinical (AC: 1, 2, 4)
  - [x] Add explicit wording rules or typed variants that say the product is not enough for this situation without claiming to be a therapist, doctor, diagnosis tool, or crisis service.
  - [x] Ensure the copy acknowledges seriousness first, then explains the product boundary, then points toward a safer next step.
  - [x] Avoid legalistic, moralizing, or shame-inducing phrases such as blunt refusal framing, diagnostic labeling, or panic wording.
- [x] Support ambiguity-sensitive crisis wording without overcommitting to the strongest interpretation (AC: 3, 5)
  - [x] Provide a softer variant for ambiguous or partially uncertain crisis states, reusing existing safety assessment metadata instead of inventing a second interpretation pipeline.
  - [x] Keep messages short enough for Telegram readability and low cognitive load under stress.
  - [x] Ensure already-active `crisis_active` sessions continue to receive bounded humane messaging on later turns without reopening normal reflection.
- [x] Add a pre-send safety guard for escalation copy and observable failure handling (AC: 6)
  - [x] Introduce a bounded validation layer for escalation messages, such as an internal rule check over generated/static variants, before the text is returned to the webhook response.
  - [x] Reuse the existing retryable ops signal pattern for messaging failures instead of inventing a parallel reporting mechanism.
  - [x] Return a minimal safe fallback response if humane escalation copy cannot be validated, and make the incident operator-visible as a safety-critical messaging problem.
- [x] Cover the messaging behavior with focused tests and preserve the backend quality bar (AC: 1, 2, 3, 4, 5, 6)
  - [x] Update `backend/tests/safety/test_escalation.py` to assert seriousness acknowledgment, non-reflective wording, boundary explanation, and bounded message length/shape.
  - [x] Add route-level tests in `backend/tests/api/routes/test_telegram_session_entry.py` proving crisis responses no longer use only routing placeholder copy and still suppress ordinary reflection.
  - [x] Add tests for ambiguous-crisis wording and failure-path observability when unsafe escalation output is blocked.
  - [x] Run `pytest`, `ruff`, and `mypy`.

## Dev Notes

- Story 3.2 already established the routing seam and persistent session state for crisis handling. Story 3.3 should build on that existing `crisis_active` path and improve the user-facing copy, not redesign the crisis-state machine. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-2-switching-from-normal-flow-to-crisis-aware-escalation-flow.md] [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- The current implementation seam is `backend/app/safety/escalation.py`, which returns a `CrisisRoutingResponse` with short placeholder messages. This story should evolve that seam into humane escalation messaging while keeping ownership inside `safety/`. [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py] [Source: /home/erda/Музыка/goals/backend/app/safety/__init__.py]
- Product positioning is strict: the system is a non-medical self-reflection tool, not a therapist, doctor, diagnostic product, or crisis service. Messaging must explain insufficiency for the current situation without sounding clinical, diagnostic, or role-confused. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
- UX requirements are explicit for safety-sensitive transitions: acknowledge seriousness calmly, avoid panic language, keep the user feeling accompanied rather than dropped, and keep the next step clearer than a generic "you need help". [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Scope discipline matters. Story 3.3 is about humane messaging and product-boundary explanation only. Static crisis links/resources belong to Story 3.4, operator alert fan-out belongs to Story 3.5, and graceful step-down belongs to Story 3.7. Do not collapse those stories into this one. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md]
- Observable failure handling is required for communication-sensitive paths. If escalation copy validation fails, reuse the existing retryable ops-signal pattern instead of logging silently or inventing a new subsystem. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md] [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py]
- The app already exposes `inline_keyboard` in `TelegramWebhookResponse`, but Story 3.3 should avoid turning this into the resource-delivery story. If buttons are added at all, they must remain minimal and not duplicate the explicit crisis-links step planned for Story 3.4. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Testing should focus on message properties and guardrails, not brittle word-for-word snapshots only. Assert that the output acknowledges seriousness, explains the boundary, avoids reflective prompts/questions, stays bounded in length, and preserves crisis routing action semantics. [Source: /home/erda/Музыка/goals/backend/tests/safety/test_escalation.py] [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py]

### Technical Requirements

- Keep crisis escalation behavior owned by `safety/`; `conversation/` continues to orchestrate but should not own the wording logic. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Reuse existing session fields such as `TelegramSession.crisis_state`, `safety_classification`, `safety_trigger_category`, and `safety_confidence` to select message variants. Do not add a new persistence model just for copy selection unless a clear gap appears during implementation. [Source: /home/erda/Музыка/goals/backend/app/models.py]
- Keep raw crisis text transient. Do not persist long-form escalation copy inputs or any new transcript-like safety payloads beyond bounded operational metadata. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
- Preserve the current `crisis_routed` action contract in the webhook response unless there is a compelling compatibility reason to change it and tests are updated consistently. [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py] [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py]
- If a pre-send validation layer is added, keep it deterministic and local. This story does not need a second LLM call to "check" crisis copy. Prefer typed variants and explicit content-rule checks. This is an inference from the existing architecture emphasis on bounded, reliable request-path behavior and low operational risk. [Inference based on: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md, /home/erda/Музыка/goals/backend/app/safety/escalation.py]

### Architecture Compliance

- Respect the actual repo layout under `backend/app/`, not the aspirational `src/goals/...` structure in the architecture doc. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-2-switching-from-normal-flow-to-crisis-aware-escalation-flow.md]
- Keep boundaries sharp:
  - `safety/` owns detection and escalation behavior.
  - `conversation/session_bootstrap.py` owns request-path orchestration and response packaging.
  - `operator/` and `ops/signals.py` own observability, not the content-generation logic itself.
- Failures in humane escalation generation should produce operator-meaningful signals, not only logs. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

### Library / Framework Requirements

- FastAPI response shapes must remain compatible with the existing `TelegramWebhookResponse` Pydantic model in `session_bootstrap.py`. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- The backend currently uses Pydantic v2, SQLModel 0.0.21, FastAPI 0.114.x, and python-telegram-bot 21.x. Use current project dependencies as the implementation target; do not introduce framework upgrades as part of this story. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- Any new validation helper for crisis copy should fit the existing strict mypy and Ruff setup. Avoid dynamic, weakly typed helpers that would degrade the backend quality bar. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]

### File Structure Requirements

- Primary implementation files:
  - `backend/app/safety/escalation.py`
  - `backend/app/safety/__init__.py`
  - `backend/app/conversation/session_bootstrap.py`
- Likely adjacent files for bounded failure reporting or typed helpers:
  - `backend/app/ops/signals.py`
  - optionally a small new helper under `backend/app/safety/` such as `message_rules.py` if `escalation.py` becomes too dense
- Primary tests:
  - `backend/tests/safety/test_escalation.py`
  - `backend/tests/api/routes/test_telegram_session_entry.py`
- Avoid implementing Story 3.3 in:
  - `backend/app/conversation/first_response.py`
  - `backend/app/conversation/clarification.py`
  - `backend/app/conversation/closure.py`
  - `backend/app/memory/`
  - operator transcript-inspection surfaces

### Testing Requirements

- Unit tests should verify both newly activated and already active crisis sessions produce humane, bounded, non-reflective messages.
- Route tests should verify crisis messaging still short-circuits normal reflection and keeps `action == "crisis_routed"`.
- Add coverage for ambiguous/borderline-sensitive wording selection if the implementation uses classification or confidence to soften phrasing.
- Add coverage for blocked/invalid escalation copy paths proving the fallback message is safe and an ops signal is recorded.
- Preserve the standard backend quality bar: `pytest`, `ruff`, and `mypy`.

### Project Structure Notes

- The architecture document prefers a richer `safety/` package with escalation-specific files, and the live repo already has the minimum seam in place: `backend/app/safety/escalation.py`. Extend that real seam rather than scattering message rules across generic helpers. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md] [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py]
- `conversation/session_bootstrap.py` currently packages webhook responses and owns failure fallback branching. Any new humane-messaging validation failure should integrate there through the existing crisis-routing call path, not by bypassing the request handler. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- No `project-context.md` was found in the workspace, so implementation should rely on the story file, planning artifacts, and current repo patterns only.

### References

- Story source and acceptance criteria: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md]
- Product boundary, trust, and safety wording constraints: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
- Architecture boundaries and communication-failure observability: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- UX rules for calm, humane escalation transitions: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Previous crisis-routing implementation context: [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-2-switching-from-normal-flow-to-crisis-aware-escalation-flow.md]
- Live crisis-copy seam: [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py]
- Live request-path orchestrator: [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Existing response model and inline keyboard shape: [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Existing safety assessment model: [Source: /home/erda/Музыка/goals/backend/app/safety/service.py]
- Durable session fields for crisis mode: [Source: /home/erda/Музыка/goals/backend/app/models.py]
- Existing ops-signal pattern: [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py]
- Backend dependency and tooling baseline: [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- Existing unit tests for crisis escalation: [Source: /home/erda/Музыка/goals/backend/tests/safety/test_escalation.py]
- Existing route tests for Telegram session entry: [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-selected from `/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog story in order after the already-created `3-2` story: `3-3-humane-escalation-messaging-and-explanation-of-product-boundaries`.
- Loaded and followed `_bmad/core/tasks/workflow.xml` with workflow config `_bmad/bmm/workflows/4-implementation/create-story/workflow.yaml`.
- Analyzed planning artifacts: `epics.md`, `prd.md`, `architecture.md`, and `ux-design-specification.md`.
- Loaded prior Epic 3 implementation context from `3-2-switching-from-normal-flow-to-crisis-aware-escalation-flow.md`.
- Inspected live backend seams in `backend/app/safety/escalation.py`, `backend/app/safety/service.py`, `backend/app/conversation/session_bootstrap.py`, `backend/app/models.py`, and `backend/tests/...` to keep the story aligned with the real codebase instead of only the architecture ideal.
- Confirmed the workspace is not a Git repository root here, so git-history intelligence from the workflow was not available.
- Confirmed `_bmad/core/tasks/validate-workflow.xml` does not exist in this workspace, so the checklist-validation invocation cannot be executed literally from Step 6 of the workflow.
- Tried official web lookup for current framework references on FastAPI, Pydantic, and python-telegram-bot, but the available web search responses did not return additional repo-relevant constraints beyond the already pinned local dependency set; the story therefore anchors implementation guidance to the workspace’s actual versions in `backend/pyproject.toml`.
- Marked sprint status `3-3-humane-escalation-messaging-and-explanation-of-product-boundaries` as `in-progress` before implementation and `review` after completion.
- Replaced the placeholder crisis copy in `backend/app/safety/escalation.py` with a typed message-variant catalog for high-concern activation, high-concern continuation, and softer continuation inside already-active crisis sessions.
- Added deterministic crisis-copy validation to block disallowed phrasing, overlong messages, question-ending prompts, and variants that fail to explain the product boundary or stop normal reflective flow.
- Updated `backend/app/conversation/session_bootstrap.py` to pass the current safety classification and confidence into the crisis messaging seam so sticky `crisis_active` sessions can use softer wording when the latest turn is no longer explicit crisis text.
- Added unit coverage for humane activation copy, continuation copy, softer continuation wording, and validator failure on unsafe phrases.
- Added route-level coverage ensuring first-turn crisis replies use humane boundary framing, safe follow-ups in `crisis_active` sessions use the softer variant, and invalid crisis copy is blocked while producing an operator-visible failure signal.
- Validation executed against the local Postgres instance on port `5433` because the default `5432` credentials fail in this workspace.
- Validation commands executed:
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest backend/tests/safety/test_escalation.py backend/tests/api/routes/test_telegram_session_entry.py -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest backend/tests -q`
  - `uv run ruff check backend/app backend/tests`
  - `uv run mypy backend/app backend/tests`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story `3.3` is intentionally limited to humane escalation wording and honest boundary explanation on top of the already existing `crisis_active` routing path.
- Static crisis links/resources remain in Story `3.4`; operator alert delivery remains in Story `3.5`; graceful step-down remains in Story `3.7`.
- The safest implementation direction is to upgrade `compose_crisis_routing_response()` with typed humane variants and deterministic copy-rule checks rather than introducing a second LLM pass for crisis copy generation.
- Messaging failures must be operator-visible and must not leak unsafe or cold/legalistic text to the user.
- Added explicit humane crisis variants that acknowledge seriousness, explain that the ordinary reflection format is insufficient, and steer the user toward a safer next step without medicalized or legalistic phrasing.
- Added a softer continuation variant for already-active `crisis_active` sessions when the latest turn is no longer explicit crisis language, preventing overcommitment to the strongest interpretation while still blocking ordinary reflection.
- Added deterministic validation for crisis copy so unsafe phrases such as blunt refusal framing or clinical wording are rejected before sending.
- Preserved the existing fallback path in `session_bootstrap.py`, so invalid crisis copy still returns a minimal safe response and records a retryable operator-visible failure signal.
- Full backend validation passed with `pytest`, `ruff`, and `mypy` on the `5433` Postgres test instance.

### File List

- _bmad-output/implementation-artifacts/3-3-humane-escalation-messaging-and-explanation-of-product-boundaries.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/safety/escalation.py
- backend/app/safety/__init__.py
- backend/app/conversation/session_bootstrap.py
- backend/tests/safety/test_escalation.py
- backend/tests/api/routes/test_telegram_session_entry.py

## Change Log

- 2026-03-13: Implemented humane crisis escalation messaging with typed variants, deterministic copy validation, softer continuation wording for sticky crisis sessions, and regression coverage for blocked unsafe phrasing and route-level crisis replies.
- 2026-03-13: Code review fixes — added validator rules for AC1 (seriousness acknowledgment in first message) and AC4 (next-step steering marker); added route-level test for high_concern_continuation path; added borderline/medium ambiguous-crisis unit test; exported CrisisMessagingValidationError from safety/__init__.py. All 175 tests pass, ruff and mypy clean.
