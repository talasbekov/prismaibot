# Story 1.1a: Базовый CI/CD, staging и migration-safe deployment path

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer operating a trust-sensitive MVP backend,
I want настроить минимальный CI/CD pipeline, staging environment и migration-safe deployment discipline,
so that ранняя разработка и выкладка не ломают webhook, billing, deletion или safety-critical flows.

## Acceptance Criteria

1. Существуют отдельные `local`, `staging` и `production` environment-конфигурации, а secrets и environment-specific settings не смешиваются между собой. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-11a-Базовый-CICD-staging-и-migration-safe-deployment-path]
2. CI pipeline выполняет automated tests, linting/type checks и базовую migration-aware verification; build не считается green, если critical validation failed. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-11a-Базовый-CICD-staging-и-migration-safe-deployment-path]
3. Staging позволяет проверять Telegram webhook behavior, payment callback wiring и operator-only endpoints вне production без ad hoc ручных шагов, известных одному человеку. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-11a-Базовый-CICD-staging-и-migration-safe-deployment-path]
4. Schema changes выкатываются по controlled migration path, совместимому с выбранной hosting model, без тихого дрейфа между schema state и app state. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-11a-Базовый-CICD-staging-и-migration-safe-deployment-path]
5. Если CI/CD или staging покрывают trust-critical paths неполно, limitation становится observable; setup не считается sufficient только потому, что manual deploy все еще возможен. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md#Story-11a-Базовый-CICD-staging-и-migration-safe-deployment-path]

## Tasks / Subtasks

- [x] Выпрямить environment baseline под `local` / `staging` / `production` без смешения секретов и runtime assumptions (AC: 1, 3, 5)
  - [x] Зафиксировать и документировать обязательные env vars для backend runtime, migrations, webhook verification и operator-only surface.
  - [x] Убрать зависимость staging/production story от template-специфичных web/frontend переменных, если они не нужны Telegram-first backend runtime.
  - [x] Подготовить отдельные environment templates или documented env sets для staging и production без reuse локальных небезопасных defaults из `.env`.
- [x] Довести CI baseline до architecture-required quality gates (AC: 2, 5)
  - [x] Расширить существующий backend workflow так, чтобы он явно запускал `ruff`, `mypy`, `pytest` и migration-aware verification вместо implicit test-only green path.
  - [x] Добавить failure behavior, делающий limitation observable, если DB migration path, config loading или app startup в CI ломаются.
  - [x] Не оставлять story в состоянии, где “tests pass” но migration discipline или environment validity не проверяются.
- [x] Выровнять staging deployment path под trust-sensitive pre-production verification (AC: 1, 3, 4)
  - [x] Определить управляемый staging flow для backend-only сервиса с PostgreSQL, webhook wiring, ops endpoints и callback verification.
  - [x] Убрать reliance на self-hosted/manual knowledge path как единственный способ staging deploy.
  - [x] Убедиться, что staging может проверять `/api/v1/ops/healthz`, `/api/v1/ops/readyz`, Telegram webhook ingress seam и callback-related config без production rollout.
- [x] Сделать deployment migration-safe и совместимым с выбранной hosting model (AC: 3, 4)
  - [x] Явно определить controlled migration execution order относительно app rollout: migration/prestart first, app traffic second.
  - [x] Проверить, что текущие compose/deploy scripts и managed-platform assumptions не допускают тихий drift между кодом и схемой.
  - [x] Зафиксировать rollback/failed-migration expectation хотя бы на MVP-уровне observability и deploy halt.
- [x] Добавить тесты и lightweight docs для operational confidence (AC: 2, 3, 5)
  - [x] Обновить tests или CI assertions для environment parsing, ops readiness behavior и migration/prestart scripts where practical.
  - [x] Добавить краткую документацию по локальному, staging и production delivery path, чтобы dev следующих story не изобретал процесс заново.

## Dev Notes

- Эта история продолжает foundation work из story `1.1` и должна строиться поверх уже существующих seams `bot/`, `conversation/`, `memory/`, `safety/`, `billing/`, `ops/`, `shared`, а не переизобретать runtime shape. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-1-starter-template-telegram-backend.md]
- Архитектура требует environments `local`, `staging`, `production`; staging здесь обязательный, а не optional, потому что нужно безопасно проверять webhook behavior, payment callbacks, deletion workflows и alert routing вне production. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Infrastructure--Deployment]
- CI/CD baseline по архитектуре должен включать automated tests, linting, type checks, migration-aware deploy gating и controlled deployment to staging and production. Текущий репозиторий частично это покрывает, но явно не дотягивает до полного story scope. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#CICD-Strategy]
- PRD и architecture согласованы в том, что webhook acknowledgements, payment callback failures, deletion requests и alert routing failures должны быть observable, retry-safe и не должны теряться в ad hoc operational knowledge. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md] [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Operational-Signal-Expectations]
- Текущий CI workflow [`test-backend.yml`](/home/erda/Музыка/goals/.github/workflows/test-backend.yml) поднимает Docker services и гоняет backend tests, но не запускает отдельно `ruff` и `mypy`; это gap относительно architecture-required validation gates.
- Текущие deploy workflows [`deploy-staging.yml`](/home/erda/Музыка/goals/.github/workflows/deploy-staging.yml) и [`deploy-production.yml`](/home/erda/Музыка/goals/.github/workflows/deploy-production.yml) все еще завязаны на template-era `self-hosted` + `docker compose` path и не отражают Railway-first / Render-equivalent managed deployment baseline, указанную в архитектуре.
- Текущий runtime compose path в [`compose.yml`](/home/erda/Музыка/goals/compose.yml) уже содержит важный порядок `db -> prestart (migrations + initial data) -> backend`, и этот controlled order нужно либо сохранить, либо перенести в managed-platform equivalent без silent schema/app drift.
- В story 1.1 readiness уже опирается на `/api/v1/ops/readyz` с реальной DB probe, поэтому staging/CI в этой истории должны использовать ops endpoints как часть deployment confidence, а не только process start. [Source: /home/erda/Музыка/goals/backend/app/ops/api.py]

### Project Structure Notes

- Основные изменения этой истории должны оставаться в `.github/workflows/`, `backend/scripts/`, `backend/app/core/config.py`, `compose.yml`, `.env` templates и краткой operational documentation.
- Не смещай центр архитектуры обратно в template-oriented frontend stack. Story относится к backend delivery discipline для Telegram-first сервиса.
- Если сохраняется `docker compose` path для local verification, не делай его единственным знанием о deploy. Staging/prod path должен быть читаемым, воспроизводимым и отделенным от локальной разработки.
- Не завязывай story на `frontend/`, `adminer`, mail flows или legacy CRUD routes, если это не требуется для trust-critical backend rollout checks.

### References

- Story source and ACs: [epics.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/epics.md)
- Product constraints and trust/reliability requirements: [prd.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md)
- Deployment model, CI/CD, environments, observability: [architecture.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md)
- Trust-sensitive Telegram UX and failure posture: [ux-design-specification.md](/home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md)
- Previous foundation story: [1-1-starter-template-telegram-backend.md](/home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-1-starter-template-telegram-backend.md)
- Current CI workflow: [test-backend.yml](/home/erda/Музыка/goals/.github/workflows/test-backend.yml)
- Current staging deploy workflow: [deploy-staging.yml](/home/erda/Музыка/goals/.github/workflows/deploy-staging.yml)
- Current production deploy workflow: [deploy-production.yml](/home/erda/Музыка/goals/.github/workflows/deploy-production.yml)
- Current compose-based rollout order: [compose.yml](/home/erda/Музыка/goals/compose.yml)

## Developer Context

### Technical Requirements

- Поддерживай три environment режима: `local`, `staging`, `production`. Они прямо требуются архитектурой и story AC, а staging не является optional промежуточным окружением. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Infrastructure--Deployment]
- CI должен валить изменения не только по тестам, но и по lint/type/migration gates. История не закрыта, если pipeline все еще пропускает migration drift или config/startup breakage. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#CICD-Strategy]
- Deployment должен сохранять controlled order `migrations before app traffic`. Любой managed-platform equivalent должен воспроизводить смысл текущей цепочки `prestart -> backend`, а не просто “запустить контейнер”. [Source: /home/erda/Музыка/goals/compose.yml]
- Health and readiness checks должны быть частью delivery baseline. Для этого проекта readiness уже должен подтверждать реальную DB reachability, а не только наличие env vars. [Source: /home/erda/Музыка/goals/backend/app/ops/api.py]
- В trust-sensitive продукте staging должен покрывать webhook behavior, callback wiring, operator-only endpoints и deploy-time config validity до production rollout. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md]

### Architecture Compliance

- Сохраняй architecture baseline: один deployable FastAPI service + managed PostgreSQL, без premature worker split и без возврата к full-stack template assumptions. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Infrastructure--Deployment]
- Следуй Railway-first или Render-equivalent managed deployment direction. Если временно остается compose-based deploy automation, оформи это как transitional path, а не как целевую архитектуру. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Deployment-Baseline]
- Не допускай, чтобы deploy process зависел от знаний одного человека или от незафиксированных ручных шагов. Это прямо противоречит story AC и architecture CI/CD intent.
- Наблюдаемость должна быть privacy-aware: не добавляй routine sensitive-content logging ради deploy debugging. [Source: /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md#Observability-Strategy]

### Library / Framework Requirements

- Текущий backend stack в репозитории: `FastAPI`, `sqlmodel`, `alembic`, `psycopg`, `pydantic-settings`, `apscheduler`, `httpx`, `python-telegram-bot`, `pytest`, `mypy`, `ruff`. История должна использовать уже существующий toolchain, а не вводить новый CI/runtime стек без явной необходимости. [Source: /home/erda/Музыка/goals/backend/pyproject.toml]
- Для GitHub Actions в репозитории уже используются `actions/checkout@v6`, `actions/setup-python@v6`, `astral-sh/setup-uv@v7`. Предпочтительно дорабатывать существующий workflow, а не создавать параллельный delivery path без причины. [Source: /home/erda/Музыка/goals/.github/workflows/test-backend.yml]
- Alembic остается source of truth для schema migrations; migration verification должна опираться на `alembic upgrade head` или эквивалентный controlled check, а не на косвенные предположения о состоянии БД. [Source: /home/erda/Музыка/goals/backend/scripts/prestart.sh]

### File Structure Requirements

- Наиболее вероятные файлы изменений:
  - `.github/workflows/test-backend.yml`
  - `.github/workflows/deploy-staging.yml`
  - `.github/workflows/deploy-production.yml`
  - `backend/scripts/prestart.sh`
  - `backend/scripts/tests-start.sh`
  - `backend/app/core/config.py`
  - `compose.yml`
  - `.env` / `.env.example` / новые env templates or docs
- Если добавляется delivery documentation, держи ее рядом с backend/deployment context и делай короткой, task-oriented.
- Не вноси крупные изменения в domain modules (`conversation/`, `memory/`, `billing/`, `safety/`), если они не нужны для rollout verification.

### Testing Requirements

- Минимальный story-complete baseline должен включать:
  - CI запуск `pytest`
  - CI запуск `ruff`
  - CI запуск `mypy`
  - migration-aware verification
  - проверку startup/readiness behavior
- Добавь или обнови tests/checks для env parsing и ops readiness там, где это дает прямую ценность для deployment confidence.
- Если staging path меняется, должна быть documented verification sequence для `/api/v1/ops/healthz`, `/api/v1/ops/readyz`, webhook ingress seam и critical config presence.
- Не считай историю завершенной, если pipeline формально зеленый, но не покрывает migration drift, env separation или readiness semantics.

### Previous Story Intelligence

- Story `1.1` уже отделила product runtime center от legacy CRUD/auth template routes и ввела ops endpoints как часть foundation baseline. Не откатывай это, пытаясь “подружить deploy” с прежней template topology. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-1-starter-template-telegram-backend.md]
- Story `1.1` также зафиксировала, что env-backed settings должны оставаться cwd-independent и secrets не должны хардкодиться. Используй этот baseline для environment templates и CI checks. [Source: /home/erda/Музыка/goals/_bmad-output/implementation-artifacts/1-1-starter-template-telegram-backend.md]
- Readiness уже усиливали до реального DB probe. Значит deploy confidence в этой истории должен опираться на readiness semantics, а не на “container started successfully”.

### Git Intelligence Summary

- Локальный workspace не является git-репозиторием, поэтому commit history analysis для этой истории недоступен.

### Library / Framework Latest Information

- FastAPI current official guidance по deployment продолжает опираться на стандартный ASGI app lifecycle, process managers/containers и health-oriented deployment discipline; не изобретай custom runtime layer для этой истории. [Source: https://fastapi.tiangolo.com/deployment/docker/]
- Alembic official docs по-прежнему предполагают явный migration command path и контролируемое применение schema revisions; implicit schema sync не является заменой migration discipline. [Source: https://alembic.sqlalchemy.org/en/latest/]
- Railway и Render обе поддерживают health-check-oriented managed deployment patterns; для этой истории это означает, что staging/prod path должен иметь явную health/readiness verification, а не только build success. This is an inference from official platform deployment guidance.

### Project Context Reference

- Отдельный `project-context.md` в workspace не найден. Для этой истории authoritative context set: `epics.md`, `prd.md`, `architecture.md`, `ux-design-specification.md`, предыдущая story `1.1`, текущие CI/deploy workflows и compose/runtime files.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story target auto-discovered from `_bmad-output/implementation-artifacts/sprint-status.yaml` as the first backlog item in order: `1-1a-basic-cicd-staging-and-migration-safe-deployment-path`.
- Loaded full workflow engine, dev-story workflow config, instructions, checklist, sprint status, target story, architecture context, PRD/UX references, previous story `1.1`, and current local delivery/runtime files.
- No `project-context.md` was found.
- Git intelligence branch skipped because `/home/erda/Музыка/goals` is not a git repository.
- Moved sprint tracking for `1-1a-basic-cicd-staging-and-migration-safe-deployment-path` from `ready-for-dev` to `in-progress` before implementation and to `review` after completion.
- Added non-local runtime validation for `DEPLOYMENT_TARGET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, and `OPS_AUTH_TOKEN` in `backend/app/core/config.py`.
- Added billing webhook and ops auth-check seams plus matching config validation for `PAYMENT_PROVIDER_WEBHOOK_SECRET` so staging/prod verification covers callback wiring and operator-only access explicitly.
- Added environment templates for local, staging, and production plus `docs/delivery.md` to document required secrets, verification flow, and managed-platform rollout sequence.
- Added `backend/scripts/ci-verify.sh`, hardened `backend/scripts/test.sh`, and expanded GitHub Actions workflows to run lint, mypy, migration-aware verification, backend image builds, and runtime smoke checks.
- Updated compose runtime wiring to pass delivery env vars through `prestart` and `backend`, and switched backend healthcheck to `/api/v1/ops/readyz`.
- Full regression validation initially exposed two pre-existing repo integration gaps: legacy auth/user/item tests were not opting into legacy routes, and compose smoke verification was using a stale backend image. Fixed by moving legacy-route coverage to an isolated `legacy_client` test harness and forcing `docker compose build prestart backend` before smoke startup.
- Code review fixes closed the remaining gaps by turning staging/production workflows into actual managed deploy flows, removing non-local `FRONTEND_HOST` coupling from the baseline, and verifying remote readiness, operator auth, and payment callback seams after deploy.
- Validation completed successfully with `uv run pytest tests/api/routes/test_foundation_runtime.py tests/api/routes/test_ops_routes.py tests/api/routes/test_billing_routes.py tests/api/routes/test_login.py tests/api/routes/test_users.py tests/api/routes/test_items.py tests/api/routes/test_private.py`, `uv run bash scripts/ci-verify.sh "Story 1.1a review fixes"`, and curl smoke checks for `/api/v1/ops/healthz`, `/api/v1/ops/readyz`, `/api/v1/ops/auth-check`, `/api/v1/telegram/webhook`, and `/api/v1/billing/webhook`.

### Completion Notes List

- Added explicit local/staging/production env templates and documented the required non-local secrets for Telegram webhook verification, ops access, and migration-safe rollout.
- Strengthened CI with a reusable `backend/scripts/ci-verify.sh` gate that runs `ruff`, `mypy`, `alembic upgrade head`, initial data setup, and the full pytest suite with coverage.
- Reworked staging and production workflows to use GitHub Environments plus reproducible managed deploy steps for Railway/Render instead of the old self-hosted compose-only path.
- Updated compose and delivery docs so backend smoke verification now checks `/api/v1/ops/healthz`, `/api/v1/ops/readyz`, `/api/v1/ops/auth-check`, the Telegram webhook seam, and the billing callback seam after rebuilding the backend image.
- Added config validation and tests for non-local deployment settings so staging/production cannot stay green with missing delivery-critical secrets.
- Preserved runtime behavior by keeping legacy routes disabled by default while opting them back into an isolated regression-only test context.
- Verified the story with `uv run pytest tests/api/routes/test_foundation_runtime.py tests/api/routes/test_ops_routes.py tests/api/routes/test_billing_routes.py tests/api/routes/test_login.py tests/api/routes/test_users.py tests/api/routes/test_items.py tests/api/routes/test_private.py`, `uv run bash scripts/ci-verify.sh "Story 1.1a review fixes"`, and curl smoke checks for health, readiness, ops auth, Telegram ingress, and billing webhook handling.

### File List

- _bmad-output/implementation-artifacts/1-1a-basic-cicd-staging-and-migration-safe-deployment-path.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- .github/workflows/test-backend.yml
- .github/workflows/deploy-staging.yml
- .github/workflows/deploy-production.yml
- compose.yml
- .env
- .env.example
- .env.staging.example
- .env.production.example
- backend/README.md
- backend/app/billing/api.py
- backend/scripts/test.sh
- backend/scripts/ci-verify.sh
- backend/app/core/config.py
- backend/tests/conftest.py
- backend/tests/api/routes/test_billing_routes.py
- backend/tests/api/routes/test_foundation_runtime.py
- backend/tests/api/routes/test_ops_routes.py
- docs/delivery.md

### Change Log

- 2026-03-12: Added delivery environment templates, non-local config validation, CI/staging/production verification workflows, compose readiness healthcheck wiring, a reusable backend verification script, and delivery documentation for story `1.1a`.
- 2026-03-12: Closed code review findings by adding billing/operator verification seams, isolating legacy route tests from the default runtime, and converting staging/production workflows into reproducible managed deploy + remote verification paths.
