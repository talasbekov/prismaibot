# Story 3.1: Обнаружение red-flag сигналов в пользовательских сообщениях

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь в потенциально кризисном состоянии,
I want чтобы продукт распознавал признаки self-harm risk, dangerous abuse и других высокорисковых состояний,
so that обычный reflective flow не продолжался там, где нужен более безопасный сценарий.

## Acceptance Criteria

1. When a user sends a new message in an active or newly started session, the system evaluates that text for red-flag signals before continuing the normal reflective flow, and this check happens in the main conversational path without a separate manual trigger. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-31-Обнаружение-red-flag-сигналов-в-пользовательских-сообщениях] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
2. When a message contains explicit or sufficiently strong signs of crisis, self-harm ideation, dangerous abuse, or comparable safety risk, the message is marked as requiring crisis-aware handling and normal reflective continuation is not treated as the safe default path. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-31-Обнаружение-red-flag-сигналов-в-пользовательских-сообщениях] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
3. When a message is emotionally intense but not necessarily crisis-level, the product distinguishes normal overload from more dangerous safety patterns and does not escalate every heavy message as crisis by default. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-31-Обнаружение-red-flag-сигналов-в-пользовательских-сообщениях] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
4. When the system detects an uncertain or borderline signal, the detection result remains usable for more cautious next-step handling and the product is not required to behave as if a severe crisis is already confirmed. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-31-Обнаружение-red-flag-сигналов-в-пользовательских-сообщениях] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
5. When a user sends multiple messages in one session, red-flag detection is applied to new incoming messages throughout the conversation, and a previously safe session can be moved into the crisis-aware path when a later message introduces a new risk signal. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-31-Обнаружение-red-flag-сигналов-в-пользовательских-сообщениях] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]
6. When the detection step errors or cannot complete reliably, the failure becomes observable to the system and the product must not silently assume full safety if critical detection failed. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-31-Обнаружение-red-flag-сигналов-в-пользовательских-сообщениях] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

## Tasks / Subtasks

- [x] Add a dedicated safety-evaluation seam on every inbound user message before normal reflection continues (AC: 1, 5, 6)
  - [x] Introduce a `safety/` service entry point that accepts the normalized inbound message plus minimal session context and returns a bounded detection result.
  - [x] Call that safety seam from `conversation/session_bootstrap.py` on first turn and subsequent turns before choosing first-trust, clarification, or closure behavior.
  - [x] Keep the detection payload transcript-minimal and scoped to the current incoming message plus only the context needed for safety classification.
- [x] Define deterministic MVP red-flag classification behavior for clear, borderline, and non-crisis cases (AC: 2, 3, 4)
  - [x] Start with a curated rule/phrase policy for explicit self-harm, suicide, dangerous abuse, or acute danger signals instead of a vague “AI magic” detector.
  - [x] Produce classification levels that preserve ambiguity where needed, for example `safe`, `borderline`, and `crisis`, rather than a binary only.
  - [x] Ensure emotionally heavy but ordinary conflict language does not trip crisis routing by default.
- [x] Persist enough safety signal state for later stories without leaking sensitive content into routine ops paths (AC: 2, 4, 5, 6)
  - [x] Extend the live session state and/or add a dedicated bounded safety record so later stories can route to escalation, alerts, and false-positive step-down without relying on raw transcript reuse.
  - [x] Store only signal-level metadata such as classification, trigger category, confidence bucket, and timestamps, not full crisis text bodies.
  - [x] Keep the schema aligned with the current SQLModel/Alembic setup and the architecture’s privacy boundary.
- [x] Add observable failure and review-safe signal handling for detection failures (AC: 6)
  - [x] Reuse the existing ops signal pattern where possible so a failed safety check becomes operator-visible in a bounded, retry-safe way.
  - [x] Ensure failure handling does not silently drop the signal and then continue the standard reflective path as if the safety check succeeded.
  - [x] Keep user-facing fallback language calm and non-technical if safety evaluation fails mid-request.
- [x] Add regression coverage for first-turn, later-turn, borderline, and failure paths (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add route/integration tests around `/api/v1/telegram/webhook` proving detection runs before standard flow selection on first and later turns.
  - [x] Add safety-domain unit tests for explicit crisis phrases, dangerous-abuse phrasing, emotionally intense but non-crisis messages, and borderline ambiguity.
  - [x] Add tests showing a later message can flip an existing active session into a crisis-classified state.
  - [x] Add tests showing safety-evaluation failure creates an observable bounded signal and suppresses silent “all safe” behavior.
  - [x] Run the normal backend quality bar: `pytest`, `ruff`, and `mypy`.

## Dev Notes

- The live request-path seam is `backend/app/conversation/session_bootstrap.py`. Every inbound Telegram text flows through `_handle_message()`, which currently decides between first response, clarification, and closure with no safety gate in front of those branches. Story 3.1 should insert detection there before normal flow selection. [Source: /home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py]
- The repository already has a reserved `backend/app/safety/` module, but it contains no implementation yet. This story should make `safety/` the owner of red-flag detection behavior rather than scattering keyword checks through `conversation/`, `bot/`, or route handlers. [Source: /home/erda/Музыка/goals/backend/app/safety/__init__.py] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Story 3.1 is only the detection layer. It should not try to fully implement the escalation copy, crisis resources, or operator-alert UX from Stories 3.2-3.7. It does need to produce a stable signal and state shape that those stories can build on. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md]
- Privacy constraints are strict: raw transcripts are transient processing input, operators do not get routine transcript access, and sensitive-content logging must stay minimized. That means the safety detector may inspect message text in-process, but durable artifacts and logs must stay signal-level and sanitized. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- The current codebase already has an observable-failure pattern in `ops/signals.py` and `SummaryGenerationSignal`. Story 3.1 should follow that precedent for safety-check failure visibility instead of inventing an unrelated error side channel. [Source: /home/erda/Музыка/goals/backend/app/ops/signals.py] [Source: /home/erda/Музыка/goals/backend/app/models.py]
- UX guidance is explicit that safety transitions must feel supportive rather than cold, legalistic, or abrupt. Even though full escalation copy lands in later stories, Story 3.1 should avoid returning a normal reflective reply when the detector says `crisis`, and it should preserve an ambiguity-aware result when the signal is only borderline. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]

## Developer Context

### Technical Requirements

- Evaluate each new inbound message for safety risk before first-trust, clarification, or closure logic continues. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-31-Обнаружение-red-flag-сигналов-в-пользовательских-сообщениях]
- Distinguish at least three practical states for MVP behavior: no crisis signal, borderline concern, and crisis-level concern. Binary-only classification is too coarse for the documented UX and product requirements. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md]
- Keep red-flag evaluation cheap and deterministic enough for the main latency-sensitive Telegram path. This story should not introduce a heavy separate moderation platform or transcript-wide batch pipeline. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- Detection failure must be observable and must not silently degrade into “safe”. If the detector cannot run or cannot classify reliably, that state has to remain explicit for downstream handling. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-31-Обнаружение-red-flag-сигналов-в-пользовательских-сообщениях]
- Keep data retention bounded. Signal metadata may be persisted for routing and ops, but raw crisis wording should not become routine durable memory or routine ops payload content. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]

### Architecture Compliance

- `conversation/` remains the orchestration layer for live session progression, but `safety/` should own detection logic and signal shaping. Do not embed the classification rules directly inside `session_bootstrap.py`. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- `bot/` stays a Telegram transport boundary. Do not solve Story 3.1 in webhook adapters or Telegram-specific payload parsing. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md]
- `ops/` should receive bounded operational signals, not full crisis transcript content. Any new persistence or alertable failure object must preserve the current transcript-free operator posture. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md] [Source: /home/erda/Музыка/goals/backend/app/ops/api.py]
- Stay within the current modular-monolith repo shape. The live codebase already has `conversation/`, `memory/`, `ops/`, and a placeholder `safety/` package; no separate service or worker is justified for this story. [Source: /home/erda/Музыка/goals/backend/app]

### Library / Framework Requirements

- Stay on the current backend stack declared in `backend/pyproject.toml`: FastAPI, SQLModel, Alembic, `pydantic-settings`, PostgreSQL via `psycopg`, and `python-telegram-bot` `>=21.6,<22.0`. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- FastAPI’s current official docs continue to position `BackgroundTasks` as post-response work. Story 3.1 should not rely on deferred background evaluation for the primary safety classification, because the routing decision must happen before the normal reflective reply is chosen. Source: https://fastapi.tiangolo.com/tutorial/background-tasks/
- SQLModel’s official FastAPI session-dependency guidance still fits the current request-scoped DB access pattern. Keep safety classification reads/writes inside the existing request transaction shape rather than inventing a parallel persistence flow. Source: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Keep any detector thresholds, phrase lists, or feature flags in the existing settings/config seam rather than scattering hard-coded constants through route handlers. Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- The upstream `python-telegram-bot` docs now document the current stable API line separately from the repo’s pinned `<22` range. Avoid adopting v22-specific assumptions while touching ingress-related code; keep Telegram handling changes compatible with the existing pin. Source: https://docs.python-telegram-bot.org/en/stable/

### File Structure Requirements

- Primary implementation files are likely:
  - `backend/app/conversation/session_bootstrap.py`
  - `backend/app/safety/__init__.py`
  - one or more new files under `backend/app/safety/` such as `service.py`, `schemas.py`, or `policy.py`
  - `backend/app/models.py` if bounded safety signal persistence is added
  - `backend/app/ops/signals.py` if safety-check failures reuse the ops-signal pattern
- Primary test files are likely:
  - `backend/tests/api/routes/test_telegram_session_entry.py`
  - new safety-domain tests under `backend/tests/` such as `tests/safety/test_service.py`
  - `backend/tests/api/routes/test_foundation_runtime.py` if module wiring or route exposure changes
- Avoid solving this story in:
  - `backend/app/bot/`
  - generic global helper modules detached from `safety/`
  - raw transcript archiving or operator transcript-view features

### Testing Requirements

- Add tests proving red-flag detection runs before the first-trust response is selected on the first user turn.
- Add tests proving a later message in an already active session can trigger a crisis classification.
- Add tests for emotionally intense but non-crisis messages so the detector does not over-escalate normal conflict language.
- Add tests for borderline cases where the result is cautious/bounded rather than hard-crisis by default.
- Add tests for detector failure that create an observable signal and avoid silently treating the session as definitely safe.
- Run the normal backend quality bar: `pytest`, `ruff`, and `mypy`.

### Git Intelligence Summary

- No git history was available from `/home/erda/Музыка/goals`, so there was no commit-level pattern analysis for this story.

### Library / Framework Latest Information

- FastAPI’s official guidance still supports post-response background work, which reinforces that the safety detector itself belongs on the request path while any non-critical follow-up work can stay async. Source: https://fastapi.tiangolo.com/tutorial/background-tasks/
- SQLModel’s current FastAPI tutorial still centers on dependency-injected request sessions, which matches the repo’s existing session-scoped persistence approach in Telegram webhook handling. Source: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Pydantic Settings continues to document a central env-backed settings seam. Use that seam for detector policy configuration or toggles rather than distributing policy constants through multiple modules. Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- The current upstream `python-telegram-bot` stable docs are ahead of this repo’s pinned `<22` dependency line, so ingress changes should remain pinned-version compatible instead of copying newer examples blindly. Source: https://docs.python-telegram-bot.org/en/stable/

### Project Structure Notes

- The live repo is slightly ahead of the planning docs in one useful way: `backend/app/safety/` already exists as a reserved domain package, so Story 3.1 can land cleanly there without inventing a new boundary.
- The main structural risk is putting crisis detection directly into conversation text-generation helpers. Keep classification policy in `safety/` and let `conversation/` consume a typed detection result.
- A second structural risk is over-persisting sensitive content. Prefer bounded safety state and ops-visible signal metadata over transcript-heavy records.

### References

- Story source and acceptance criteria: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Product requirements and safety constraints: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Architecture boundaries, ops/privacy posture, and modular-monolith rules: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- UX rules for safety transitions and calm escalation tone: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)
- Live conversation ingress/orchestration seam: [session_bootstrap.py](/home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py)
- Existing first-response seam: [first_response.py](/home/erda/Музыка/goals/backend/app/conversation/first_response.py)
- Existing clarification seam: [clarification.py](/home/erda/Музыка/goals/backend/app/conversation/clarification.py)
- Reserved safety domain package: [__init__.py](/home/erda/Музыка/goals/backend/app/safety/__init__.py)
- Existing ops signal pattern: [signals.py](/home/erda/Музыка/goals/backend/app/ops/signals.py)
- Existing durable models: [models.py](/home/erda/Музыка/goals/backend/app/models.py)
- Telegram webhook integration tests: [test_telegram_session_entry.py](/home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py)
- Ops route tests: [test_ops_routes.py](/home/erda/Музыка/goals/backend/tests/api/routes/test_ops_routes.py)
- Runtime/module wiring tests: [test_foundation_runtime.py](/home/erda/Музыка/goals/backend/tests/api/routes/test_foundation_runtime.py)
- Official FastAPI Background Tasks docs: https://fastapi.tiangolo.com/tutorial/background-tasks/
- Official SQLModel FastAPI session dependency docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/
- Official Pydantic Settings docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Official python-telegram-bot stable docs: https://docs.python-telegram-bot.org/en/stable/

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-discovered from `/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog story in order: `3-1-detection-of-red-flag-signals-in-user-messages`.
- Core context loaded from `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, the live backend seams in `conversation/`, `ops/`, and `models.py`, and the current dependency declarations in `backend/pyproject.toml`.
- No previous story file exists in Epic 3 yet because this is the first story in the epic.
- No `project-context.md` was found in the workspace.
- No git history was available because `/home/erda/Музыка/goals` is not a git repository root.
- The workflow step that references `_bmad/core/tasks/validate-workflow.xml` could not be executed literally because that file does not exist in the workspace.
- Web verification was used only for current official framework guidance around FastAPI background tasks, SQLModel request-session usage, Pydantic Settings, and python-telegram-bot documentation posture.
- Added failing tests first in `backend/tests/safety/test_service.py` and `backend/tests/api/routes/test_telegram_session_entry.py` for crisis detection, borderline handling, later-turn escalation, and safety-evaluation failure visibility.
- Implemented the safety seam in `backend/app/safety/service.py` and exported it through `backend/app/safety/__init__.py`.
- Extended `TelegramSession` and added `SafetySignal` in `backend/app/models.py`, plus Alembic migration `ab12cd34ef56_add_safety_signal_and_session_safety_state.py`.
- Updated `backend/app/conversation/session_bootstrap.py` to evaluate every inbound message before normal reflection, return `safety_hold` for crisis detections, and emit a bounded failure response if safety evaluation fails.
- Generalized retryable ops signaling in `backend/app/ops/signals.py` so safety-evaluation failures can create operator-visible bounded signals without adding a second signal mechanism.
- Validation used the isolated Postgres instance on port `5433` because the default local `5432` instance rejects this repo’s credentials.
- Validation commands executed:
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run alembic upgrade heads`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest tests/safety/test_service.py tests/api/routes/test_telegram_session_entry.py -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 uv run pytest tests -q`
  - `POSTGRES_SERVER=localhost POSTGRES_PORT=5433 ENABLE_LEGACY_WEB_ROUTES=true uv run pytest tests -q`
  - `uv run ruff check app tests`
  - `uv run mypy app tests`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story 3.1 is intentionally scoped as the detection layer only; escalation messaging, resources, alerts, and false-positive recovery remain in Stories 3.2-3.7.
- The implementation focus is a request-path safety detector, bounded crisis/borderline classification, transcript-minimal persistence, and observable failure handling.
- Guardrails explicitly prohibit transcript-heavy ops payloads, webhook-layer safety logic, and overengineered moderation infrastructure for MVP.
- Added a deterministic rule-based detector that classifies inbound messages as `safe`, `borderline`, or `crisis`, with explicit support for self-harm and dangerous-abuse patterns.
- Added bounded session-level safety state plus a durable `SafetySignal` record so later stories can route escalation and alerts without depending on raw transcript retention.
- Blocked the normal reflective path for crisis detections with a dedicated `safety_hold` response and preserved bounded signal-only behavior for borderline detections.
- Added explicit operator-visible handling for detector failures via the existing retryable signal mechanism, with a calm user-facing `safety_check_error` fallback.
- Full validation passed on the isolated database: targeted safety tests, full pytest, legacy-route pytest, `ruff`, and `mypy`.

### File List

- _bmad-output/implementation-artifacts/3-1-detection-of-red-flag-signals-in-user-messages.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/alembic/versions/ab12cd34ef56_add_safety_signal_and_session_safety_state.py
- backend/app/alembic/versions/bc23de45fg67_add_unique_constraint_to_safety_signal.py
- backend/app/conversation/session_bootstrap.py
- backend/app/models.py
- backend/app/ops/signals.py
- backend/app/safety/__init__.py
- backend/app/safety/service.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/conftest.py
- backend/tests/safety/test_service.py

## Change Log

- 2026-03-13: Created Story 3.1 implementation guide with acceptance criteria, task decomposition, architecture guardrails, privacy constraints, latest framework guidance, and backend test expectations aligned to the live repo.
- 2026-03-13: Implemented request-path safety detection, bounded safety persistence, crisis-hold routing, retryable safety-failure signaling, and regression coverage for crisis/borderline/later-turn detection behavior.
