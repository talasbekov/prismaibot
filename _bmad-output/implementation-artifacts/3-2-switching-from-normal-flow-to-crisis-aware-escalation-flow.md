# Story 3.2: Переключение из normal flow в crisis-aware escalation flow

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь, у которого в сообщении обнаружены кризисные сигналы,
I want чтобы продукт корректно переключал разговор из обычного reflective режима в более безопасный crisis-aware flow,
so that система не продолжает неподходящий normal conversation path в момент повышенного риска.

## Acceptance Criteria

1. When red-flag detection marks the current message or session as requiring crisis-aware handling, the normal reflective flow is interrupted and the system routes the conversation into a dedicated crisis-aware escalation path instead of continuing ordinary first-response, clarification, or closure behavior. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-32-Переключение-из-normal-flow-в-crisis-aware-escalation-flow] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
2. When a crisis signal is detected in the middle of an already active reflective session, the transition happens inside that same user session without contradictory state, and the previously active normal flow no longer continues as if nothing changed. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-32-Переключение-из-normal-flow-в-crisis-aware-escalation-flow] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
3. When the user was previously in `fast` or `deep` mode, crisis-aware routing takes priority over that conversational mode for the next unsafe step, so mode-specific reflection logic does not control the crisis transition. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-32-Переключение-из-normal-flow-в-crisis-aware-escalation-flow] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
4. When the detection result has high enough confidence for escalation, downstream response generation uses crisis-aware handling rules and does not emit standard situation breakdowns, routine reflective prompts, or ordinary next-step suggestions. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-32-Переключение-из-normal-flow-в-crisis-aware-escalation-flow] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
5. When an escalation trigger activates the crisis-aware path, the internal session state is updated to reflect that the session is in crisis-aware mode, so later stories for messaging, resources, and alerts can rely on stable downstream routing state. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-32-Переключение-из-normal-flow-в-crisis-aware-escalation-flow] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
6. When the flow-switching step cannot complete reliably, the failure becomes observable as a safety-relevant issue and the system does not silently fall back to ordinary reflective continuation. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-32-Переключение-из-normal-flow-в-crisis-aware-escalation-flow] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

## Tasks / Subtasks

- [x] Add an explicit crisis-routing state machine on top of the Story 3.1 safety seam (AC: 1, 2, 3, 5, 6)
  - [x] Extend the live session model with a bounded crisis-flow state such as `normal`, `crisis_active`, and any minimal transition metadata needed for deterministic routing.
  - [x] Update `conversation/session_bootstrap.py` so a `crisis` safety classification moves the session into crisis-aware mode inside the same session instead of returning a temporary `safety_hold` dead-end branch.
  - [x] Ensure previously selected `fast` or `deep` mode remains persisted but no longer governs the immediate unsafe turn once crisis routing is active.
- [x] Introduce a dedicated crisis-aware response seam owned outside normal reflection builders (AC: 1, 3, 4, 5)
  - [x] Add a focused `safety/` or `conversation/` crisis-routing component that returns a typed crisis-path response instead of reusing `first_response.py`, `clarification.py`, or `closure.py`.
  - [x] Keep Story 3.2 scoped to routing and state only: do not fully implement humane escalation copy, crisis-help resources, or operator alert delivery from Stories 3.3-3.5.
  - [x] Ensure the crisis-aware branch suppresses ordinary reflective breakdowns, routine next-step suggestions, and normal closure generation while the session is in crisis mode.
- [x] Persist and expose downstream-safe crisis state for later safety stories (AC: 2, 5, 6)
  - [x] Store only bounded routing metadata needed for later messaging, resources, alerts, and false-positive step-down, without turning raw crisis text into durable memory.
  - [x] Reuse the existing safety and ops signal patterns where possible so crisis-routing failures become observable without adding a second unrelated failure channel.
  - [x] Make repeat crisis messages or webhook retries idempotent enough that routing does not create contradictory session state.
- [x] Add regression coverage for first-turn crisis routing, mid-session switching, mode override, and failure handling (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add route/integration tests proving a crisis message on the first turn enters crisis-aware mode and does not call the standard first-trust branch.
  - [x] Add tests proving a later message flips an active reflective session into crisis-aware mode within the same session record.
  - [x] Add tests proving `fast` and `deep` modes do not control the next step after a crisis classification.
  - [x] Add tests proving routing failures produce an observable safety-relevant signal and do not silently continue the normal reflective path.
  - [x] Run the backend quality bar: `pytest`, `ruff`, and `mypy`.

## Dev Notes

- Story 3.1 already inserted the safety seam into the live Telegram request path and currently returns a temporary `safety_hold` action from `backend/app/conversation/session_bootstrap.py` when `evaluate_incoming_message_safety()` classifies a turn as `crisis`. Story 3.2 should replace that dead-end hold with a real crisis-aware routing branch that later stories can build on. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py] [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-1-detection-of-red-flag-signals-in-user-messages.md]
- The existing safety domain already owns classification and bounded signal persistence through `backend/app/safety/service.py` and the `SafetySignal` / `TelegramSession.safety_*` fields in `backend/app/models.py`. Story 3.2 should extend that ownership into crisis-routing state rather than moving crisis logic into `bot/` adapters or reflection builders. [Source: /home/erda/Музыка/goals/backend/app/safety/service.py] [Source: /home/erda/Музыка/goals/backend/app/models.py] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Scope discipline matters here: Story 3.2 is only about switching from normal flow to crisis-aware flow and persisting that routing state. Humane escalation wording, crisis-help resources, operator alerts, and false-positive step-down belong to Stories 3.3, 3.4, 3.5, and 3.7 respectively and should not be fully implemented here. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md]
- The crisis-aware branch must preempt `fast` and `deep` mode logic for the unsafe step, but should not erase those mode values entirely. The mode may still be useful later for audits or eventual recovery flows; it just cannot govern the immediate crisis turn. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md] [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- Privacy and operator boundaries remain strict. Raw crisis text is transient processing input, while durable state should stay bounded to routing metadata, signal category, confidence, timestamps, and crisis-mode flags. Do not widen routine operator exposure to session content in this story. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Reuse the existing retryable failure signal mechanism in `backend/app/ops/signals.py` for crisis-routing failures where possible. Story 3.2 should not introduce a parallel failure-reporting framework just for safety routing. [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py]
- UX guidance is explicit that crisis transitions must feel supportive, calm, and bounded. For this story, that means normal reflective replies must stop once crisis mode is active, but the response seam should stay minimal and routing-oriented so that later stories can layer humane escalation copy without undoing the state model. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]

### Project Structure Notes

- The live codebase does not follow the exact `src/goals/...` structure from the architecture doc; instead it uses the existing repo layout under `backend/app/`. Keep Story 3.2 aligned with the actual working structure rather than trying to “correct” the repo to the aspirational architecture tree during implementation. [Source: /home/erda/Музыка/goals/backend/app] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- The main implementation seam remains:
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/safety/service.py`
  - `backend/app/models.py`
  - `backend/app/ops/signals.py`
- Likely new or changed implementation files:
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/safety/service.py`
  - `backend/app/safety/__init__.py`
  - one or more new crisis-routing helpers such as `backend/app/safety/routing.py` or `backend/app/safety/escalation.py`
  - `backend/app/models.py`
  - a new Alembic migration under `backend/app/alembic/versions/`
- Likely tests to update:
  - `backend/tests/api/routes/test_telegram_session_entry.py`
  - `backend/tests/safety/test_service.py`
  - possibly `backend/tests/api/routes/test_ops_routes.py` if failure visibility expands bounded ops signal behavior
- Avoid implementing Story 3.2 in:
  - `backend/app/bot/`
  - generic utility modules detached from `safety/`
  - memory persistence code such as `backend/app/memory/`
  - operator-facing transcript inspection paths
- There is no generated `project-context.md` in the workspace right now, so implementation should rely on the story file, planning artifacts, and live repo patterns rather than hidden project-level AI rules. [Source: workspace search on 2026-03-13]

### References

- Story source and ACs: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Product requirements and safety constraints: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Architecture boundaries, modular-monolith rules, and ops/privacy posture: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- UX rules for safety transitions and calm escalation tone: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)
- Previous Epic 3 implementation context: [3-1-detection-of-red-flag-signals-in-user-messages.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/3-1-detection-of-red-flag-signals-in-user-messages.md)
- Live request-path routing seam: [session_bootstrap.py](/home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py)
- Existing first-response seam: [first_response.py](/home/erda/Музыка/goals/backend/app/conversation/first_response.py)
- Existing clarification seam: [clarification.py](/home/erda/Музыка/goals/backend/app/conversation/clarification.py)
- Existing closure seam: [closure.py](/home/erda/Музыка/goals/backend/app/conversation/closure.py)
- Existing safety service and signal persistence: [service.py](/home/erda/Музыка/goals/backend/app/safety/service.py)
- Safety package export seam: [__init__.py](/home/erda/Музыка/goals/backend/app/safety/__init__.py)
- Durable models including `TelegramSession` and `SafetySignal`: [models.py](/home/erda/Музыка/goals/backend/app/models.py)
- Existing retryable ops signal pattern: [signals.py](/home/erda/Музыка/goals/backend/app/ops/signals.py)
- Backend dependency declarations: [pyproject.toml](/home/erda/Музыка/goals/backend/pyproject.toml)
- Telegram webhook route tests: [test_telegram_session_entry.py](/home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py)
- Safety-domain tests: [test_service.py](/home/erda/Музыка/goals/backend/tests/safety/test_service.py)
- Ops endpoint constraints: [api.py](/home/erda/Музыка/goals/backend/app/ops/api.py)
- Official FastAPI Background Tasks docs: https://fastapi.tiangolo.com/tutorial/background-tasks/
- Official SQLModel FastAPI session dependency docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Official Pydantic Settings docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Official python-telegram-bot stable docs: https://docs.python-telegram-bot.org/en/stable/

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-discovered from `/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog story in order: `3-2-switching-from-normal-flow-to-crisis-aware-escalation-flow`.
- Loaded full workflow config from `_bmad/bmm/workflows/4-implementation/create-story/workflow.yaml` and executed it under `_bmad/core/tasks/workflow.xml`.
- Core context loaded from `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, the live backend seams in `conversation/`, `safety/`, `ops/`, and `models.py`, plus the completed Story `3.1` implementation guide.
- Confirmed from live code that Story `3.1` currently ends crisis detections with action `safety_hold`; Story `3.2` therefore needs a true reusable crisis-aware branch rather than a placeholder hold response.
- No generated `project-context.md` was found in the workspace.
- No git history was available because `/home/erda/Музыка/goals` is not a git repository root.
- Party-mode was invoked during the `story_requirements` checkpoint and reinforced four guardrails: keep `3.2` centered on routing/state, preserve crisis-mode persistence, keep later messaging/resources out of scope, and make regression coverage explicit for mid-session switching and mode override.
- Web verification was used for current official framework guidance around FastAPI background-task boundaries, SQLModel request-session usage, Pydantic Settings configuration seams, and python-telegram-bot stable documentation posture.
- The workflow references `_bmad/core/tasks/validate-workflow.xml` for checklist validation, but that file does not exist in the current workspace and therefore cannot be executed literally during create-story finalization.
- Implemented bounded crisis routing state directly on `TelegramSession` via `crisis_state`, `crisis_activated_at`, and `crisis_last_routed_at`, plus Alembic migration `cd34ef45ab67_add_crisis_state_to_telegram_session.py`.
- Added a dedicated crisis response seam in `backend/app/safety/escalation.py` and wired `session_bootstrap.py` to use `_compose_crisis_routing_response()` instead of the temporary `safety_hold` branch.
- Updated request-path behavior so crisis classifications and already-active crisis sessions both short-circuit normal reflective builders and return action `crisis_routed`.
- Added explicit `safety_routing_failed` handling that records a retryable ops signal and returns a bounded error response instead of falling back into normal reflection.
- Extended route tests with first-turn crisis routing, same-session midstream switching, mode-priority assertions, routing-failure handling, and crisis-mode persistence checks.
- Added unit coverage for the crisis-routing response seam and fixed an existing detector gap for sexual-violence verb forms by extending direct abuse patterns in `backend/app/safety/service.py`.
- Validation executed against the local Postgres instance on port `5433` because the default `5432` credentials fail in this workspace.
- Validation commands executed:
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run alembic upgrade heads`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest tests/safety/test_service.py tests/safety/test_escalation.py tests/api/routes/test_telegram_session_entry.py -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest tests -q`
  - `uv run ruff check app tests`
  - `uv run mypy app tests`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story `3.2` is intentionally scoped to crisis-flow switching, routing state, and bounded persistence; full humane escalation copy, crisis resources, operator alert fan-out, and false-positive recovery remain in later Epic 3 stories.
- The implementation center of gravity is `backend/app/conversation/session_bootstrap.py` plus the `safety/` domain, not the Telegram adapter and not the reflection text builders.
- Guardrails explicitly prohibit transcript-heavy persistence, normal reflective continuation after crisis routing, and scope creep into Stories `3.3-3.5`.
- Regression coverage must prove first-turn crisis routing, later-turn switching inside the same session, mode override semantics, and routing-failure visibility.
- Recommended completion note for the final story status: `Ultimate context engine analysis completed - comprehensive developer guide created`.
- Replaced the temporary crisis `safety_hold` dead-end with a reusable `crisis_routed` branch that persists crisis state on the session and keeps later turns on the safety-first path until a later story introduces step-down behavior.
- Added a dedicated crisis response seam in `backend/app/safety/escalation.py` so crisis handling no longer reuses normal reflection builders.
- Added bounded crisis metadata to `TelegramSession` and corresponding Alembic migration support so downstream stories can build messaging, resources, and alerts on stable session state.
- Added explicit crisis-routing failure signaling via the existing retryable ops-signal mechanism instead of silently resuming ordinary reflection.
- Added and updated regression tests covering first-turn crisis routing, mid-session switching, mode override semantics, crisis-mode persistence, routing failure handling, and the sensitive-content scenario that previously flowed to closure.
- Full backend validation passed with `pytest`, `ruff`, and `mypy` on the `5433` Postgres test instance.

### File List

- _bmad-output/implementation-artifacts/sprint-status.yaml
- _bmad-output/implementation-artifacts/3-2-switching-from-normal-flow-to-crisis-aware-escalation-flow.md
- backend/app/alembic/versions/cd34ef45ab67_add_crisis_state_to_telegram_session.py
- backend/app/conversation/session_bootstrap.py
- backend/app/models.py
- backend/app/safety/__init__.py
- backend/app/safety/escalation.py
- backend/app/safety/service.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/safety/test_escalation.py

## Change Log

- 2026-03-13: Created Story 3.2 implementation guide with routing-focused acceptance criteria, task decomposition, crisis-state guardrails, live repo references, official framework guidance, and regression expectations aligned to the current safety implementation.
- 2026-03-13: Implemented crisis-aware routing state, dedicated crisis response handling, failure signaling, migration support, and regression coverage for first-turn and mid-session crisis switching.
