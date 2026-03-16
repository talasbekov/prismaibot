# Story 1.5: Clarification и разбор фактов, эмоций и интерпретаций

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a пользователь, который пытается разобраться в конфликте или внутреннем напряжении,
I want чтобы бот помог мне отделить факты, эмоции и мои интерпретации через уточняющие вопросы и структурированный разбор,
so that ситуация становится яснее и менее хаотичной.

## Acceptance Criteria

1. After the first trust-making response, the clarification phase asks a limited number of relevant follow-up questions that reduce ambiguity without turning the interaction into an interrogation or rigid questionnaire. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-15-Clarification-и-разбор-фактов-эмоций-и-интерпретаций]
2. When user input mixes facts, emotions, assumptions, and possible distortions, the system helps separate factual elements, emotional reactions, and interpretation layers in a normal conversational format rather than a dry analytic dump. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-15-Clarification-и-разбор-фактов-эмоций-и-интерпретаций]
3. As the user adds more detail during an active session, the system updates its current understanding of the situation and keeps later follow-up prompts and interim reflections consistent with already collected context. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-15-Clarification-и-разбор-фактов-эмоций-и-интерпретаций]
4. In `fast` mode, clarification stays intentionally bounded and optimized for reaching useful clarity quickly, without dragging the session deeper than the selected mode implies. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-15-Clarification-и-разбор-фактов-эмоций-и-интерпретаций]
5. In `deep` mode, the system may use a richer reflective path with additional clarification and interpretation support, while keeping the depth tied to the user’s real context rather than a template script. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-15-Clarification-и-разбор-фактов-эмоций-и-интерпретаций]
6. If the user is vague, contradictory, or emotionally overloaded and the bot cannot reliably continue the breakdown, it responds with a gentle next question or interim reflection instead of abrupt conclusions, blame, or loss of conversational coherence. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-15-Clarification-и-разбор-фактов-эмоций-и-интерпретаций]
7. If the user shifts into a topic outside the product’s self-reflection boundary, the bot gently reasserts the product boundary and offers to return to the user’s situation instead of switching into a general-purpose assistant mode. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-15-Clarification-и-разбор-фактов-эмоций-и-интерпретаций]
8. If work, business, money, or technology is part of the user’s actual life situation, the bot continues the reflective flow through that context rather than rejecting the message based only on keywords. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-15-Clarification-и-разбор-фактов-эмоций-и-интерпретаций]

## Tasks / Subtasks

- [x] Introduce a clarification-stage conversation component on top of the existing early-session seam (AC: 1, 2, 3, 6)
  - [x] Extend the conversation layer so it can generate one clarification turn at a time from the current session state and the latest user message.
  - [x] Encode a clear distinction between factual details, emotional signals, and interpretation hypotheses so the bot can reflect them separately without sounding robotic.
  - [x] Keep the transport route thin; do not embed clarification policy directly inside the Telegram webhook handler.
- [x] Add bounded clarification behavior that respects reflective mode (AC: 1, 3, 4, 5)
  - [x] Use the current session mode when deciding whether to ask a narrower `fast` follow-up or a richer `deep` follow-up.
  - [x] Keep the number of active clarification prompts low and avoid stacked multi-question turns.
  - [x] Ensure later turns remain consistent with previously collected context instead of re-asking the same thing in different words.
- [x] Implement gentle low-confidence and overload handling (AC: 2, 3, 6)
  - [x] Detect when the system lacks enough confidence to cleanly separate facts, emotions, and interpretations.
  - [x] In that branch, produce tentative wording plus one focused next move rather than a confident but brittle breakdown.
  - [x] Preserve conversational coherence for fragmented or emotionally overloaded user replies.
- [x] Enforce product-boundary behavior without keyword-only rejection (AC: 7, 8)
  - [x] Distinguish "off-topic general assistant request" from "topic is part of the user’s lived situation."
  - [x] Add a soft boundary response for true out-of-scope pivots.
  - [x] Keep reflective analysis active when business, money, work, or tech are part of the user’s real conflict context.
- [x] Keep clarification output Telegram-readable and aligned with prior trust-building work (AC: 1, 2, 4, 5, 6)
  - [x] Reuse the reflection-first and chunked-message style established by Story 1.4.
  - [x] Keep questions short, single-purpose, and low-pressure.
  - [x] Preserve typing-signal behavior if the current Telegram path already emits it.
- [x] Verify the clarification flow and regression boundaries in the live backend (AC: 1, 2, 3, 4, 5, 6, 7, 8)
  - [x] Add tests for a mixed-input clarification turn that separates facts, emotions, and interpretations.
  - [x] Add tests for `fast` mode bounded depth and `deep` mode richer depth.
  - [x] Add tests for vague/contradictory input, out-of-scope pivots, and keyword-false-positive cases where work/tech context is still part of the user’s situation.
  - [x] Run backend validation with `pytest`, `ruff`, and `mypy`.

## Dev Notes

- Story 1.5 is the middle of Epic 1, not a new entrypoint. It must build directly on the trust-making reply from Story 1.4 and hand off naturally to Story 1.6 session closure rather than creating a disconnected mini-flow. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-4-first-trust-making-response-with-situation-reflection.md]
- The product promise here is structured clarity, not clinical analysis. UX explicitly wants clarification to feel progressive and conversational, not interrogative or form-like. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#Component-Strategy]
- PRD scope remains text-first and trust-sensitive. Clarification should improve understanding inside the existing response envelope rather than adding heavy orchestration, memory persistence, or unrelated product surfaces. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#MVP---Minimum-Viable-Product]
- Mode sensitivity from Story 1.3 is now operationally important: `fast` and `deep` can no longer be passive state only; they must shape clarification depth in a predictable, session-scoped way. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-3-fast-deep-reflective-mode.md]
- Product boundaries matter in this story. The bot should not drift into generic helper behavior just because the user mentions money, work, or technology; the real test is whether the topic is part of the user’s current emotional situation.
- The live repo is partially behind the implementation-story chain: `backend/app/conversation/session_bootstrap.py` is still a placeholder, `backend/app/models.py` is still template-heavy, and the route-test source file described by Story 1.2 is not present in `backend/tests/api/routes/`. Story 1.5 implementation should converge those seams rather than assuming the planned files already exist exactly as earlier stories describe.

### Project Structure Notes

- Current Telegram ingress is [`backend/app/bot/api.py`](/home/erda/Музыка/goals/backend/app/bot/api.py). It is still a stub returning `{"status": "accepted"}`, so clarification logic must not be written as if a mature Telegram delivery path already exists.
- Product router composition is centered in [`backend/app/api/main.py`](/home/erda/Музыка/goals/backend/app/api/main.py). Keep work anchored on the `telegram` runtime path and avoid re-centering the product around legacy `login`, `users`, or `items` routes.
- The intended conversation seam exists only as a placeholder in [`backend/app/conversation/session_bootstrap.py`](/home/erda/Музыка/goals/backend/app/conversation/session_bootstrap.py). If Story 1.5 needs reusable clarification orchestration, it should be added under `backend/app/conversation/` in a way that future session-entry and trust-response work can share.
- Persisted models still live in [`backend/app/models.py`](/home/erda/Музыка/goals/backend/app/models.py) and are dominated by starter-template `User` and `Item` types. If clarification needs session-aware state, introduce or extend product-aligned session structures carefully instead of burying reflective state inside unrelated template entities.
- The only current Telegram-related route test source in the repo is foundational routing coverage in [`backend/tests/api/routes/test_foundation_runtime.py`](/home/erda/Музыка/goals/backend/tests/api/routes/test_foundation_runtime.py). Story 1.5 likely needs a new `test_telegram_session_entry.py` or adjacent conversation-focused tests because the planned source file is absent.
- Existing settings live in [`backend/app/core/config.py`](/home/erda/Музыка/goals/backend/app/core/config.py). Keep any mode or clarification tuning inside the existing settings/config seam rather than adding ad hoc environment parsing.

### References

- Story source and acceptance criteria: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Immediate previous story context: [1-4-first-trust-making-response-with-situation-reflection.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-4-first-trust-making-response-with-situation-reflection.md)
- Session-entry and mode baseline: [1-2-telegram-session-entry.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-2-telegram-session-entry.md)
- Mode-selection expectations: [1-3-fast-deep-reflective-mode.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-3-fast-deep-reflective-mode.md)
- Product scope and trust constraints: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Architecture boundaries and runtime constraints: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- UX rules for reflective blocks, clarification prompts, and Telegram readability: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)

## Developer Context

### Technical Requirements

- Clarification is a one-question-at-a-time conversational repair mechanism, not a questionnaire. UX explicitly defines clarification prompts as short, focused, and low-pressure. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md#Component-Strategy]
- The system must actively distinguish factual details, emotional reactions, and interpretation hypotheses. FR8 is not satisfied by generic empathy or by rephrasing the entire message without separation. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-15-Clarification-и-разбор-фактов-эмоций-и-интерпретаций]
- Clarification turns must remain coherent across an active session. Once the user gives extra detail, subsequent prompts should update from the accumulated context rather than treating each message as stateless. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-15-Clarification-и-разбор-фактов-эмоций-и-интерпретаций]
- `fast` mode should compress the clarification path; `deep` mode may widen it, but neither mode should produce wall-of-text output or canned therapy homework. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-15-Clarification-и-разбор-фактов-эмоций-и-интерпретаций]
- The core flow remains text-first and must not depend on mandatory buttons. If buttons exist at all, they are support controls, not the clarification mechanism itself. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md#Non-Functional-Requirements]
- Product boundary enforcement here should be soft and context-aware. Rejecting all work/money/tech mentions would violate the story because those can be part of the user’s real conflict context. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-15-Clarification-и-разбор-фактов-эмоций-и-интерпретаций]

### Architecture Compliance

- Keep Telegram transport in `bot/` and reflective clarification behavior in `conversation/`; do not let the webhook route become the decision engine. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Structure--Boundaries]
- Stay inside the trust-sensitive request path. Clarification should not pull in summary generation, durable memory enrichment, billing, or operator workflows before the user receives the next reflective turn. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Project-Context-Analysis]
- Repo reality overrides aspirational architecture when they conflict. The architecture document prefers SQLAlchemy 2 directly, but the live backend uses SQLModel today; Story 1.5 should extend the real codebase cleanly instead of forcing an unrelated ORM migration inside a clarification story.
- Preserve a clean seam for later safety interruption. Story 1.5 operates on the normal reflective path and should not entangle crisis escalation logic beyond leaving space for Story 3.x to short-circuit later.
- Keep the clarification component reusable so Story 1.6 can consume the structured understanding it produces when building takeaway and next-step guidance.

### Library / Framework Requirements

- Use the current backend stack from [`backend/pyproject.toml`](/home/erda/Музыка/goals/backend/pyproject.toml): FastAPI, SQLModel, Alembic, `pydantic-settings`, and `python-telegram-bot`.
- FastAPI’s official router guidance still centers `APIRouter` composition and `include_router()` for multi-file applications. Story 1.5 should keep new Telegram/conversation behavior inside the existing router composition rather than inventing a parallel app shell. [Official docs: https://fastapi.tiangolo.com/tutorial/bigger-applications/]
- Pydantic Settings still defines `BaseSettings` as the environment-backed configuration mechanism. If clarification needs thresholds or feature toggles, keep them in the existing settings model instead of module-local constants. [Official docs: https://docs.pydantic.dev/latest/api/pydantic_settings/]
- The repo currently pins `python-telegram-bot<22.0,>=21.6`, while the current stable upstream docs are on `v22.6` as of March 11, 2026. Do not accidentally adopt v22-only APIs without first changing the dependency policy. [Official docs: https://docs.python-telegram-bot.org/en/stable/]
- If clarification uses inline callbacks or button support, follow official Telegram library constraints such as callback-data semantics and keep them optional; stable docs continue to document `InlineKeyboardButton` as a support mechanism, not a reason to make the whole flow button-driven. [Official docs: https://docs.python-telegram-bot.org/en/stable/telegram.inlinekeyboardbutton.html]
- SQLModel’s official FastAPI guidance still favors one session per request via a dependency. If Story 1.5 introduces session-backed clarification state, align with the existing request/session dependency style already present in the repo. [Official docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/]

### File Structure Requirements

- Primary touch points should stay inside:
  - `backend/app/bot/api.py`
  - `backend/app/conversation/`
  - `backend/app/models.py` or a product-aligned session model module
  - `backend/app/core/config.py`
  - `backend/tests/api/routes/`
- Likely files to touch:
  - `backend/app/bot/api.py`
  - `backend/app/conversation/session_bootstrap.py`
  - new clarification helpers under `backend/app/conversation/`
  - `backend/app/models.py`
  - a new Alembic migration only if session-mode or clarification state truly requires schema change
  - a new `backend/tests/api/routes/test_telegram_session_entry.py` or equivalent Telegram/conversation test module
- Avoid spreading clarification policy into legacy CRUD/auth modules or generic utility dumping grounds.
- If you add reusable reflective components, keep them under `backend/app/conversation/` so Story 1.6 and later continuity work can build on them instead of copying formatting logic.

### Testing Requirements

- Add or update tests for:
  - a mixed situation message that yields separate factual/emotional/interpretive handling
  - `fast` mode clarification that stays bounded
  - `deep` mode clarification that goes one layer deeper without becoming a script
  - vague or contradictory follow-up input that triggers tentative clarification instead of brittle certainty
  - out-of-scope general-assistant pivots
  - in-scope work/money/tech context that must remain within reflective handling
  - Telegram-readable chunking / no wall-of-text regression
- Keep route-level coverage on `/api/v1/telegram/webhook` and add conversation-level tests where the clarification component is extracted.
- Reuse the existing backend validation toolchain from [`backend/pyproject.toml`](/home/erda/Музыка/goals/backend/pyproject.toml): `pytest`, `ruff`, and `mypy`.
- If the expected Telegram test source file is still absent, create it as part of implementation rather than burying clarification assertions in unrelated legacy suites.

### Previous Story Intelligence

- Story 1.4 established the most important carry-over rule: clarification must continue the reflection-first tone instead of switching to advice, diagnosis, or bureaucratic questioning. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-4-first-trust-making-response-with-situation-reflection.md]
- Story 1.3 made mode selection optional at the UX layer; Story 1.5 is where that optional choice begins to matter behaviorally by changing clarification depth rather than startup friction. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-3-fast-deep-reflective-mode.md]
- Story 1.2 defined the intended Telegram-first session seam, typing feedback, and minimal session state, but the current repo does not fully reflect that documented implementation. Treat this as a reconciliation task, not a reason to open a second conversation path.
- Story 1.6 will depend on the quality of the structured understanding produced here. If clarification state is too vague or transport-specific, the closure story will have to re-derive context and likely regress the flow.

### Git Intelligence Summary

- No usable local git history is available in `/home/erda/Музыка/goals`, so there are no recent commits to mine for coding patterns or prior fixes.

### Project Context Reference

- No `project-context.md` was found in the workspace. The authoritative context set for implementation is `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, Stories 1.2 through 1.4, and the live backend codebase.

### Library / Framework Latest Information

- FastAPI official guidance still emphasizes splitting larger apps with `APIRouter` and composing them into the main application with `include_router()`. This supports keeping Telegram and conversation seams modular rather than centralizing logic in one file. [Official docs: https://fastapi.tiangolo.com/tutorial/bigger-applications/]
- Pydantic’s current `pydantic-settings` docs still define `BaseSettings` as the standard way to pull environment-backed settings into an app, which matches the live `backend/app/core/config.py` approach. [Official docs: https://docs.pydantic.dev/latest/api/pydantic_settings/]
- The stable `python-telegram-bot` docs are currently published as `v22.6` on March 11, 2026, while this repo remains pinned to `<22.0`. Any Telegram clarification UX should therefore stick to 21.x-compatible usage unless the dependency is explicitly upgraded first. [Official docs: https://docs.python-telegram-bot.org/en/stable/telegram.html]
- SQLModel’s current FastAPI tutorial still recommends session injection through a dependency and one session per request, which fits the repo’s existing dependency style if session-backed clarification state is added. [Official docs: https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story auto-discovered from `_bmad-output/implementation-artifacts/sprint-status.yaml` as the first `backlog` story in order: `1-5-clarification-and-breakdown-of-facts-emotions-and-interpretations`.
- Core source context loaded from `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, and prior implementation stories `1-2`, `1-3`, and `1-4`.
- Live backend inspection showed the repo had already advanced past the earlier story narrative: `backend/app/bot/api.py` delegates into `session_bootstrap`, and the active implementation seam for Story 1.5 was `backend/app/conversation/clarification.py`.
- No `project-context.md` was found in the workspace.
- No usable git repository metadata was available for commit intelligence.
- Latest framework verification used official documentation for FastAPI, Pydantic Settings, `python-telegram-bot`, and SQLModel.
- Local verification required a clean Docker Postgres reset plus `alembic upgrade head`, because the existing test database volume had stale schema/data from earlier runs.

### Completion Notes List

- Reworked `backend/app/conversation/clarification.py` into a context-aware clarification component that separates fact, emotion, and interpretation signals while staying reflection-first and one-question-at-a-time.
- Added mode-aware follow-up behavior so `fast` stays bounded around a single main knot and `deep` explicitly goes one layer deeper without turning into a scripted questionnaire.
- Added low-confidence handling for vague, contradictory, and overloaded replies using tentative wording plus a single focused next move instead of brittle certainty.
- Hardened boundary logic so true general-assistant pivots get a soft redirect, while work, money, business, and technology remain in scope when they are part of the user’s lived conflict context.
- Extended route and conversation tests to cover mixed-input clarification, deep-mode depth, vague/contradictory input, and in-scope technology/work cases.
- Validation completed with `uv run pytest backend/tests/api/routes/test_telegram_session_entry.py -q`, `cd backend && uv run pytest tests/conversation/test_clarification.py --confcutdir=tests/conversation -q`, `uv run ruff check backend/app backend/tests`, `uv run mypy backend/app backend/tests`, and `ENABLE_LEGACY_WEB_ROUTES=true uv run pytest backend/tests -q`.

### File List

- _bmad-output/implementation-artifacts/1-5-clarification-and-breakdown-of-facts-emotions-and-interpretations.md
- backend/app/conversation/_text_utils.py
- backend/app/conversation/clarification.py
- backend/tests/api/routes/test_telegram_session_entry.py
- backend/tests/conversation/test_clarification.py

### Change Log

- 2026-03-12: Implemented Story 1.5 clarification flow with context-aware fact/emotion/interpretation separation, mode-aware bounded follow-ups, overload-safe tentative handling, and expanded Telegram/conversation regression coverage.
- 2026-03-12: Code review fixes — _build_context now trims prior_context from start instead of losing latest message on overflow (H1); _is_low_confidence no longer uses word count as proxy for signal confidence (M1/M3); gender-neutral phrase for "устал" marker (M2); _text_utils.py added to File List (L1).
