# Story 1.1: Инициализация проекта из starter template для Telegram-first backend

Status: done
<!-- Reviewed: 2026-03-11 — all critical/high issues resolved -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer setting up the MVP foundation,
I want развернуть проект из выбранного starter approach и подготовить минимальную рабочую backend-основу,
so that дальнейшие пользовательские истории Telegram-бота могут реализовываться на согласованной архитектурной базе.

## Acceptance Criteria

1. Initial codebase uses a minimal FastAPI backend foundation with modular monolith structure and avoids unnecessary full-stack or microservice scaffolding. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-11-Инициализация-проекта-из-starter-template-для-Telegram-first-backend]
2. Initial project structure and dependencies are sufficient for bot ingress, conversation flow evolution, and persistence evolution, but do not create upfront domain tables or unrelated infrastructure. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-11-Инициализация-проекта-из-starter-template-для-Telegram-first-backend]
3. Development environment, dependency installation, and baseline configuration work reproducibly and are ready for follow-on Telegram session entry stories. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-11-Инициализация-проекта-из-starter-template-для-Telegram-first-backend]
4. Foundation remains compatible with Railway-first or Render-equivalent managed deployment and keeps secrets/config externalized from source code. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-11-Инициализация-проекта-из-starter-template-для-Telegram-first-backend]
5. Setup failures are observable and the project is not treated as ready if starter baseline is partial or inconsistent. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-11-Инициализация-проекта-из-starter-template-для-Telegram-first-backend]

## Tasks / Subtasks

- [x] Audit the existing repository scaffold and define the keep/adapt/defer boundary for this story (AC: 1, 2, 4)
  - [x] Confirm that the repo already contains a full-stack FastAPI template scaffold under `backend/` and `frontend/`, and treat this story as adaptation/minimization rather than greenfield generation from an empty directory.
  - [x] Identify legacy modules that should not be expanded for MVP startup in this story, especially auth/user/item CRUD surfaces and frontend-driven assumptions.
  - [x] Record a concrete decision in code comments or lightweight docs on whether legacy modules are retained temporarily, isolated, or removed from active runtime wiring.
- [x] Establish the Telegram-first backend foundation without premature domain build-out (AC: 1, 2)
  - [x] Restructure or prepare backend module boundaries toward the target modular monolith shape: `bot/`, `conversation/`, `memory/`, `safety/`, `billing/`, `ops/`, `shared/` or an equivalent near-term scaffold that clearly preserves those seams.
  - [x] Ensure the app entrypoint and router composition can support Telegram ingress as a first-class path without requiring the existing web-auth CRUD API surface to remain central.
  - [x] Do not create product-domain tables, summaries, profiles, billing tables, or safety tables in this story unless strictly required for startup baseline.
- [x] Align dependency and configuration baseline with the architecture decision (AC: 1, 3, 4)
  - [x] Keep FastAPI, SQLModel, Alembic, psycopg, Pydantic Settings, httpx, and APScheduler available or planned according to the architecture baseline.
  - [x] Add `python-telegram-bot` if missing from the active backend environment baseline, but do not implement bot logic yet.
  - [x] Keep configuration externalized through environment-backed settings and avoid introducing hardcoded secrets, tokens, or provider credentials.
  - [x] Preserve compatibility with a single deployable service and managed PostgreSQL.
- [x] Create the minimum runtime and persistence baseline required for follow-on stories (AC: 2, 3, 5)
  - [x] Ensure the backend starts reproducibly in local development.
  - [x] Ensure migration tooling remains usable, but do not generate unrelated schema just to “prepare everything upfront”.
  - [x] Provide or preserve a health/readiness mechanism suitable for startup verification if one already exists or is trivial to add without broadening scope.
  - [x] Make startup/configuration errors observable via logs or explicit failure behavior.
- [x] Verify the foundation and protect future implementation seams (AC: 3, 4, 5)
  - [x] Run baseline checks for dependency install, app import/startup, and any existing minimal test suite relevant to startup.
  - [x] Add or update tests that verify startup/config behavior introduced by this story.
  - [x] Document the specific files/folders that later stories should extend instead of reinventing.

## Dev Notes

- This story is a foundation story and was forced by final validation because the architecture explicitly specifies a starter approach. It is not a user-visible feature story, but it is a prerequisite context story for the rest of Epic 1. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Starter-Template-Evaluation]
- The architecture chose a minimal FastAPI backend foundation with an explicit modular monolith structure, specifically to avoid inheriting frontend/auth/infrastructure assumptions from a heavier full-stack template. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Chosen-Starter-Approach]
- The local repo already contains a full-stack FastAPI template skeleton:
  - `backend/app/api/routes/login.py`
  - `backend/app/api/routes/users.py`
  - `backend/app/api/routes/items.py`
  - `frontend/`
  - compose files for a broader web stack
  This means the implementation should minimize and redirect the existing scaffold instead of blindly layering Telegram-specific code on top of an auth-first CRUD architecture.
- The story must not trigger broad destructive cleanup unless clearly necessary. Prefer isolating, detaching from runtime wiring, or narrowing the active app path over mass deletion.
- Do not create all future modules/tables “because they will be needed later”. The create-epics workflow explicitly forbids big upfront technical work.

### Project Structure Notes

- Current active backend entrypoint is [`backend/app/main.py`](/home/erda/Музыка/goals/backend/app/main.py), which currently wires a generic API router and CORS around web-oriented routes. This will likely need adaptation so the runtime center shifts toward Telegram-first backend behavior rather than login/users/items CRUD.
- Current API router aggregator is [`backend/app/api/main.py`](/home/erda/Музыка/goals/backend/app/api/main.py), which includes `login`, `users`, `utils`, `items`, and `private` routes. That is not aligned with the target domain and should not remain the architectural center. [Source: /home/erda/Музыка/goals/backend/app/api/main.py]
- Current settings live in [`backend/app/core/config.py`](/home/erda/Музыка/goals/backend/app/core/config.py). Reuse the environment-backed `BaseSettings` pattern rather than inventing a second config system. Extend it carefully for Telegram/backend needs. [Source: /home/erda/Музыка/goals/backend/app/core/config.py]
- Current models in [`backend/app/models.py`](/home/erda/Музыка/goals/backend/app/models.py) are template artifacts (`User`, `Item`). Do not expand these into product-domain models. If they stay temporarily, they should not shape the product architecture.
- Current backend dependency baseline in [`backend/pyproject.toml`](/home/erda/Музыка/goals/backend/pyproject.toml) already includes FastAPI, Alembic, SQLModel, psycopg, and Pydantic Settings, but does not currently list `python-telegram-bot` or `apscheduler`. If added, add only what this story truly needs as foundation. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]

### References

- Story source and ACs: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Product constraints and NFRs: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Starter decision, deployment baseline, adapter boundaries, structure guidance: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- Telegram-native UX constraints and text-first behavior: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)

## Developer Context

### Technical Requirements

- Use Python backend only as the implementation center for this story. The architecture explicitly selects Python, FastAPI, PostgreSQL, SQLAlchemy/SQLModel style persistence, Alembic, and a modular monolith deployment shape. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Technical-Constraints--Dependencies]
- Keep the service as one deployable app with managed PostgreSQL; do not introduce workers, queues, Redis, Celery, or microservices in this story. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Infrastructure--Deployment]
- Preserve externalized config and secrets handling. Existing settings already load from top-level `.env`; keep this pattern or improve it, but do not hardcode Telegram/billing secrets. [Source: /home/erda/Музыка/goals/backend/app/core/config.py]
- The first follow-on stories require Telegram entry, text-first session bootstrapping, and low-friction conversation start. Foundation choices in this story must make those easy, not harder. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Epic-1-Первая-полезная-reflective-сессия-в-Telegram]

### Architecture Compliance

- Follow the chosen starter approach: minimal FastAPI backend foundation, explicit modular monolith structure, Railway-first or Render-equivalent deployment path, community starters used only as references. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Chosen-Starter-Approach]
- Protect early adapter boundaries:
  - Telegram adapter must remain ingress/delivery, not the domain center.
  - Payment provider logic must remain behind billing boundaries.
  Even if not implemented in this story, the folder/layout baseline should not violate these seams. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Adapter-Boundaries]
- Avoid letting the existing full-stack template shape the product around auth-first REST CRUD. The architecture explicitly rejected that as the wrong center of gravity. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Starter-Decision-Rationale]
- Foundation work must be story-scoped. Do not create all future tables or all future endpoints.

### Library / Framework Requirements

- Active local backend baseline already pins:
  - `fastapi[standard] >=0.114.2,<1.0.0`
  - `alembic >=1.12.1,<2.0.0`
  - `sqlmodel >=0.0.21,<1.0.0`
  - `psycopg[binary] >=3.1.13,<4.0.0`
  - `pydantic-settings >=2.2.1,<3.0.0`
  Preserve compatibility unless there is a compelling reason to change. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- Architecture-recommended additions for this product baseline include `httpx`, `apscheduler`, and `python-telegram-bot`. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Recommended-Initialization-Commands]
- Prefer official docs and stable APIs:
  - FastAPI docs: https://fastapi.tiangolo.com/
  - SQLModel docs: https://sqlmodel.tiangolo.com/
  - SQLAlchemy 2.x docs: https://docs.sqlalchemy.org/en/20/
  - Alembic docs: https://alembic.sqlalchemy.org/en/latest/
  - Pydantic docs: https://docs.pydantic.dev/latest/
  - python-telegram-bot docs: https://docs.python-telegram-bot.org/en/stable/
- Do not add frontend/runtime dependencies to serve this story. Frontend exists in repo but this story is backend-foundation scoped.

### File Structure Requirements

- Primary touch surface should stay inside `backend/`.
- Expected high-value files/folders for this story:
  - `backend/pyproject.toml`
  - `backend/app/main.py`
  - `backend/app/api/main.py` or a replacement routing composition file
  - `backend/app/core/config.py`
  - new modular directories under `backend/app/` that prepare product seams, such as `bot/`, `conversation/`, `memory/`, `safety/`, `billing/`, `ops/`, `shared/`
- Avoid scattering startup logic across unrelated legacy template modules.
- If existing template routes remain, they should not remain the default growth path for product implementation.
- Do not create product-domain models or migrations unless strictly required for startup baseline. If you must touch migrations, keep them minimal and explain why.

### Testing Requirements

- Use the existing backend test toolchain (`pytest`, `mypy`, `ruff`, coverage baseline) from [`backend/pyproject.toml`](/home/erda/Музыка/goals/backend/pyproject.toml).
- Minimum validation for this story should include:
  - dependency install succeeds
  - backend app imports/starts with the new foundation
  - config loads correctly in local dev
  - any new routing/bootstrap module is covered by at least a smoke test
- Do not claim readiness if startup is only structurally rearranged but not actually executable.
- If a health/readiness path is introduced or preserved in this story, add a test for it.

### Library / Framework Latest Information

- FastAPI official docs continue to center on application setup via `FastAPI()` and router-based composition. Preserve that pattern instead of inventing a custom framework layer too early. [Official docs: https://fastapi.tiangolo.com/]
- SQLAlchemy official docs are on 2.x style documentation; avoid old 1.x patterns when touching persistence or engine setup. [Official docs: https://docs.sqlalchemy.org/en/20/]
- python-telegram-bot stable docs should be the source of truth for Telegram integration patterns; do not implement against random examples from blogs. [Official docs: https://docs.python-telegram-bot.org/en/stable/]

### Previous Story Intelligence

- No previous implementation story file exists. This is the first implementation story and should establish conventions deliberately so later stories do not need to undo avoidable decisions.

### Git Intelligence Summary

- No usable local git history was available through the workflow step, so there are no recent commit learnings to inherit.

### Project Context Reference

- No `project-context.md` was found in the workspace. Use `epics.md`, `architecture.md`, `prd.md`, `ux-design-specification.md`, and the existing local scaffold as the authoritative context set for this story.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story created from `_bmad-output/planning-artifacts/epics.md` with architecture and local scaffold analysis.
- No `sprint-status.yaml` was present, so the target story was inferred from the explicit request to create the first implementation story.
- No prior implementation story file was available.
- Runtime foundation refactored around product-first router composition with `ops` and `telegram` routes, while legacy CRUD/auth routes were retained only as a compatibility layer.
- Top-level `.env` loading was made cwd-independent to avoid startup/test failures when running commands from the repository root.
- Validation required a local PostgreSQL instance plus Alembic upgrade because the existing backend test harness eagerly initializes SQLModel sessions.
- After the FastAPI template was added to the project workspace, the story was revalidated against the current backend scaffold and confirmed to remain aligned with the Telegram-first foundation scope.
- Code review found three high-severity scope/validation issues: legacy template routes were enabled by default, `/ops/readyz` did not verify database reachability, and Telegram session-entry logic had leaked into foundation scope.
- Review fixes removed product behavior from the foundation webhook path, changed legacy route exposure to opt-in, and upgraded readiness to perform a real database probe.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Local repo already contains a full-stack scaffold; implementation should adapt/minimize it instead of assuming an empty project.
- Starter-template requirement from final validation is explicitly encoded here.
- Added modular seams under `backend/app/` for `bot`, `conversation`, `memory`, `safety`, `billing`, `ops`, and `shared` without introducing premature domain tables or migrations.
- Added product-aligned runtime routes for `ops/healthz`, `ops/readyz`, and a placeholder Telegram webhook ingress while keeping legacy login/users/items routes isolated from the runtime center.
- Added `DEPLOYMENT_TARGET`, `ENABLE_LEGACY_WEB_ROUTES`, and `TELEGRAM_BOT_TOKEN` to env-backed settings and made `.env` resolution stable regardless of working directory.
- Added foundation smoke tests and ops endpoint tests; verified `uv run pytest`, `uv run ruff check`, and `uv run mypy app tests` all pass.
- Revalidated the current FastAPI template baseline by starting local PostgreSQL via Docker Compose, applying Alembic migrations, and rerunning the backend validation suite successfully.
- Fixed code-review findings by making legacy CRUD/auth routes opt-in, reducing Telegram webhook behavior to a minimal ingress seam, and replacing config-only readiness with a real database probe.
- Updated the backend test suite so foundation coverage matches story 1.1 scope instead of silently validating story 1.2 behavior.

### File List

- _bmad-output/implementation-artifacts/1-1-starter-template-telegram-backend.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/main.py
- backend/app/api/main.py
- backend/app/billing/__init__.py
- backend/app/bot/__init__.py
- backend/app/bot/api.py
- backend/app/conversation/__init__.py
- backend/app/conversation/session_bootstrap.py
- backend/app/core/config.py
- backend/app/memory/__init__.py
- backend/app/models.py
- backend/app/ops/__init__.py
- backend/app/ops/api.py
- backend/app/safety/__init__.py
- backend/app/shared/__init__.py
- backend/app/shared/runtime_policy.py
- backend/pyproject.toml
- backend/tests/conftest.py
- backend/tests/api/routes/test_foundation_runtime.py
- backend/tests/api/routes/test_ops_routes.py

### Change Log

- 2026-03-10: Re-centered the backend around Telegram-first foundation routes, added modular seam packages, hardened env loading, and verified the backend baseline with pytest, ruff, and mypy.
- 2026-03-10: Revalidated the story after the FastAPI template update by bringing up local PostgreSQL, applying migrations, and confirming pytest, ruff, and mypy all pass against the current scaffold.
- 2026-03-10: Addressed code-review findings by making legacy routes opt-in, reducing the Telegram webhook to foundation-only ingress behavior, removing Telegram session schema from story 1.1 scope, and upgrading readiness checks to validate live database connectivity.
- 2026-03-11: Adversarial code review (round 2) — removed TelegramSession model and migration (story 1.2 scope leak), stubbed conversation/session_bootstrap.py as seam placeholder, simplified bot/api.py to foundation-only ingress, fixed readyz blocking event loop (async→sync handler), added SECRET_KEY non-local env validation, removed global ENABLE_LEGACY_WEB_ROUTES env hack from test conftest, deleted test_telegram_session_entry.py (story 1.2 scope), corrected File List to include main.py and session_bootstrap.py.
