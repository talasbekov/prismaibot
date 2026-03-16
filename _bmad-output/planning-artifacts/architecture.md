---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md
  - /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md
  - /home/erda/Музыка/goals/_bmad-output/planning-artifacts/product-brief-goals-2026-03-09.md
  - /home/erda/Музыка/goals/_bmad-output/planning-artifacts/research/technical-llm-memory-architecture-for-telegram-bots-research-2026-03-09.md
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-03-10'
project_name: 'goals'
user_name: 'Bratan'
date: '2026-03-10'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**  
The product currently defines 43 functional requirements across the following architectural areas:

- user access and low-friction session start;
- guided reflection flow and structured conversational interpretation;
- continuity between sessions through retained memory artifacts;
- safety and crisis escalation behavior;
- subscription, access control, and payment state handling;
- retention mechanisms such as periodic reflective insights;
- privacy, deletion, and transcript retention boundaries;
- operator oversight and service operations.

Architecturally, this means the system is not just a Telegram bot. It is a stateful conversational backend with trust-sensitive branching, memory-aware orchestration, payment-aware access control, and operator-facing observability.

**Non-Functional Requirements:**  
Several NFRs will strongly shape the architecture:

- main user-facing response target of up to 8 seconds p95 for typical interaction paths;
- asynchronous summary generation so post-session memory work does not block the conversation;
- encryption in transit and at rest;
- raw transcript minimization and durable summary/profile retention;
- idempotent webhook handling and reliable payment callback processing;
- red-flag alert visibility and deletion auditability;
- mobile-first Telegram behavior and readability-driven UX performance.

These NFRs imply a strong need for explicit state management, bounded request-path work, asynchronous enrichment, and operational discipline.

**Scale & Complexity:**  
This project should be treated as a high-complexity, high-sensitivity greenfield conversational backend, but not as an enterprise-scale system.

- Primary domain: Telegram-first conversational backend for mental wellness / psychology-adjacent use cases
- Complexity level: High
- Estimated architectural components: 8–10 major components or modules

The complexity is driven less by feature count than by the combination of:
- emotionally sensitive conversations;
- memory correctness requirements;
- safety-sensitive flow branching;
- payment and access-state coordination;
- operator visibility without routine exposure to sensitive content.

Weekly insight exists in scope, but should be treated as a secondary architectural driver compared with the core reflection, continuity, safety, and access-state flows.

### Technical Constraints & Dependencies

Known constraints and dependencies already present in the project context:

- Telegram is the only core product surface in MVP.
- The architecture must support text-first interaction rather than UI-heavy workflows.
- Summary-per-session plus accumulated user profile is the chosen MVP memory direction.
- Raw transcript retention must be minimized.
- Python is the selected implementation language for MVP.
- The architecture should favor a modular monolith rather than microservices.
- PostgreSQL is the preferred durable store.
- Async post-session enrichment is expected for summary/profile updates and possibly later weekly insight generation.
- Payment integration must support Telegram Stars and/or ЮKassa.
- Static crisis/help links are required for escalation flows.
- No vector-first retrieval architecture should exist in MVP critical path.
- No public API or SDK surface is required.

### Cross-Cutting Concerns Identified

The following concerns will affect multiple architectural modules simultaneously:

- **Trust and Safety:** red-flag detection, humane escalation, and careful product boundary enforcement.
- **Privacy and Retention:** durable summary/profile storage, transcript minimization, deletion workflows, and constrained operator visibility.
- **Latency and User Experience:** keeping the first meaningful response fast enough while still assembling enough context for quality.
- **Request-Path Quality Under Context Assembly:** Telegram ingress, memory lookup, red-flag evaluation, prompt assembly, and response generation must all cooperate inside a trust-sensitive latency envelope.
- **State Orchestration:** maintaining consistency across Telegram session flow, memory continuity, premium access, and crisis branching.
- **Idempotency and Reliability:** duplicate Telegram updates, payment callback retries, and async job failures must not corrupt user state.
- **Observability Without Surveillance:** operators need visibility into failures, alerts, and system health without routine access to session content.
- **Monetization Integrity:** premium gating must preserve continuity and trust rather than disrupt the core reflective experience.
- **Telegram Runtime Constraints:** formatting, chunking, typing indicators, sparse inline controls, and client-specific behavior all shape implementation.
- **Asynchronous Re-entry and Fragmented Session Behavior:** users may drop, resume, switch device contexts, or return later, so the architecture must support non-linear session continuity rather than assume one uninterrupted chat session.

A final architectural implication from the UX is especially important: the quality of the first meaningful response is not only a product or prompt concern. It is an architectural responsibility, because context assembly, memory selection, safety checks, and latency directly determine whether that trust-making moment succeeds.

## Starter Template Evaluation

### Primary Technology Domain

`API/Backend` based on the project requirements and product shape.

The product is a Telegram-first conversational service with no public API surface, no user-facing web client in MVP, and no need for a full-stack starter. The architectural center is a stateful backend that handles Telegram webhooks, conversation orchestration, continuity between sessions, safety branching, billing, and operator-facing operational behavior.

### Starter Options Considered

#### Option 1: Official `fastapi/full-stack-fastapi-template`

This is the best-known official FastAPI starter and has the advantage of active maintenance and a large community.

**What it provides**
- FastAPI backend
- React frontend
- Dockerized local and production setup
- auth and user management assumptions
- broader full-stack structure

**Why it is not the best fit**
- too broad for a Telegram-only MVP;
- introduces frontend and auth assumptions the current product does not need;
- carries more platform shape than the current architecture should inherit.

This template is valuable as a reference for production hygiene, but not as the direct starting point for this project.

#### Option 2: Community modular-monolith FastAPI starters

Several community repositories demonstrate modular FastAPI structures closer to the target system shape.

**What they provide**
- modular project layout
- examples of settings, routers, and service boundaries
- useful reference patterns for structuring a monolith

**Why they are not ideal as the base repo**
- many are heavily opinionated;
- they often include early Redis, Celery, observability, or auth assumptions;
- they risk pulling MVP decisions toward infrastructure before user value is validated.

These starters are best treated as reference architectures and implementation checklists, not as a direct base to fork.

#### Option 3: Minimal FastAPI starter plus an explicit modular monolith structure

This option uses a minimal FastAPI baseline and adds a deliberate project structure owned by the product itself.

**What it provides**
- async-first FastAPI request handling;
- low initial complexity;
- complete control over module boundaries;
- clean alignment with Telegram-first backend needs;
- no inherited frontend, auth, or infrastructure assumptions.

**Why it fits**
- matches the product’s narrow MVP scope;
- keeps the architectural center on conversation, memory, safety, and billing;
- avoids platform overreach while still allowing disciplined structure from day one.

### Chosen Starter Approach

The recommended starter approach is:

- **minimal FastAPI backend foundation**
- **explicit modular monolith structure owned by the project**
- **Railway-first or Render-first managed deployment path**
- **community starter repos used only as references**

This is the strongest fit because the project needs deliberate structure more than it needs a heavy template.

### Starter Decision Rationale

This approach is preferable for several reasons:

- the MVP has no web frontend or admin panel that justifies a full-stack template;
- the product’s primary risks live in trust-sensitive request-path quality, not in missing boilerplate;
- a heavy starter would likely introduce unnecessary assumptions around auth, frontend, queues, or infrastructure;
- the team needs fast iteration on conversation quality, continuity, safety, and monetization rather than platform scaffolding.

The main architectural goal at this stage is not to inherit a broad stack. It is to start with a narrow, disciplined backend that can evolve cleanly as the product proves value.

### Deployment Baseline

The preferred deployment baseline is:

- **Railway** first choice
- **Render** as equivalent managed alternative
- **Docker VPS** only as a cost or control fallback later

This supports MVP speed and reduces operational overhead without forcing premature infrastructure decisions.

### Async and Background Work Baseline

The MVP should begin with:

- in-process async handling;
- asynchronous post-response enrichment for summaries and profile updates;
- a lightweight scheduler for later periodic jobs such as weekly insights.

This should be implemented with a clean extraction seam so background work can later move into a dedicated worker if scale or reliability needs increase.

In other words:
- in-process async is acceptable for MVP;
- it should not be treated as a permanent architecture constraint.

### Adapter Boundaries

Two early adapter boundaries should be protected from the start:

- **Telegram adapter** should remain an ingress and delivery layer, not the architectural center of the application.
- **Payment provider adapter** should remain behind a billing boundary so Telegram Stars or a future alternative like ЮKassa does not leak into the conversation core.

This keeps the system organized around domain concerns rather than around external service libraries.

### Recommended Initialization Commands

For a lightweight FastAPI-first baseline, the recommended initialization path is:

```bash
mkdir goals && cd goals
uv init --package .
uv add fastapi uvicorn[standard] pydantic-settings sqlmodel psycopg[binary] httpx apscheduler python-telegram-bot
```

If a more conventional virtualenv flow is preferred:

```bash
mkdir goals && cd goals
python -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" pydantic-settings sqlmodel "psycopg[binary]" httpx apscheduler python-telegram-bot
```

These commands are not the architecture themselves. They simply provide the thinnest acceptable foundation for the architecture selected in this workflow.

### Architectural Shape Implied by the Starter

This starter approach naturally supports a modular monolith organized around product domains such as:

- `bot/`
- `conversation/`
- `memory/`
- `safety/`
- `billing/`
- `ops/`
- `shared/`

This structure keeps the architectural center on the product’s actual complexity multipliers:
- reflective conversation quality;
- continuity between sessions;
- safety routing;
- access and billing state;
- operator visibility.

### Final Starter Recommendation

The starter should be:

1. **custom and minimal**
2. **FastAPI-based**
3. **modular from day one**
4. **managed-platform deployable**
5. **free of premature platform assumptions**

Heavy full-stack templates should be avoided. Community modular starters should be mined for ideas, not adopted wholesale. The architecture should begin with a minimal foundation and deliberate boundaries rather than with inherited stack complexity.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (In Progress):**
- data architecture foundation
- authentication and operator security boundary
- API validation and error-handling standards
- environment and configuration strategy
- observability and sensitive-data logging policy

**Important Decisions (Pending):**
- rate limiting and abuse controls
- API documentation exposure strategy
- deployment topology details
- future async worker extraction seam

**Deferred Decisions (Post-MVP):**
- Redis-backed caching
- dedicated worker service
- web admin surface
- vector retrieval and semantic archive
- advanced analytics pipeline

### Data Architecture

The selected data architecture foundation for MVP is:

- **PostgreSQL** as the durable system of record
- **SQLAlchemy 2** as the ORM and persistence layer
- **Pydantic v2** for request/response and boundary validation
- **Alembic** for schema migrations
- **No dedicated cache layer in MVP**

#### Rationale

This is the strongest fit for the project because it balances MVP speed with long-term architectural control.

`SQLAlchemy 2 + Pydantic v2` is preferred over `SQLModel` because the system is not a simple CRUD application. It needs explicit control over:

- sensitive user and session data models;
- summary and profile persistence;
- billing and access-state transitions;
- deletion and audit workflows;
- operator-visible but privacy-constrained operational records.

Using SQLAlchemy directly keeps the persistence layer mature and flexible without forcing the project into a simpler abstraction that may become restrictive as trust, safety, and billing flows evolve.

#### Data Validation Strategy

Validation should happen at two levels:

- **Pydantic v2 schemas** at system boundaries such as Telegram ingress, internal API surfaces, callback payloads, and operator-facing endpoints
- **domain/service validation** inside modules where business rules depend on session state, memory state, premium access, or safety context

This keeps input validation explicit while preventing business rules from leaking into transport schemas.

#### Migration Strategy

Schema evolution should use **Alembic** from day one.

This is required because the product already includes multiple durable data concerns:

- user identity and Telegram mapping
- session records
- summary and profile artifacts
- billing and access state
- deletion and audit traces
- operational alerts

Even in MVP, schema change discipline is needed.

#### Caching Strategy

MVP should start **without Redis or a distributed cache**.

The initial strategy is:

- PostgreSQL as the primary durable source
- process-local temporary in-memory optimization only where safe
- no cache dependency in the critical trust path

This avoids premature infra complexity while preserving the option to introduce external caching later if request-path pressure or scale justifies it.

### Authentication & Security

The selected MVP security model is intentionally minimal in surface area but strict in trust boundaries.

#### Identity Model

- **End-user identity:** Telegram identity only, keyed by `telegram_user_id`
- **No separate end-user login** in MVP

This preserves the product’s low-friction entry model and avoids adding account-creation complexity that would directly conflict with the UX promise.

#### Operator Authentication Model

The internal operational surface should use a **secret-protected internal operations interface** rather than a full auth platform in MVP.

This means:
- internal endpoints are protected by strong secret-based access;
- the secret must be rotation-capable;
- the internal surface must remain intentionally small;
- if hosting controls allow it, network/IP restrictions should be added as defense-in-depth.

This is acceptable only because the operator surface is tiny in MVP. It must be replaceable later without refactoring domain logic.

#### Authorization Model

MVP should use a **single operator role**.

There is no current need to split roles such as admin, analyst, or moderator. The product is not yet operating at a scale that justifies role proliferation. However, authorization logic should still be isolated so role expansion can happen later if operational complexity grows.

#### Sensitive Access Policy

The access policy should be:

- **no routine access to session content by default**
- **exceptional access only by policy**
- **all exceptional access must be auditable**

This keeps the privacy posture aligned with the product promise while preserving a legitimate path for incident investigation and critical troubleshooting.

The architecture should therefore support:
- privacy-preserving defaults;
- audit traces for deletion and exceptional access;
- operational visibility without routine transcript exposure.

#### Encryption and Secret Management

The MVP should use:

- provider-managed encryption at rest for managed services;
- encryption in transit everywhere;
- application-managed secrets via environment variables or a managed secret store;
- no secrets in source control or static configuration files.

This is sufficient for MVP so long as secret handling remains disciplined and replaceable with stronger centralized secret management later if the risk profile changes.

#### Webhook and Callback Security

Security at ingress must be explicit and enforced:

- Telegram webhook requests must use secret token verification;
- payment callbacks must use provider signature verification or equivalent authenticity checks;
- duplicate inbound events must be handled idempotently.

This is not just API hygiene. It is required to prevent state corruption in:
- message processing
- payment and access-state transitions
- safety event handling

#### Payment Security Boundary

Payment details should remain entirely provider-boundary concerns.

The application may store:
- provider event IDs
- payment/reference IDs
- access-state transitions
- timestamps

The application should **not** store raw payment instrument details locally.

#### Security Evolution Seam

This MVP security model is intentionally minimal, not permanent.

The architecture should preserve clean upgrade paths for:
- stronger internal auth later;
- richer authorization roles later;
- dedicated key management later;
- broader operational tooling later.

The domain core should not depend directly on the MVP secret-based operator auth approach.

### API & Communication Patterns

The selected communication model for MVP is an **event-ingress backend with a small internal HTTP operations surface**.

This is intentionally not an API-first product architecture. The system exists to receive external events, process domain state safely, and return user-safe outcomes through Telegram, not to expose a broad developer platform.

#### Communication Classes

The architecture should treat three communication classes as distinct:

1. **Telegram ingress events**
   - incoming user messages and Telegram-originated updates
2. **Payment provider callbacks**
   - payment success, failure, timeout, renewal, or status events
3. **Internal operational endpoints**
   - health, deletion execution, restricted operational actions, and limited internal diagnostics

Each class has different security, idempotency, and error-handling requirements and should not be treated as one generic API surface.

#### API Style

The MVP should use:

- webhook-driven external ingress
- a small set of internal HTTP endpoints
- no GraphQL
- no public API surface
- no public SDK or developer platform assumptions

This keeps the communication model aligned with the actual product instead of overbuilding for hypothetical consumers that do not exist in MVP.

#### Error Handling Model

The architecture should use a **custom domain error taxonomy** with three translation layers:

- **domain error representation**
  - used inside modules and orchestration logic
- **operational/log representation**
  - used for alerts, diagnostics, observability, and failure categorization
- **user-safe conversational representation**
  - used when the failure must be expressed in Telegram in a calm, non-technical, trust-preserving way

This separation is mandatory because raw infrastructure or backend language must never leak into emotionally sensitive user-facing flows.

#### Documentation Exposure

OpenAPI and autogenerated docs may exist for internal development and operational use, but they should not be treated as public product surfaces.

The architecture should assume:

- internal docs are acceptable during development;
- production docs exposure should be restricted or disabled by default;
- no public developer-facing documentation is required in MVP.

Health endpoints, internal docs, and restricted operational endpoints should also be treated with different exposure assumptions rather than one blanket policy.

#### Rate Limiting and Abuse Controls

Rate limiting should be framed as **abuse and stability protection at ingress**, not as a product-level quota system.

The architecture should include:

- per-user message abuse protection on Telegram ingress;
- defensive handling for repeated or malformed external events;
- separate treatment for provider callbacks, which should not be constrained by user-style message limits;
- protections that reduce cost and preserve system stability without degrading legitimate conversational use.

#### Idempotency as a State Integrity Rule

Idempotency must be treated as a first-class state integrity concern, not merely as middleware convenience.

This applies especially to:

- Telegram update processing
- payment callback processing
- deletion request execution

The goal is to ensure that duplicate or retried events do not corrupt:

- access state
- session state
- summary/profile state
- operator-visible operational records

#### Operational Signal Expectations

Failures in communication-sensitive paths should produce operator-meaningful signals rather than only raw log entries.

This includes:

- payment callback failures
- summary or post-response update failures
- red-flag alert delivery failures
- deletion workflow failures

The communication architecture should therefore connect ingress handling with observability and operational follow-up rather than treat them as separate concerns.

### Infrastructure & Deployment

The selected infrastructure model for MVP is a **single deployable FastAPI service with managed PostgreSQL**.

This matches the real needs of the product:
- fast iteration on a Telegram-first backend;
- minimal operational overhead;
- clean support for request-path quality, continuity, safety, and billing;
- a future extraction seam without premature service splitting.

#### Deployment Topology

The MVP topology should be:

- one deployable FastAPI application service
- one managed PostgreSQL instance
- no separate worker service in MVP
- no microservice split

This is the correct MVP shape because the product is operationally sensitive but not yet broad enough to justify a multi-service runtime.

#### Async Boundary

The architecture should support:

- in-request processing for trust-critical user response paths;
- asynchronous post-response enrichment for summary/profile updates where the user-facing message must not be blocked by secondary work;
- in-process scheduling only for **secondary periodic jobs** such as later weekly insight delivery.

This means:
- in-process scheduler use is acceptable for low-frequency, non-critical work;
- scheduler-based patterns should not become the permanent model for all async workloads;
- the app should preserve a clean seam for future worker extraction if scale or reliability later requires it.

#### Environment Strategy

The environment model should be:

- `local`
- `staging`
- `production`

Staging is required, not optional, because the product must safely test:

- webhook behavior
- payment callbacks
- deletion workflows
- alert routing
- environment-specific secrets and configuration

This project is too trust-sensitive to rely on local-only testing plus direct production rollout.

#### CI/CD Strategy

The recommended CI/CD baseline is **minimal GitHub Actions plus managed deployment**.

The CI/CD pipeline should include at least:

- automated tests
- linting and type checks
- migration-aware deploy gating
- controlled deployment to staging and production

The goal is not enterprise pipeline complexity. The goal is to prevent fragile deploys in a high-sensitivity product.

#### Observability Strategy

Observability should include:

- application logs
- sanitized error tracking
- health/status visibility
- tiered operator-visible alerts for trust-critical failures

The observability model should distinguish between:

- general health/status signals
- application and integration errors
- trust-critical operational failures such as:
  - payment callback failures
  - summary/profile update failures
  - red-flag alert delivery failures
  - deletion workflow failures

Observability must not rely on routine sensitive transcript logging.

#### Secrets and Configuration

The infrastructure should use:

- strict per-environment configuration
- separate secrets per environment
- rotation-capable secret management
- no shared production-like credentials between staging and production

This supports both operational clarity and the product’s privacy posture.

#### Backup and Restore Assumptions

For MVP, the system may rely on managed database backup capabilities provided by the hosting platform.

This is acceptable so long as the architecture explicitly assumes:

- backups exist at the managed platform layer;
- restore capability is a real operational concern, not an ignored assumption;
- no custom backup stack is required in MVP unless managed backup limitations later prove insufficient.

#### Scaling Strategy

The initial scaling strategy should be:

- vertical simplicity first;
- horizontal app scaling later if request volume grows;
- no early queue/worker split;
- no infrastructure decisions that prevent later extraction of background work.

The system should therefore be built with a clean boundary between:

- request-path conversation handling
- post-response enrichment
- periodic scheduled work

This keeps the MVP simple while preserving a path to evolve without rewrite.

### Decision Impact Analysis

#### Implementation Sequence

The architectural decisions imply the following implementation order:

1. establish the FastAPI modular monolith foundation and environment/config model
2. implement PostgreSQL persistence with SQLAlchemy 2, Pydantic v2, and Alembic
3. implement Telegram ingress handling with idempotent event processing
4. implement the core conversation orchestration path with bounded request-path context assembly
5. implement summary/profile persistence and post-response enrichment seam
6. implement safety routing and soft escalation behavior
7. implement billing boundary, payment callbacks, and access-state transitions
8. implement observability, alerting, deletion handling, and operator-only operational endpoints
9. add secondary periodic work such as weekly insight only after the core reflection path is stable

#### Cross-Component Dependencies

The decisions made so far create several important dependencies:

- **Conversation orchestration** depends on data modeling, request-path quality, and user-safe error translation.
- **Continuity and memory** depend on persistence discipline, transcript minimization, and post-response enrichment boundaries.
- **Safety routing** depends on ingress handling, state orchestration, operator alerting, and privacy-aware access policy.
- **Billing and premium access** depend on callback verification, idempotent state transitions, and communication-safe fallback behavior.
- **Operator visibility** depends on observability design, auditability, and strict non-routine access defaults.
- **Future scaling** depends on preserving extraction seams now rather than introducing queues or workers prematurely.

The architectural center of gravity is therefore not generic CRUD or transport. It is the trust-sensitive request path where Telegram ingress, context assembly, safety evaluation, memory use, and response generation all meet inside one latency-constrained interaction.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

The architecture identifies several areas where multiple AI agents could otherwise make incompatible implementation choices. The most important conflict areas are:

- naming of database, payload, and event fields;
- table and durable-record naming;
- project and module organization;
- boundary ownership between adapters, services, and repositories;
- internal HTTP response and error envelope format;
- event naming and async communication semantics;
- validation, retry, and logging behavior across trust-sensitive flows.

These rules exist to prevent divergence before implementation begins.

### Naming Patterns

#### Database and JSON Naming Conventions

- Use `snake_case` everywhere.
- Database tables, columns, JSON payloads, internal dictionaries, and event payloads should all use the same naming style.
- Avoid case-conversion layers unless an external integration explicitly requires them.

**Examples**
- `telegram_user_id`
- `access_state`
- `is_premium`
- `summary_generated_at`

This reduces translation overhead and prevents drift between persistence, internal logic, and internal APIs.

#### Database Table Naming

- Use plural table names.

**Examples**
- `users`
- `sessions`
- `session_summaries`
- `profile_facts`
- `payment_events`
- `deletion_requests`
- `operator_alerts`

Plural naming should remain consistent for durable entity, history, event, and audit-style tables.

#### Code and Module Naming

- Use domain/feature-oriented module naming.
- Directory and module names should reflect business capability first, not technical layer alone.

**Examples**
- `conversation/`
- `memory/`
- `billing/`
- `safety/`
- `operator/`
- `shared/`

Within Python code, functions, variables, and modules should follow standard `snake_case`.

### Structure Patterns

#### Project Organization

The project should use a **feature/domain-based modular monolith structure**.

Primary organizing principle:
- group code by business/domain capability first

Expected module areas:
- `bot/`
- `conversation/`
- `memory/`
- `billing/`
- `safety/`
- `operator/`
- `shared/`

This should take precedence over large cross-project folders such as one global `services/` or `repositories/` directory.

#### Layer Boundaries Within a Domain

Inside each domain module, internal layering may exist where needed, but it should remain subordinate to the domain boundary.

Example:
- `conversation/api.py`
- `conversation/service.py`
- `conversation/models.py`
- `conversation/repository.py`

Boundary ownership should be explicit:

- **repositories own persistence access**
- **services own business rules and orchestration inside the domain**
- **adapters own transport translation**, including Telegram/webhook/provider normalization and endpoint-layer schema mapping

This is a critical multi-agent consistency rule.

### Format Patterns

#### API Response Format

For **internal owned HTTP endpoints only**, use a wrapped response shape:

```json
{
  "data": {},
  "error": null
}
```

When an error occurs:

```json
{
  "data": null,
  "error": {
    "code": "payment_failed",
    "message": "Payment confirmation has not arrived yet.",
    "retryable": true
  }
}
```

This rule applies to internal operational endpoints and owned HTTP surfaces. It does **not** apply to Telegram chat messages or external provider payloads.

#### Error Format

Use:

```json
{
  "error": {
    "code": "string_code",
    "message": "human-readable message",
    "retryable": true
  }
}
```

Rules:
- `code` is stable and machine-usable
- `message` must be safe for its audience
- `retryable` indicates retry eligibility, not unlimited retries

Message handling should respect the already-defined translation layers:
- domain-facing meaning
- operator/internal meaning
- user-safe conversational fallback

`details` should be omitted by default in MVP unless a concrete operational need emerges.

#### Date and Time Format

- Use timezone-aware ISO 8601 strings at boundaries.
- Store all timestamps in UTC.
- Communicate all timestamps in UTC unless a future UX surface explicitly localizes them.
- Do not use ambiguous local timestamps in persistence or internal APIs.

### Communication Patterns

#### Async/Internal Event Naming

Use dotted lowercase event names.

**Examples**
- `summary.generated`
- `payment.confirmed`
- `payment.failed`
- `redflag.detected`
- `profile.updated`
- `deletion.requested`

Event names should represent **domain facts**, not handler instructions.

Correct style:
- `summary.generated`

Avoid command-style naming:
- `generate.summary`

#### Event Payload Structure

Event payloads should:
- use `snake_case`
- include only the minimum necessary identifiers and state
- avoid embedding raw transcript content unless absolutely required
- be designed for internal processing, not public consumption

### Process Patterns

#### Validation Timing

- Validate transport shape at boundaries with Pydantic
- Validate business rules inside domain services
- Do not let raw provider payloads flow directly into domain logic without normalization

#### Retry Pattern

- Retries must be driven by explicit retryability rules, not blanket re-execution
- Payment callbacks, summary generation, and alert delivery should all use explicit retry-safe handling
- Retryable failures should be identifiable via error codes or event handling state
- `retryable=true` means retry may be appropriate; it does not authorize unbounded retry behavior

#### Logging Pattern

- Logs must avoid routine sensitive content
- No raw transcript logging by default
- No full prompt logging by default
- Provider callback payloads must be sanitized before logging
- Prefer structured logging with identifiers and operational states
- Use event IDs, session IDs, user IDs, and payment IDs rather than raw message bodies whenever possible

#### Operator-Facing Error Discipline

- Internal failures should produce operator-meaningful signals
- User-facing conversation must never surface raw internal error language
- Error translation must preserve trust and emotional steadiness

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
goals/
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env.example
├── .env.local
├── .env.staging
├── .env.production
├── alembic.ini
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── src/
│   └── goals/
│       ├── __init__.py
│       ├── main.py
│       ├── app.py
│       ├── lifecycle.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py
│       │   ├── logging.py
│       │   └── security.py
│       ├── shared/
│       │   ├── __init__.py
│       │   ├── db/
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── session.py
│       │   │   └── types.py
│       │   ├── errors/
│       │   │   ├── __init__.py
│       │   │   ├── domain.py
│       │   │   ├── transport.py
│       │   │   └── mapping.py
│       │   ├── ids.py
│       │   ├── time.py
│       │   ├── logging_utils.py
│       │   └── telemetry.py
│       ├── bot/
│       │   ├── __init__.py
│       │   ├── webhook.py
│       │   ├── telegram_client.py
│       │   ├── typing.py
│       │   ├── formatting.py
│       │   └── dto.py
│       ├── conversation/
│       │   ├── __init__.py
│       │   ├── api.py
│       │   ├── service.py
│       │   ├── orchestrator.py
│       │   ├── models.py
│       │   ├── repository.py
│       │   ├── schemas.py
│       │   ├── prompts.py
│       │   ├── components.py
│       │   └── events.py
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── service.py
│       │   ├── models.py
│       │   ├── repository.py
│       │   ├── schemas.py
│       │   ├── summarizer.py
│       │   ├── profile_builder.py
│       │   ├── recall.py
│       │   └── events.py
│       ├── safety/
│       │   ├── __init__.py
│       │   ├── service.py
│       │   ├── models.py
│       │   ├── repository.py
│       │   ├── schemas.py
│       │   ├── detector.py
│       │   ├── escalation.py
│       │   ├── crisis_links.py
│       │   └── events.py
│       ├── billing/
│       │   ├── __init__.py
│       │   ├── api.py
│       │   ├── service.py
│       │   ├── models.py
│       │   ├── repository.py
│       │   ├── schemas.py
│       │   ├── providers/
│       │   │   ├── __init__.py
│       │   │   ├── telegram_stars.py
│       │   │   └── yukassa.py
│       │   ├── access.py
│       │   └── events.py
│       ├── operator/
│       │   ├── __init__.py
│       │   ├── api.py
│       │   ├── service.py
│       │   ├── schemas.py
│       │   ├── alerts.py
│       │   ├── deletion.py
│       │   └── health.py
│       ├── jobs/
│       │   ├── __init__.py
│       │   ├── scheduler.py
│       │   ├── summary_enrichment.py
│       │   └── weekly_insights.py
│       └── llm/
│           ├── __init__.py
│           ├── client.py
│           ├── models.py
│           ├── prompt_builder.py
│           └── guardrails.py
├── tests/
│   ├── unit/
│   │   ├── conversation/
│   │   ├── memory/
│   │   ├── safety/
│   │   ├── billing/
│   │   ├── operator/
│   │   └── llm/
│   ├── integration/
│   │   ├── bot/
│   │   ├── webhooks/
│   │   ├── payments/
│   │   ├── memory/
│   │   └── deletion/
│   ├── e2e/
│   │   ├── conversation_flow/
│   │   ├── red_flag_flow/
│   │   ├── premium_boundary/
│   │   └── reentry_flow/
│   ├── fixtures/
│   ├── factories/
│   └── conftest.py
└── scripts/
    ├── run_dev.sh
    ├── run_migrations.sh
    ├── seed_dev_data.py
    └── replay_webhook_event.py
```

### Architectural Boundaries

#### Adapter Boundaries

- `bot/` handles Telegram transport only.
- `billing/providers/` handles provider-specific payment details only.
- `llm/` handles model/provider integration only.

These modules are adapters and capability infrastructure. They must not become the architectural center of the product.

#### Domain Boundaries

- `conversation/` owns reflective flow orchestration and conversation-domain operations.
- `memory/` owns summaries, profile facts, and recall logic.
- `safety/` owns red-flag detection and escalation behavior.
- `billing/` owns payment state and premium access.
- `operator/` owns the tiny internal operational surface.

These modules carry product behavior and should remain the core of the monolith.

#### Shared Boundary

- `shared/` contains only cross-cutting primitives:
  - DB session/base
  - error mapping
  - IDs, time, and logging helpers
  - telemetry helpers

No domain logic should drift into `shared/`.

### Module Role Clarifications

#### Conversation Module

Inside `conversation/`, boundary ownership should be explicit:

- `orchestrator.py` owns request-path flow coordination
- `service.py` owns conversation-domain operations
- `repository.py` owns persistence access
- `api.py` owns internal HTTP surface if needed

This prevents agents from splitting conversation logic inconsistently.

#### Jobs Module

`jobs/` is an execution shell, not a business module.

Rules:
- `jobs/*` schedules or invokes work
- domain modules perform the actual business logic
- jobs must not duplicate summary, billing, safety, or continuity logic

`weekly_insights.py` may exist in the tree as a deferred or secondary capability, but it is not phase-1 core.

#### LLM Module

`llm/` is a capability infrastructure layer, not the product brain.

It may own:
- client integration
- model configuration
- prompt-building helpers
- guardrail plumbing

It must not own:
- product policy
- safety policy
- monetization logic
- memory truth rules

Those remain in domain modules.

#### Operator Module

`operator/` must remain a tiny internal surface, not the seed of a broad backoffice platform.

It should only support:
- alerts
- deletion execution
- health/status visibility
- minimal restricted operational actions

### Requirements to Structure Mapping

- session entry and Telegram ingress → `bot/`, `conversation/`
- guided reflection and conversation loop → `conversation/`, `llm/`
- continuity between sessions → `memory/`
- red-flag detection and escalation → `safety/`
- subscription, access, and payment state → `billing/`
- deletion, alerts, health, and internal ops → `operator/`
- secondary periodic work → `jobs/`

### Integration Points

#### Internal Communication

- `bot/` never talks directly to repositories; it calls domain services or orchestrators
- domain modules communicate through explicit service/orchestrator boundaries
- `jobs/` may trigger domain services, but should not contain domain logic
- `llm/` is invoked by domain logic, not vice versa

#### External Integrations

- Telegram integration enters through `bot/`
- payment provider integrations enter through `billing/providers/`
- managed Postgres is accessed through repositories and shared DB primitives

#### Data Flow

- Telegram update → `bot/` adapter → `conversation/orchestrator.py`
- orchestrator may consult `memory/`, `safety/`, `billing/`, and `llm/`
- resulting state changes are persisted through domain repositories
- post-response enrichment is triggered through `jobs/` or async seams where appropriate

### Structure Principles

- `bot/` must never become the architectural center
- repositories own persistence, services own business rules, adapters own transport translation
- tests are organized by test type because critical behaviors cross module boundaries
- cross-module trust-sensitive flows must be visible at integration and e2e levels

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:**  
The selected architecture is internally coherent. The chosen stack — FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, PostgreSQL, and a modular monolith deployment shape — works together without obvious contradiction. The deployment model, async boundaries, ingress model, and module decomposition all align with the project’s Telegram-first, high-sensitivity backend needs.

**Pattern Consistency:**  
The implementation patterns support the architectural decisions well. Naming conventions, structure rules, response formats, event naming, retry semantics, and logging rules all reinforce the selected modular monolith approach and reduce agent-level implementation drift.

**Structure Alignment:**  
The project structure aligns with both product and technical decisions. Domain modules map cleanly to the major requirement clusters, adapter boundaries are explicit, and shared infrastructure is constrained enough to avoid becoming a dumping ground.

### Requirements Coverage Validation

**Functional Requirements Coverage:**  
All major functional requirement groups have architectural support:
- Telegram ingress and session start are supported by `bot/` and `conversation/`
- reflective flow is supported by `conversation/` and `llm/`
- continuity between sessions is supported by `memory/`
- safety escalation is supported by `safety/`
- premium access and payment state are supported by `billing/`
- deletion, alerts, and operator actions are supported by `operator/`
- deferred periodic work is supported by `jobs/`

**Non-Functional Requirements Coverage:**  
The architecture addresses the main NFRs:
- latency through bounded request-path work and async enrichment
- privacy through transcript minimization and constrained access policies
- reliability through idempotent ingress and callback handling
- observability through health, error, and operator-visible trust-critical signals
- scalability through explicit extraction seams rather than premature service splitting

### Implementation Readiness Validation

**Decision Completeness:**  
The architecture includes enough critical decisions to support implementation without major ambiguity. Core technology choices, boundaries, deployment shape, and communication patterns are all specified.

**Structure Completeness:**  
The project tree is concrete enough to guide implementation. Major modules, internal layering, and test organization are explicitly defined.

**Pattern Completeness:**  
The current consistency rules cover the most likely multi-agent conflict points: naming, structure, event semantics, response formats, retry semantics, and logging discipline.

### Gap Analysis Results

**Critical Gaps:**  
No critical blocking gaps identified.

**Important Gaps:**  
The following areas would benefit from additional detail before implementation:
- explicit initial database entity list
- request-path orchestration sequence for the hot conversational path
- sharper boundary wording between `conversation/` and `memory/`
- canonical access-state vocabulary for billing and premium handling

**Nice-to-Have Gaps:**  
The following would improve implementation smoothness but are not blockers:
- initial event catalog
- initial error-code catalog
- migration ownership rules
- future worker extraction trigger criteria

### Architecture Readiness Assessment

**Overall Status:** IMPLEMENTATION-READY

The architecture is ready to guide MVP implementation. Remaining work is refinement, not structural correction. The main residual risks are future drift in request-path orchestration, memory boundaries, and billing/access-state semantics if those areas are left implicit for too long.
