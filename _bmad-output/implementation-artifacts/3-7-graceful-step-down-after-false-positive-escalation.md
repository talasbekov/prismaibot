# Story 3.7: Graceful step-down after false positive escalation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user affected by an overly strong crisis interpretation,
I want чтобы продукт мягко снимал слишком сильную crisis framing, если она не соответствует моему реальному контексту,
so that trust не разрушается даже при false positive safety handling.

## Acceptance Criteria

1. When crisis escalation was activated but later conversational context shows the initial interpretation was too strong, the product can gently step down from crisis framing, and the transition does not read like blame toward the user or a system-dump apology. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-37-graceful-step-down-after-false-positive-escalation]
2. When crisis framing is softened for a still-vulnerable user, the language stays respectful, calm, and non-shaming, and the conversation does not jump abruptly back into normal reflective mode. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-37-graceful-step-down-after-false-positive-escalation] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
3. When step-down happens after an escalation message was already sent, the product returns to normal reflective flow through gentle bridging language, and the user does not receive contradictory or whiplash-like messaging. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-37-graceful-step-down-after-false-positive-escalation] [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py]
4. When false-positive recovery fails or leaves state uncertain, the failure becomes observable as a safety-relevant issue, and the product does not pretend graceful recovery already happened while state is unresolved. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#story-37-graceful-step-down-after-false-positive-escalation] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

## Tasks / Subtasks

- [x] Add explicit false-positive recovery state to the crisis-routing path instead of relying on sticky `crisis_active` forever (AC: 1, 3, 4)
  - [x] Extend `TelegramSession` crisis-state handling in `backend/app/models.py` beyond `normal | crisis_active` with a bounded recovery representation such as `step_down_pending` / `step_down_completed`, or equivalent fields that let request-path orchestration distinguish active crisis routing from recovery.
  - [x] Add an Alembic migration under `backend/app/alembic/versions/` for the new state or markers.
  - [x] Keep persistence and state names explicit and `snake_case`; do not hide recovery state only inside `last_bot_prompt`.
- [x] Implement step-down detection and state transition rules in the conversation request path (AC: 1, 2, 3, 4)
  - [x] Update `backend/app/conversation/session_bootstrap.py` so a session already in crisis mode can evaluate later safe/non-blocking context and decide whether to enter a recovery path instead of hard-routing every subsequent message back to crisis copy.
  - [x] Keep the decision bounded and conservative: step down only after explicit conditions that indicate over-escalation or false positive, not on a single ambiguous token.
  - [x] Ensure unresolved or failed recovery leaves the session in a safety-conscious state and records an observable ops/safety signal.
- [x] Add dedicated calm step-down messaging with bridge-back copy (AC: 1, 2, 3)
  - [x] Introduce a dedicated step-down response builder in `backend/app/safety/escalation.py` or an adjacent safety messaging seam, rather than burying recovery copy in generic clarification or closure components.
  - [x] The copy must acknowledge sensitivity, soften framing without system self-justification, and bridge into the next reflective move in a non-whiplash way.
  - [x] Preserve the product boundary and non-medical tone while clearly signaling that the conversation can continue in a calmer reflective mode.
- [x] Preserve ops learning and false-positive traceability without making user recovery depend on operator review (AC: 1, 4)
  - [x] Reuse the existing `false_positive_review` / `false_positive` investigation vocabulary in `backend/app/ops/investigations.py` as the operator-side learning seam.
  - [x] Do not require an operator to close an investigation before the user-facing conversation can recover.
  - [x] If recovery occurs automatically, leave enough durable state or signal metadata for later operator review and safety tuning.
- [x] Add failure visibility for step-down and recovery uncertainty (AC: 4)
  - [x] Record a bounded retryable signal when step-down evaluation or recovery copy generation fails.
  - [x] Make it clear in state and tests that the system does not claim recovery succeeded if persistence, messaging, or transition logic failed partway through.
- [x] Add focused tests for state transitions, message tone, and non-whiplash behavior (AC: 1, 2, 3, 4)
  - [x] Extend `backend/tests/api/routes/test_telegram_session_entry.py` to cover crisis-to-recovery transitions, including the current sticky-crisis branch that must now step down under defined conditions.
  - [x] Add/update `backend/tests/safety/test_escalation.py` to validate bounded step-down copy alongside crisis copy.
  - [x] Add model/service tests proving unresolved failure keeps the session safety-visible and does not silently drop into normal mode.
  - [x] Run `pytest`, `ruff`, and `mypy`.

## Dev Notes

- Story 3.7 is the user-facing counterpart to Story 3.6. Story 3.6 added operator-side `false_positive_review` and `false_positive` investigation outcomes; this story should add the user-facing recovery behavior after an over-strong escalation. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-6-controlled-investigation-path-for-critical-safety-incidents.md] [Source: /home/erda/Музыка/goals/backend/app/ops/investigations.py]
- The live request path currently hard-sticks any session with `crisis_state == "crisis_active"` into crisis routing, even when a later message is safe. That is the main behavior this story must deliberately change. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- `session_bootstrap.py` already treats crisis routing as a request-path orchestration concern, while `safety/escalation.py` owns the crisis copy variants and copy validation. Keep that separation and add step-down behavior through those seams rather than scattering it into unrelated conversation components. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py] [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py]
- The existing crisis copy is intentionally bounded, calm, and validation-checked. Step-down copy should meet the same bar: short, Telegram-readable, non-medical, and not defensive. [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- UX and PRD rules are explicit that safety transitions must feel humane and that false positives need a graceful step-down path. This is not a nice-to-have polish item; it is part of preserving trust in a safety-sensitive product. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Existing alert payloads intentionally avoid transcript exposure by default, and investigation access is explicit. Keep that privacy posture intact. Story 3.7 should not add broad transcript retention just to support recovery. [Source: /home/erda/Музыка/goals/backend/app/ops/alerts.py] [Source: /home/erda/Музыка/goals/backend/app/ops/investigations.py]
- No `project-context.md` exists in this workspace, so implementation guidance is based on live backend seams plus planning artifacts only.

### Project Structure Notes

- Respect the live backend layout under `backend/app/`, not the aspirational `src/goals/...` structure from planning docs.
- Primary files to change:
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/safety/escalation.py`
  - `backend/app/models.py`
  - a new Alembic migration in `backend/app/alembic/versions/`
- Likely related files:
  - `backend/app/safety/service.py`
  - `backend/app/ops/signals.py`
  - `backend/app/ops/investigations.py`
  - `backend/tests/api/routes/test_telegram_session_entry.py`
  - `backend/tests/safety/test_escalation.py`
- Avoid implementing Story 3.7 mainly inside:
  - `backend/app/conversation/first_response.py`
  - `backend/app/conversation/clarification.py`
  - `backend/app/conversation/closure.py`
  - `backend/app/memory/`
- Keep ownership clear:
  - `conversation/` decides request-path transition timing
  - `safety/` owns classification semantics and step-down/crisis wording
  - `ops/` owns review and learning visibility

### Technical Requirements

- Replace the current binary crisis stickiness with an explicit recovery-aware state machine or equivalent bounded recovery flags. The current `normal | crisis_active` model is insufficient for graceful step-down because safe follow-up messages still route through the sticky crisis branch. [Source: /home/erda/Музыка/goals/backend/app/models.py] [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Keep step-down detection conservative. A single non-risk message should not automatically erase safety context unless the story’s logic deliberately establishes that the previous escalation was too strong. This is an inference from the product’s safety posture and the requirement to avoid abrupt mode-switching. [Inference based on: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md, /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Add a dedicated response path for false-positive recovery. Reusing crisis copy or dropping directly into normal clarification risks contradictory messaging and whiplash. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md] [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py]
- Recovery copy must preserve product boundary and calm tone: no blame, no “system error” dump, no clinical language, no abrupt switch from crisis warning to ordinary advice. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
- Failure handling must be observable. If step-down evaluation, state persistence, or recovery-message generation fails, record a bounded safety/ops signal and keep the session in a safety-visible state rather than silently pretending recovery happened. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md] [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py]
- Preserve operator learning seams but do not couple user recovery to ops review latency. Existing investigation outcomes can inform later analysis, but the request path must be able to recover on its own when appropriate. [Source: /home/erda/Музыка/goals/backend/app/ops/investigations.py]

### Architecture Compliance

- Preserve the privacy-first architecture: no routine transcript visibility, no broad transcript rehydration to make step-down work. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Keep module boundaries intact:
  - `conversation/session_bootstrap.py` owns routing/orchestration
  - `safety/service.py` owns detection/classification
  - `safety/escalation.py` owns crisis and recovery wording
  - `ops/` owns investigation and learning follow-up
- Prefer additive implementation: introduce explicit recovery state or fields rather than encoding recovery implicitly in free-text prompts.
- Keep internal signaling consistent with the architecture’s error/ops visibility rules; false-positive recovery failures should surface as operator-meaningful signals, not only logs.

### Library / Framework Requirements

- Maintain compatibility with the current backend stack pinned in `backend/pyproject.toml`: FastAPI `0.114.x`, SQLModel `0.0.21`, `python-telegram-bot 21.x`, and Pydantic `2.x`. Do not turn this story into a dependency upgrade. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- Use the same SQLModel/Pydantic patterns already present in `backend/app/models.py` and route schemas. [Source: /home/erda/Музыка/goals/backend/app/models.py]
- Keep Telegram message formatting bounded for readability, following the existing escalation copy validation style instead of introducing long multi-message essays. [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py]

### File Structure Requirements

- Primary implementation files:
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/safety/escalation.py`
  - `backend/app/models.py`
- New file expected:
  - new Alembic migration in `backend/app/alembic/versions/`
- Test files:
  - `backend/tests/api/routes/test_telegram_session_entry.py`
  - `backend/tests/safety/test_escalation.py`
  - optionally a dedicated safety/service or conversation routing test if the state machine becomes complex

### Testing Requirements

- Add tests proving a previously crisis-routed session can enter a bounded recovery path after defined false-positive conditions.
- Add tests proving recovery copy is calm, non-shaming, and bridge-oriented rather than contradictory.
- Add tests proving unresolved recovery failures keep safety visibility and do not silently return to normal flow.
- Update sticky-crisis tests so they still protect against unsafe premature recovery while allowing the new intended step-down path.
- Preserve the backend quality bar: `pytest`, `ruff`, and `mypy`.

### Previous Story Intelligence

- Story 3.6 already established the operator-side vocabulary and audit trail for false-positive review. Reuse that terminology and keep the user-facing step-down separate from operator investigation mechanics. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-6-controlled-investigation-path-for-critical-safety-incidents.md]
- Story 3.6 also reinforced that default ops surfaces remain transcript-free. Story 3.7 should not weaken that privacy boundary while implementing recovery. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-6-controlled-investigation-path-for-critical-safety-incidents.md]

### Git Intelligence Summary

- Git history was unavailable because `/home/erda/Музыка/goals` is not a Git repository in this workspace, so no commit-pattern analysis could be performed.

### Latest Tech Information

- Official FastAPI release notes have advanced beyond the repo pin, but this story should stay inside the existing `0.114.x` project baseline and avoid assuming newer helpers. [Source: https://fastapi.tiangolo.com/release-notes/]
- Official SQLModel release notes continue to support the current `0.0.21` style already used in the repo, so adding recovery-state fields or related persistence should not require ORM strategy changes. [Source: https://sqlmodel.tiangolo.com/release-notes/]
- Official Pydantic changelog confirms the active v2 line; continue using current v2 model validation patterns already present in the codebase. [Source: https://docs.pydantic.dev/changelog/]
- Official `python-telegram-bot` docs remain async-first; this story should stay focused on backend request-path behavior rather than broadening Telegram integration scope. [Source: https://docs.python-telegram-bot.org/en/stable/]

### References

- Story source and acceptance criteria: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md]
- Product requirements and safety posture: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
- Architecture boundaries and operator visibility rules: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- UX requirements for calm, non-shaming, non-whiplash recovery: [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Previous story context for false-positive investigation and review vocabulary: [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-6-controlled-investigation-path-for-critical-safety-incidents.md]
- Live request-path orchestrator: [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Live safety classification seam: [Source: /home/erda/Музыка/goals/backend/app/safety/service.py]
- Live crisis messaging seam: [Source: /home/erda/Музыка/goals/backend/app/safety/escalation.py]
- Live model definitions: [Source: /home/erda/Музыка/goals/backend/app/models.py]
- Live ops investigations seam: [Source: /home/erda/Музыка/goals/backend/app/ops/investigations.py]
- Existing route coverage around crisis routing: [Source: /home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py]
- Existing safety copy coverage: [Source: /home/erda/Музыка/goals/backend/tests/safety/test_escalation.py]
- Backend dependency baseline: [Source: /home/erda/Музыка/goals/backend/pyproject.toml]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-selected from `/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog story in order: `3-7-graceful-step-down-after-false-positive-escalation`.
- Loaded and followed `_bmad/core/tasks/workflow.xml` with workflow config `_bmad/bmm/workflows/4-implementation/create-story/workflow.yaml`.
- Analyzed planning artifacts: `epics.md`, `architecture.md`, `prd.md`, and `ux-design-specification.md`.
- Loaded previous Epic 3 story context from `3-6-controlled-investigation-path-for-critical-safety-incidents.md`.
- Inspected live backend seams in `backend/app/conversation/session_bootstrap.py`, `backend/app/safety/service.py`, `backend/app/safety/escalation.py`, `backend/app/ops/investigations.py`, and `backend/app/models.py`.
- Inspected existing crisis-routing and safety tests in `backend/tests/api/routes/test_telegram_session_entry.py` and `backend/tests/safety/test_escalation.py`.
- Confirmed no `project-context.md` exists in this workspace.
- Confirmed the current workspace root is not a Git repository, so git-history intelligence from the workflow was unavailable.
- Checked official docs for FastAPI, SQLModel, Pydantic, and python-telegram-bot to avoid embedding stale framework guidance; implementation advice remains pinned to the repo’s current dependency versions.
- Added `TelegramSession.crisis_step_down_at` plus a new Alembic migration `e7b9c1d2f3a4_add_crisis_step_down_tracking.py`.
- Added conservative false-positive recovery detection in `backend/app/safety/service.py` and exported it through the safety seam.
- Added `compose_crisis_step_down_response()` plus validation rules in `backend/app/safety/escalation.py`.
- Updated `backend/app/conversation/session_bootstrap.py` to:
  - enter `step_down_pending` on a safe correction after crisis routing,
  - emit `crisis_step_down` responses with `safety_recovery_step_down`,
  - resume normal reflective flow on the next safe turn,
  - keep the session in crisis mode and record `safety_step_down_failed` if recovery composition fails.
- Added route and safety tests covering crisis step-down, resume behavior, and recovery-failure visibility.
- Ran migration and validation commands with explicit DB env:
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run alembic upgrade heads`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests/safety/test_escalation.py tests/api/routes/test_telegram_session_entry.py -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5432 POSTGRES_USER=postgres POSTGRES_PASSWORD=example POSTGRES_DB=app uv run pytest tests -q`
  - `uv run ruff check --fix app tests`
  - `uv run ruff check app tests`
  - `uv run mypy app tests`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story `3.7` is intentionally scoped to user-facing graceful recovery after false-positive or over-strong crisis escalation.
- The main implementation risk is the current sticky `crisis_active` branch in `session_bootstrap.py`; copy-only changes will not satisfy the story.
- Recovery must stay calm, respectful, non-shaming, and avoid contradictory jump-cuts back into normal reflective flow.
- Operator-side false-positive learning from Story `3.6` should remain reusable, but user recovery must not wait on manual review.
- Default ops and alerting privacy boundaries remain intact; no broad transcript retention should be added for this story.
- Implemented an explicit recovery seam with `step_down_pending` state and `crisis_step_down_at` tracking on `TelegramSession`.
- Added a conservative false-positive recovery detector that only steps down when a crisis-active session receives a safe corrective message, not on a generic non-crisis follow-up.
- Added a bounded two-message step-down response that acknowledges over-strong framing, keeps an осторожный tone, and bridges back with one focused reflective question.
- Kept failed recovery in a safety-visible path with `safety_step_down_failed` retryable signaling and `crisis_mode_active` response semantics.
- Prevented abrupt closure immediately after step-down by resuming one clarification turn before normal closure logic can reapply.
- Full backend regression suite passed: `215 passed`.
- Ruff and mypy passed after import normalization and validation.
- Resolved a pre-existing full-suite inconsistency in operator-investigation deny-path expectations by aligning the test with the audit-safe denied behavior already exercised elsewhere in the suite.

### File List

- _bmad-output/implementation-artifacts/3-7-graceful-step-down-after-false-positive-escalation.md
- backend/app/alembic/versions/e7b9c1d2f3a4_add_crisis_step_down_tracking.py
- backend/app/conversation/session_bootstrap.py
- backend/app/models.py
- backend/app/ops/investigations.py
- backend/app/safety/__init__.py
- backend/app/safety/escalation.py
- backend/app/safety/service.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/operator/test_investigations.py
- backend/tests/safety/test_escalation.py

## Change Log

- 2026-03-14: Implemented graceful false-positive step-down for crisis-routed sessions, including explicit recovery state, bounded bridge-back messaging, failure signaling, migration support, and route/safety regression coverage.
- 2026-03-14: Code review fixes applied — (H1) fixed `newly_activated` logic for `step_down_pending` state to prevent wrong copy variant on re-escalation; (H2+M3) added tests for `step_down_pending` + crisis and borderline message paths; (M1) added `crisis_step_down_at` to operator investigation context payload; (M2) tightened `step_down_pending` resume condition to `classification == "safe"` only; extended `should_route_to_crisis` to include `step_down_pending` so borderline messages during recovery route back to crisis rather than falling through to normal flow; (M4) removed ambiguous "не хочу умирать" from false-positive recovery patterns.
