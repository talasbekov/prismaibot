---
project_name: 'goals'
user_name: 'Bratan'
date: '2026-03-18'
sections_completed: ['technology_stack', 'critical_rules', 'patterns', 'language_rules', 'framework_rules', 'testing_rules', 'style_rules', 'workflow_rules', 'dont_miss_rules']
existing_patterns_found: 12
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

### Backend (Python)
- **Python**: >=3.10
- **FastAPI**: (standard <1.0.0, >=0.114.2)
- **SQLModel**: (<1.0.0, >=0.0.21) — Used for both models and schemas where appropriate.
- **Alembic**: (<2.0.0, >=1.12.1) — Migration management.
- **Pydantic**: (>2.0) — Strict validation (v2).
- **python-telegram-bot**: (<22.0, >=21.6) — Primary user interface.
- **APScheduler**: — Asynchronous enrichment and background jobs.
- **Sentry SDK**: — Error tracking.
- **Ruff**: — Fast linting and formatting.
- **Mypy**: — Strict type checking.

### Frontend (TypeScript/React)
- **React 19**: Modern functional components and hooks.
- **Vite 7**: Fast build tool.
- **Tailwind CSS 4**: Primary styling engine.
- **TanStack Router**: (>=1.157.3) — Typed routing.
- **TanStack Query**: (>=5.90.20) — Data fetching and caching.
- **TanStack Table**: (>=8.21.3) — Declarative tables.
- **Radix UI**: — Accessible component primitives.
- **Biome**: — Linting and formatting (replaces ESLint/Prettier).
- **Playwright**: — E2E testing.

### Infrastructure & Tooling
- **uv**: Python package manager (use `uv.lock`).
- **bun**: JS/TS runtime and package manager (use `bun.lock`).
- **Docker**: Containerization for dev/prod.

---

## Critical Implementation Rules

### Language-Specific Rules

- **Python (Backend)**:
  - Strict type hints required for all functions (`mypy` strict mode).
  - Use `async/await` for all I/O operations. Avoid blocking calls in FastAPI routes.
  - SQLModel entities must explicitly define `table=True` for database models.
  - Use `Pydantic v2` features (e.g., `model_validator`, `field_validator`).

- **TypeScript/React (Frontend)**:
  - Use functional components with React 19 hooks.
  - Strict typing for all component props and state.
  - Navigation must use TanStack Router's typed `Link` and `useNavigate`.
  - API calls must be wrapped in `useQuery` or `useMutation` hooks.
  - Use Biome for formatting and linting (no ESLint/Prettier).

### Framework-Specific Rules

- **FastAPI (Backend)**:
  - Use `Depends()` for all dependency injection (DB sessions, auth, config).
  - Explicitly define `response_model` in route decorators.
  - Follow the directory structure: `api/routes/` for endpoints, `crud/` for DB operations, `models/` for SQLModel classes.
  - Asynchronous background work must be handled via `BackgroundTasks` or the integrated `APScheduler`.

- **React (Frontend)**:
  - Components must be in `frontend/src/components/` using PascalCase naming (e.g., `UserActionsMenu.tsx`).
  - Use `react-hook-form` + `zod` for all form implementations.
  - Tailwind CSS 4 is the only styling method allowed. Use the `cn()` utility for class merging.
  - All navigation and routing must be strictly typed via TanStack Router.

### Testing Rules

- **Backend (Python)**:
  - All tests must reside in `backend/tests/`, following the module-based sub-directory structure.
  - Use `pytest` with `pytest-asyncio` for asynchronous logic testing.
  - External API calls (Telegram, LLM) must be mocked. Never perform real network requests during tests.
  - Database tests must use isolated test sessions.

- **Frontend (Playwright)**:
  - E2E tests must be placed in `frontend/tests/` with the `.spec.ts` suffix.
  - Use resilient selectors: `data-testid` or accessible ARIA roles.
  - Every test must be independent and handle its own setup/teardown (e.g., logging in).

### Code Quality & Style Rules

- **Linting & Formatting**:
  - **Backend**: Strictly follow Ruff rules. No `print()` statements. Run `backend/scripts/format.sh`.
  - **Frontend**: Use Biome for all linting and formatting tasks (`bun run lint`).
- **Naming Conventions**:
  - **Python**: `snake_case` for functions/variables, `PascalCase` for classes.
  - **TypeScript**: `PascalCase` for React components and files, `camelCase` for hooks and variables.
  - **Database**: Table names must be plural and in `snake_case` (e.g., `sessions`). Column names in `snake_case`.

### Development Workflow Rules

- **Git & Repository**:
  - Use branch prefixes: `feat/`, `fix/`, `docs/`, `refactor/`, `chore/`.
  - Follow **Conventional Commits** for all commit messages.
  - Never commit directly to the `main` branch. Use Pull Requests.
  - Keep `uv.lock` and `bun.lock` up to date.
- **Continuous Integration**:
  - Run `backend/scripts/ci-verify.sh` locally before pushing any changes.
- **Database Migrations**:
  - Any model change must include a corresponding Alembic migration script in the same commit.

### Critical Don't-Miss Rules

- **Privacy & Security**:
  - **NEVER** log raw conversational transcripts or user-identifiable message bodies.
  - **NEVER** store raw payment details locally.
  - **Verify Ingress**: Always check `X-Telegram-Bot-Api-Secret-Token` for Telegram webhooks.
- **Anti-Patterns**:
  - No synchronous I/O in the main application loop (use `httpx`, `asyncpg`, etc.).
  - No direct DB access from transport adapters (`bot/`, `api/`).
- **Telegram-Specific Logic**:
  - **Idempotency**: Track and skip processed `update_id` to prevent double-replies.
  - **UX/Latency**: Send `typing` status before long-running LLM operations.
  - **Safety First**: Red-flag detection must trigger immediately, overriding standard conversation flow.
- **LLM/Memory Usage**:
  - **Context Management**: Limit session history sent to LLM to prevent context overflow.
  - **Async Enrichment**: Session summaries and profile updates must happen asynchronously.
