# Story 1.4: Первый trust-making ответ с отражением ситуации

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь в эмоционально сложной ситуации,
I want получить первый ответ, который показывает, что бот меня понял, прежде чем начнет советовать или направлять,
so that я чувствую доверие к разговору и готов продолжать сессию.

## Acceptance Criteria

1. When the system produces the first meaningful response after the user describes a situation, the message begins with a short human-feeling reflection and does not begin with advice, diagnosis, moral judgment, or a therapy-like exercise. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-14-Первый-trust-making-ответ-с-отражением-ситуации]
2. The first substantive reply reflects at least one factual or situational element and one emotional or tension element from the user message, using calm, grounded, nonjudgmental phrasing. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-14-Первый-trust-making-ответ-с-отражением-ситуации]
3. The response remains readable and chunked for Telegram consumption and does not degrade into a long wall of text. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-14-Первый-trust-making-ответ-с-отражением-ситуации]
4. If system confidence is low or the input is too chaotic for a strong interpretation, the first reply uses tentative phrasing and adds exactly one clear follow-up question instead of an overconfident interpretation. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-14-Первый-trust-making-ответ-с-отражением-ситуации]
5. In the normal reflective path, with no crisis trigger present, the first meaningful response preserves the reflective flow and creates a soft transition into the next clarification step rather than closing the conversation early. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-14-Первый-trust-making-ответ-с-отражением-ситуации]
6. The generated first response avoids doctor-like, diagnostic, and treatment-oriented language so the product remains a non-medical self-reflection tool. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-14-Первый-trust-making-ответ-с-отражением-ситуации]

## Tasks / Subtasks

- [x] Introduce a dedicated first-response composition path on top of the Telegram session-entry flow (AC: 1, 2, 5, 6)
  - [x] Create or extract a conversation-layer function/service that accepts the first user message plus session context and returns a structured first-response payload.
  - [x] Keep Telegram transport thin in `backend/app/bot/api.py`; do not hardcode trust-making response logic directly inside the route handler.
  - [x] Reuse the same early-session entry path that Story 1.2 and Story 1.3 describe instead of building a second parallel "first reply" flow.
- [x] Implement reflection-first response rules for the first substantive reply (AC: 1, 2, 5, 6)
  - [x] Ensure the reply opens with a short reflective sentence before any guidance or clarifying question.
  - [x] Require extraction of one concrete situational element and one emotional or tension element from the user input.
  - [x] Keep tone nonjudgmental, calm, and non-medical; do not allow diagnosis-like labels, treatment framing, or moralizing language.
- [x] Add low-confidence fallback behavior with one follow-up question (AC: 4, 5)
  - [x] Detect when the first input is too vague, fragmented, or contradictory for a strong interpretation.
  - [x] In that case, produce tentative phrasing and exactly one focused follow-up question.
  - [x] Do not pretend to understand more than the system can justify from the message.
- [x] Make the reply Telegram-readable and consistent with the trust-first UX (AC: 3, 5)
  - [x] Split the first response into compact chunks or message sections suitable for mobile Telegram reading.
  - [x] Preserve or reuse typing-indicator behavior before delivery.
  - [x] Avoid button-heavy branching at this point; the first meaningful reply is primarily a text interaction.
- [x] Verify behavior and guard against regressions in the current starter-derived backend (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add tests for a normal conflict message that yields reflection-first output.
  - [x] Add tests for a low-confidence message that yields tentative phrasing plus one follow-up question.
  - [x] Add tests that assert no advice-first opening, no doctor-like language markers, and no wall-of-text formatting regression.
  - [x] Keep coverage centered on the `/api/v1/telegram/webhook` path and the conversation module it delegates to.

## Dev Notes

- This story is the trust-making core of Epic 1. UX explicitly says the first meaningful response is the most important interaction in the product and determines whether the user keeps talking. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#Core-User-Experience]
- The product promise here is not "answer quickly with advice". It is "reflect and organize the situation before steering". A rushed advice-first implementation fails the product even if the webhook technically works. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Executive-Summary]
- Architecture treats first-response quality as a system responsibility: context assembly, safety checks, and latency all shape whether this trust-making moment succeeds. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Context-Analysis]
- Story 1.4 should stay on the normal reflective path only. Do not implement crisis escalation here beyond leaving room for Story 3.x safety routing to short-circuit later.
- Story 1.4 should not close the whole session. The output should hand off naturally to the next clarification step that Story 1.5 will deepen.
- The current local codebase still contains only a placeholder Telegram webhook and does not yet contain the `session_bootstrap.py` / `TelegramSession` implementation described in Story 1.2 and assumed by Story 1.3. Treat that as a dependency gap, not as permission to invent a disconnected second path.

### Project Structure Notes

- Current Telegram ingress lives in [`backend/app/bot/api.py`](/home/erda/Музыка/goals/backend/app/bot/api.py). It is still a stub that only returns `accepted` / `ignored`, so this story should extend the same route path rather than introducing a second Telegram entrypoint.
- Product-first routing is already centered in [`backend/app/api/main.py`](/home/erda/Музыка/goals/backend/app/api/main.py). Keep new work on the `telegram` route tree, not in legacy `login.py`, `users.py`, or `items.py`.
- The intended early-session orchestration module from Story 1.2, [`backend/app/conversation/session_bootstrap.py`](/home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py), does not exist yet in the live repo. If Story 1.4 needs conversation composition now, add it under `backend/app/conversation/` in a way that can become the shared home for Story 1.2/1.3/1.4 logic rather than scattering orchestration across transport code.
- Current persisted models in [`backend/app/models.py`](/home/erda/Музыка/goals/backend/app/models.py) are still starter-template `User` / `Item` models. If this story needs session-aware context, prefer a product-aligned session model introduced through the same seam as Story 1.2 rather than bolting trust-response logic onto template entities.
- Current Telegram route tests live in [`backend/tests/api/routes/test_telegram_session_entry.py`](/home/erda/Музыка/goals/backend/tests/api/routes/test_telegram_session_entry.py). Extend that suite or add adjacent Telegram/conversation tests rather than hiding this behavior inside generic legacy route coverage.

### References

- Story source and acceptance criteria: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Immediate prior story context: [1-3-fast-deep-reflective-mode.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-3-fast-deep-reflective-mode.md)
- Session-entry baseline and dependency gap: [1-2-telegram-session-entry.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-2-telegram-session-entry.md)
- Product promise, trust surface, and non-medical framing: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Architecture guardrails and runtime boundaries: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- UX rules for trust-making response, chunking, tone, and typing feedback: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)

## Developer Context

### Technical Requirements

- The first meaningful reply must open with reflection, not advice. UX explicitly requires a short human reflection first, then structured interpretation, then guidance. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#Core-User-Experience]
- The reply must capture at least one concrete situation detail and one emotional/tension detail from the user's message. Generic empathy text without message grounding does not satisfy Story 1.4. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-14-Первый-trust-making-ответ-с-отражением-ситуации]
- Telegram readability is part of correctness. Long dense output is a UX and accessibility failure in this product. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#Responsive-Design--Accessibility]
- The first-response path stays inside the latency-sensitive request path. Do not add summary generation, memory enrichment, payment checks, or other nonessential work before the first substantive reply. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Context-Analysis]
- Product framing remains non-medical. Avoid diagnosis-like wording, clinical labels, or treatment language in prompts, templates, tests, and generated text rules. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Domain-Specific-Requirements]

### Architecture Compliance

- Keep Telegram transport concerns in `bot/` and first-response composition in `conversation/`; do not let the route handler become the product brain. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Structure--Boundaries]
- Use the current product-first router composition and extend it, rather than reopening legacy CRUD routes as the center of the implementation.
- Treat low-confidence interpretation as an explicit branch of the reflective flow, not as an error path.
- Preserve a clean seam for later safety short-circuiting. Story 1.4 implements normal-path trust creation; Story 3.x will own crisis-path interruption.
- If Story 1.2 and Story 1.3 infrastructure is still missing in code, implement this story through the same emerging conversation-entry seam so earlier and later stories can converge on one path.

### Library / Framework Requirements

- Use the existing backend stack in [`backend/pyproject.toml`](/home/erda/Музыка/goals/backend/pyproject.toml): FastAPI, SQLModel, Alembic, `pydantic-settings`, and `python-telegram-bot`.
- Keep FastAPI router composition and request handling idiomatic; use the existing `APIRouter` pattern and avoid custom framework abstractions. [Official docs: https://fastapi.tiangolo.com/]
- Keep environment-backed configuration in the existing settings system rather than hardcoded response-tuning constants spread across modules. [Official docs: https://docs.pydantic.dev/latest/]
- Telegram-specific behavior should remain compatible with the repo’s current `python-telegram-bot<22.0,>=21.6` constraint. Stable official docs now document v22 APIs; unless dependency policy changes first, avoid adopting v22-only patterns in this story. [Inference from official docs and repo pins]
- If delivery semantics or chat actions need to align with Telegram capabilities, use the official library/Bot API documentation as the source of truth rather than ad hoc examples. [Official docs: https://docs.python-telegram-bot.org/en/stable/]

### File Structure Requirements

- Primary touch points should stay inside:
  - `backend/app/bot/api.py`
  - `backend/app/conversation/`
  - `backend/app/models.py` or a product-aligned session model module if Story 1.2 scope is pulled in
  - `backend/tests/api/routes/test_telegram_session_entry.py`
  - adjacent conversation-focused tests if the composition logic is split out
- Avoid putting trust-response logic into legacy web-auth modules, frontend code, or generic utility dumping grounds.
- If you create prompt/formatter helpers for the first reply, keep them under `backend/app/conversation/` so later reflective-flow stories can reuse them instead of reimplementing them.
- If new persistence is required because Story 1.2 never landed, keep it minimal and aligned with the session-entry seam rather than introducing broad memory/profile storage.

### Testing Requirements

- Add or update tests for:
  - a normal first message that yields reflection-first output
  - a message with identifiable facts and emotion/tension that are both reflected back
  - a low-confidence message that yields tentative phrasing plus one follow-up question
  - Telegram-readable chunking / no wall-of-text regression
  - a guard against advice-first or doctor-like opening language
- Preserve typing-indicator or equivalent response-signal expectations if Story 1.2 behavior is implemented on the same path.
- Run the backend validation toolchain from [`backend/pyproject.toml`](/home/erda/Музыка/goals/backend/pyproject.toml): `pytest`, `ruff`, and `mypy`.
- Keep regression coverage focused on the Telegram path and the conversation module it delegates to.

### Previous Story Intelligence

- Story 1.3 already defined an important constraint: mode selection is optional support behavior only and must not dominate the first-run interaction. Story 1.4 must keep the trust-making reply stronger than any mode UI or setup friction. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-3-fast-deep-reflective-mode.md]
- Story 1.3 also assumed a session-aware conversation seam (`session_bootstrap.py`, persisted session context, and route-level Telegram tests). The live repo has not caught up to that plan yet. Build toward that seam rather than away from it.
- Story 1.2 established the intended pattern of typing feedback, free-text-first progression, and minimal session bootstrap. Reuse those design decisions if you need to land the missing infrastructure while implementing Story 1.4. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-2-telegram-session-entry.md]
- Current repo reality matters: `backend/app/bot/api.py` is still a placeholder, `backend/app/conversation/` contains no implementation module, and `backend/app/models.py` is still starter-template state. Account for that gap explicitly during implementation.

### Git Intelligence Summary

- No usable local git history was available at `/home/erda/Музыка/goals`, so there are no recent commits to mine for patterns or prior fixes.

### Project Context Reference

- No `project-context.md` was found in the workspace. Use `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, Stories 1.2 and 1.3, and the live backend codebase as the authoritative context set.

### Library / Framework Latest Information

- FastAPI’s official documentation continues to center router-based application composition and dependency-driven request handling. Story 1.4 should implement first-response behavior by composing on the existing route/service flow, not by introducing a parallel application layer. [Official docs: https://fastapi.tiangolo.com/]
- Pydantic’s current documentation continues to position `pydantic-settings` as the standard environment-backed configuration layer. If trust-response tuning needs settings, keep them centralized there rather than scattered as module globals. [Official docs: https://docs.pydantic.dev/latest/]
- `python-telegram-bot` stable docs now reflect the v22 line, while this repo currently pins `<22.0`. For this story, prefer 21.x-compatible usage and only upgrade to 22.x through an explicit dependency change, because silent API drift here would create avoidable implementation churn. [Inference from official docs and repo pins]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-discovered from `_bmad-output/implementation-artifacts/sprint-status.yaml` as the first `backlog` story in order: `1-4-first-trust-making-response-with-situation-reflection`.
- Source context loaded from `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, and prior implementation stories `1-2` and `1-3`.
- No `project-context.md` was found in the workspace.
- No usable git history was available because `/home/erda/Музыка/goals` is not a git repository.
- Live backend inspection showed a product-first router composition is present, but Telegram session handling is still a placeholder and the conversation/session modules assumed by prior stories are not yet implemented.
- Implemented dedicated first-response composition in `app/conversation/first_response.py` and routed first-turn handling through that seam from `session_bootstrap.py`.
- Used a temporary local Postgres container on port `5433` to run migrations and tests because the host's `localhost:5432` belongs to another workspace and rejects this repo's credentials.
- Validation runs completed with:
  - `POSTGRES_PORT=5433 uv run pytest tests/api/routes/test_telegram_session_entry.py tests/conversation/test_first_response.py`
  - `POSTGRES_PORT=5433 uv run ruff check app tests`
  - `POSTGRES_PORT=5433 uv run mypy app tests`
  - `POSTGRES_PORT=5433 ENABLE_LEGACY_WEB_ROUTES=true uv run pytest`

### Completion Notes List

> **Note:** The entries below are from the story-creation analysis phase, not from implementation. Story 1.4 status is `ready-for-dev` — no code has been written for this story yet.

- [Story creation] Context analysis completed — comprehensive developer guide created.
- [Story creation] Story 1.4 is scoped as the first trust-making reflective reply on the normal path, not as crisis handling, summary generation, or session closure.
- [Story creation] Dev guidance explicitly reconciles planning artifacts with current repo reality so implementation can converge earlier stories instead of creating a second divergent path.
- [Story creation] Guardrails emphasize reflection-first output, message-grounded phrasing, one-question low-confidence fallback, Telegram-readable chunking, and non-medical language.
- [Story creation] Implementation should prefer a reusable `conversation/` seam so Stories 1.2, 1.3, 1.4, and 1.5 can share one early-session flow.
- [Implementation 2026-03-11] Added a dedicated trust-response composer that produces chunked, reflection-first output for the first substantive Telegram reply.
- [Implementation 2026-03-11] Added a low-confidence branch with tentative wording and exactly one follow-up question instead of overconfident interpretation.
- [Implementation 2026-03-11] Preserved the existing Telegram route seam and typing signals while keeping composition logic in `conversation/`.
- [Implementation 2026-03-11] Added route and unit tests covering reflection-first output, low-confidence fallback, chunking, and non-medical regression guards.
- [Implementation 2026-03-11] Full backend regression suite passed against temporary Postgres with `ENABLE_LEGACY_WEB_ROUTES=true`; targeted Story 1.4 checks passed without that flag.
- [Code review #3 2026-03-11] Fixed 7/13 emotion grammar errors (тебя→тебе for short predicative adjectives), removed fabricated "снова" from situation templates, added negation detection (`_is_negated`) so "не обидно" no longer returns "обидно", removed over-broad `not has_situation` from low-confidence condition, changed `FirstTrustResponse.messages` from `list[str]` to `tuple[str, ...]`, made route tests behavioural (survive LLM swap), expanded unit tests to 12 cases covering negation/grammar/boundary/immutability, added `OPENAI_API_KEY` to Settings.

### File List

- _bmad-output/implementation-artifacts/1-4-first-trust-making-response-with-situation-reflection.md
- backend/app/conversation/first_response.py
- backend/app/conversation/session_bootstrap.py
- backend/app/core/config.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/conversation/test_first_response.py

### Change Log

- 2026-03-11: Implemented trust-making first-response composition for Telegram first-turn messages, including low-confidence fallback, chunked reply delivery, and regression coverage.
