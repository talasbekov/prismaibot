---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'LLM memory architecture for Telegram bots'
research_goals: 'Выбрать стратегию памяти между сессиями для MVP Telegram-бота: session summary vs RAG vs накопительный профиль, понять что реалистично для MVP, а что лучше отложить'
user_name: 'Bratan'
date: '2026-03-09'
web_research_enabled: true
source_verification: true
workflow_completed: true
---

# Research Report: technical

**Date:** 2026-03-09
**Author:** Bratan
**Research Type:** technical

---

## Research Overview

## Technical Research Scope Confirmation

**Research Topic:** LLM memory architecture for Telegram bots
**Research Goals:** Выбрать стратегию памяти между сессиями для MVP Telegram-бота: session summary vs RAG vs накопительный профиль, понять что реалистично для MVP, а что лучше отложить

**Technical Research Scope:**

- Architecture Analysis - design patterns, frameworks, system architecture
- Implementation Approaches - development methodologies, coding patterns
- Technology Stack - languages, frameworks, tools, platforms
- Integration Patterns - APIs, protocols, interoperability
- Performance Considerations - scalability, optimization, patterns

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-03-09

---

## Technology Stack Analysis

### Programming Languages

Для темы памяти в Telegram LLM-боте реальным ядром выбора языка оказываются не "скорость языка", а зрелость экосистемы вокруг orchestration, memory management, embeddings и prompt/state handling. По текущим официальным материалам strongest-first choices для MVP — **Python** и **TypeScript/JavaScript**.

**Python** выглядит самым практичным вариантом для MVP memory architecture, потому что:
- OpenAI публикует свежие cookbook-примеры по session memory и personalization patterns;
- LlamaIndex memory APIs и примеры long-term memory сегодня особенно подробно документированы именно в Python;
- вокруг Postgres/pgvector, embeddings, cron/scheduler и data jobs Python остается самым friction-light вариантом.

**TypeScript/JavaScript** тоже жизнеспособен, особенно если весь бот и infra уже Telegram/web-first в JS-стеке:
- LangGraph memory documentation и semantic search patterns хорошо описаны в JS/TS;
- OpenAI conversation-state examples доступны и для JS.

_Popular Languages:_ Python, TypeScript/JavaScript  
_Emerging Languages:_ Go и Rust можно использовать для infra-heavy bot backends, но для memory-rich LLM MVP у них слабее ready-made ecosystem вокруг summarization/profile memory. Это inference, а не прямое утверждение из одного источника.  
_Language Evolution:_ Экосистемы смещаются от "простого сохранения чата" к stateful agent frameworks с explicit short-term + long-term memory primitives.  
_Performance Characteristics:_ Для MVP bottleneck чаще находится в model latency, retrieval round-trips и prompt size, а не в raw language performance. Поэтому выбирается язык с лучшими SDK/docs, а не fastest runtime.

_Sources:_  
- https://developers.openai.com/cookbook/examples/agents_sdk/session_memory  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization  
- https://docs.langchain.com/oss/javascript/langgraph/memory  
- https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/

### Development Frameworks and Libraries

Для memory architecture вокруг Telegram bot today наиболее полезны не generic bot frameworks, а **LLM orchestration frameworks** и **conversation-state primitives**.

**OpenAI Responses / Conversations + Agents SDK**
- OpenAI docs показывают 2 уровня state management: built-in conversation state через `conversation` / `previous_response_id`, и более высокоуровневую session memory в Agents SDK.
- Cookbook по session memory прямо противопоставляет trimming и summarization как два базовых production patterns.
- Cookbook по personalization показывает state-based long-term memory pattern: **structured profile + global notes + session notes + consolidation rules**. Для вашего кейса это особенно релевантно.

**LangGraph / LangChain**
- LangGraph явно разделяет thread-scoped short-term memory и cross-session long-term memory.
- В docs long-term memory описывается не как один паттерн, а как набор вариантов, включая continuously updated user profile и semantic search over stored memories.

**LlamaIndex**
- LlamaIndex memory model особенно полезен как reference architecture: short-term FIFO chat history + optional memory blocks (`StaticMemoryBlock`, `FactExtractionMemoryBlock`, `VectorMemoryBlock`).
- Это практически прямое техдоказательство, что production memory чаще оказывается **composite**, а не "либо summary, либо vector db".

_Major Frameworks:_ OpenAI Responses/Conversations/Agents SDK, LangGraph, LlamaIndex  
_Micro-frameworks:_ собственная lightweight orchestration поверх OpenAI API + Postgres часто реалистичнее для MVP, чем full agent framework  
_Evolution Trends:_ рынок идет к explicit state management, memory policies и layered memory  
_Ecosystem Maturity:_ summary/profile memory patterns сегодня лучше документированы и operationally simpler, чем full semantic memory for every conversation

_Sources:_  
- https://developers.openai.com/api/docs/guides/conversation-state  
- https://developers.openai.com/cookbook/examples/agents_sdk/session_memory  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization  
- https://docs.langchain.com/oss/javascript/langgraph/memory  
- https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/

### Database and Storage Technologies

Для этого use case storage layer логично разделить на 3 уровня:

1. **Session transcript / summaries store**  
2. **Durable profile store**  
3. **Optional semantic retrieval layer**

Для MVP strongest candidate выглядит как **PostgreSQL** или другой relational store для:
- user profile;
- session summaries;
- extracted durable traits/patterns;
- billing and bot metadata.

Для RAG/vector memory есть 2 основных пути:

**pgvector in Postgres**
- удобен, если уже есть Postgres и хочется держать app data и embeddings рядом;
- поддерживает exact search by default и ANN indexes (`HNSW`, `IVFFlat`) when scale grows;
- хорошо подходит для "single operational database" стратегии.

**Managed vector DB (например Pinecone)**
- удобен, когда retrieval становится отдельной инфраструктурной задачей;
- docs подчеркивают metadata modeling, namespaces и semantic search workflows;
- operationally adds one more moving part in MVP.

Главный practical вывод:  
для memory between sessions в Telegram MVP **vector DB не обязателен**, если основная память — это session summary + accumulated profile. Vector retrieval нужен, когда:
- история становится длинной и плохо summarize-only;
- нужно искать старые эпизоды по смыслу;
- важна cross-session recall beyond latest summaries.

_Relational Databases:_ PostgreSQL как основной truth store для users, sessions, summaries, profile facts  
_NoSQL Databases:_ не обязательны для MVP; justified позже под event streams / analytics / flexible documents  
_In-Memory Databases:_ Redis полезен для ephemeral session cache, locks, rate limits, но не обязателен как main memory store  
_Data Warehousing:_ не нужно для MVP

_Sources:_  
- https://github.com/pgvector/pgvector  
- https://docs.pinecone.io/guides/index-data/data-modeling  
- https://docs.langchain.com/langgraph-platform/semantic-search  
- https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/

### Development Tools and Platforms

Для memory-heavy Telegram bot MVP важнее всего не IDE choice, а **operational tooling for state quality**:

- structured summarization prompts;
- profile update rules;
- memory consolidation jobs;
- observability around summary drift and wrong recalls.

Из OpenAI cookbook следует важный operational lesson: summaries требуют логирования и evaluation discipline, потому что summary drift и context poisoning — реальные failure modes.  
Из personalization cookbook следует, что durable memory лучше хранить как **structured fields + curated notes**, а session notes держать отдельно и только потом продвигать в long-term state.

Отсюда для MVP полезный tool stack:
- Postgres admin/migrations;
- background job runner / scheduler for consolidation and optional weekly jobs;
- prompt/version logging;
- lightweight evals for "стало ли яснее?" и "не пришлось ли объяснять заново?".

_IDE and Editors:_ topic-specific differentiator не дают  
_Version Control:_ memory prompts и summary schemas нужно version-control как code  
_Build Systems:_ обычные app build tools, без специального memory-specific requirement  
_Testing Frameworks:_ обязательны tests на summary extraction, profile merge rules, red-flag routing и prompt injection precedence

_Sources:_  
- https://developers.openai.com/cookbook/examples/agents_sdk/session_memory  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization  
- https://docs.langchain.com/oss/python/langchain/short-term-memory

### Cloud Infrastructure and Deployment

Cloud/deployment choices для memory architecture зависят от того, где живет state:

**Built-in conversation state**
- OpenAI conversation state и chained responses упрощают multi-turn continuity;
- но product-specific long-term memory все равно остается responsibility приложения, если вам нужны persistent summaries, profiles и billing-aware segmentation.

**App-owned state**
- хранение summaries/profiles в своей БД дает полный контроль над retention, safety, migration и monetization boundaries;
- это особенно важно для психологически чувствительного продукта в Telegram.

**Vector layer deployment**
- pgvector позволяет начать без отдельного vector vendor;
- managed vector DB имеет смысл позже, если retrieval становится bottleneck или отдельным capability.

_Major Cloud Providers:_ topic-agnostic; для MVP критичнее managed Postgres + bot hosting + scheduler than specific hyperscaler  
_Container Technologies:_ Docker enough; Kubernetes не нужен для раннего memory MVP  
_Serverless Platforms:_ пригодны для webhook bot handlers, но state and scheduled jobs чаще удобнее вести через обычный app service + DB  
_CDN and Edge Computing:_ не ключевой фактор для this topic

_Sources:_  
- https://developers.openai.com/api/docs/guides/conversation-state  
- https://platform.openai.com/docs/models/how-we-use-your-data  
- https://github.com/pgvector/pgvector

### Technology Adoption Trends

По текущим официальным материалам наиболее зрелая conceptual direction выглядит так:

1. **Short-term session memory** через bounded chat history, trimming или summarization  
2. **Long-term structured profile / notes** для durable facts and preferences  
3. **Selective semantic retrieval** как later-stage enhancement, а не default MVP requirement

Это видно сразу у нескольких источников:
- OpenAI cookbook по session memory рекомендует trimming/summarization для управления длинным контекстом;
- OpenAI cookbook по personalization предлагает long-term state как `profile + global notes + session notes`;
- LangGraph docs прямо выделяют profile-style semantic memory как один из нормальных long-term patterns;
- LlamaIndex показывает composite memory из static facts, extracted facts и vector memory blocks.

_Migration Patterns:_ от raw chat history к layered memory  
_Emerging Technologies:_ agent frameworks со встроенной memory policy, semantic stores over app state  
_Legacy Technology:_ "просто хранить все сообщения и каждый раз скармливать их модели" быстро упирается в cost/noise/latency  
_Community Trends:_ всё больше систем разделяют durable facts, session notes и retrievable archives вместо одной giant memory bucket

**Preliminary Recommendation for this MVP**

_High confidence:_  
Для Telegram MVP оптимальный старт — **summary per session + accumulated profile**:
- после каждой сессии сохранять короткий structured summary;
- выделять durable facts/patterns в profile/notes store;
- на следующей сессии инжектить only relevant summary/profile slices в system context.

_Medium confidence:_  
RAG/vector memory стоит отложить до v2, когда появится один из признаков:
- summaries перестают держать continuity;
- нужно доставать старые похожие эпизоды по смыслу;
- пользователи ожидают "помнишь тот случай 2 месяца назад?"

_Low confidence / not recommended for MVP:_  
Полный semantic memory layer с отдельной vector DB как primary memory strategy. Для раннего Telegram subscription bot это чаще преждевременная сложность.

_Sources:_  
- https://developers.openai.com/cookbook/examples/agents_sdk/session_memory  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization  
- https://docs.langchain.com/oss/javascript/langgraph/memory  
- https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/  
- https://github.com/pgvector/pgvector

## Integration Patterns Analysis

### API Design Patterns

Для Telegram bot с memory между сессиями базовый integration pattern почти всегда выглядит как:

1. **Telegram update arrives**  
2. **Bot backend resolves user/session context**  
3. **Backend loads short-term thread state + long-term memory slices**  
4. **LLM call runs with assembled context**  
5. **Result is sent back to Telegram**  
6. **Session summary/profile updates are persisted**

Для MVP здесь strongest fit дает **simple webhook-driven REST integration**, а не GraphQL/gRPC-heavy architecture.

**RESTful APIs**
- Telegram Bot API работает поверх HTTPS requests; webhook delivery naturally fits REST-style backend handlers.
- App-owned internal API тоже проще держать REST-like: `/telegram/webhook`, `/sessions/{id}`, `/users/{id}/profile`, `/summaries`.

**GraphQL APIs**
- Для этого кейса GraphQL почти не дает MVP advantage. It adds API surface complexity without solving the core memory problem.

**RPC / gRPC**
- Могут пригодиться позже для internal service boundaries, но для single-service MVP это лишнее.

**Webhook Patterns**
- Telegram docs описывают 2 ответа на update: либо bot делает отдельный POST к Bot API, либо отвечает JSON payload directly to webhook response.
- Для memory-sensitive product practical choice чаще: принять webhook, быстро ack/update, а дальнейшую LLM работу делать в app flow with explicit state handling.

_RESTful APIs:_ лучший fit для MVP bot backend  
_GraphQL APIs:_ низкий приоритет, weak fit  
_RPC and gRPC:_ premature for MVP  
_Webhook Patterns:_ core external integration pattern

_Sources:_  
- https://core.telegram.org/bots/faq  
- https://developers.openai.com/api/docs/guides/conversation-state

### Communication Protocols

Ключевые протоколы в этой архитектуре несложны, но роли у них разные:

- **HTTPS/Webhooks** между Telegram и bot backend  
- **HTTPS API calls** между backend и OpenAI  
- **DB protocol / driver traffic** между backend и Postgres/Redis/store  
- **Optional scheduler/job events** для summaries and weekly jobs

**HTTP/HTTPS**
- Основной integration protocol и для Telegram Bot API, и для OpenAI API.
- Это упрощает single-service Python backend: no custom protocol stack required.

**WebSockets**
- Не обязательны для Telegram bot MVP, так как Telegram уже является messaging transport.
- Streaming response UX можно реализовать через partial message edits или typing indicators, without WebSocket infra.

**Message Queues**
- Для MVP не обязательны, но полезны, если summary generation, profile consolidation или weekly insight jobs начинают мешать request latency.
- Тогда lightweight queue/job runner может отделить user-facing response from post-processing.

**gRPC / Protobuf**
- Не дают заметного MVP выигрыша для single bot backend.

_HTTP/HTTPS Protocols:_ основной transport layer  
_WebSocket Protocols:_ не required  
_Message Queue Protocols:_ useful later for async post-processing  
_gRPC and Protocol Buffers:_ not needed for MVP

_Sources:_  
- https://core.telegram.org/bots/faq  
- https://developers.openai.com/api/docs/guides/conversation-state

### Data Formats and Standards

Для memory architecture важен не только transport format, но и **internal memory schema**.

External communication mostly uses **JSON**:
- Telegram updates приходят как JSON payloads;
- OpenAI request/response bodies тоже JSON;
- internal app APIs can remain JSON-first.

Но для продукта memory-critical важнее standardize **structured summary schema**.  
Практически useful schema для каждой сессии:
- `session_id`
- `user_id`
- `timestamp`
- `situation_summary`
- `people_involved`
- `emotions_detected`
- `cognitive_patterns`
- `suggested_next_step`
- `durable_profile_updates`
- `red_flag_status`

Такой JSON schema дает:
- deterministic prompt assembly;
- easier profile merge rules;
- later compatibility with embeddings/retrieval if needed.

**Binary formats** вроде Protobuf/MessagePack не нужны на MVP-stage.  
**CSV/flat files** irrelevant для live memory path.

_JSON and XML:_ JSON is the practical default everywhere  
_Protobuf and MessagePack:_ no clear MVP advantage  
_CSV and Flat Files:_ not relevant for runtime memory  
_Custom Data Formats:_ structured JSON summary/profile schemas are worth defining early

_Sources:_  
- https://core.telegram.org/bots/faq  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization

### System Interoperability Approaches

Для этого use case main interoperability problem не “enterprise integration”, а **how multiple memory scopes coexist safely**:

- Telegram chat/thread context
- application session context
- long-term user profile
- optional retrievable archive

Наиболее полезный interoperability pattern today:

**Thread-scoped short-term memory + user-scoped long-term memory**
- LangGraph docs прямо показывают `thread_id` for conversation state/checkpoints и separate namespace using `user_id` for long-term store.
- Это очень близко к Telegram reality: один пользователь может иметь много отдельных conversation turns over time, but one durable relationship with the bot.

Для вашего MVP это переводится так:
- `telegram_user_id` = primary durable identity
- `session_id` = current acute conversation
- `summary store` = session-scoped artifacts
- `profile store` = user-scoped durable memory

**Point-to-point integration**
- Telegram -> bot service -> DB/OpenAI is enough for MVP.

**API gateway / service mesh / ESB**
- Не нужны на старте. Они не помогают core memory quality.

_Point-to-Point Integration:_ best MVP pattern  
_API Gateway Patterns:_ optional later if platform expands  
_Service Mesh:_ no MVP need  
_Enterprise Service Bus:_ irrelevant

_Sources:_  
- https://docs.langchain.com/oss/python/langgraph/persistence  
- https://docs.langchain.com/oss/python/langgraph/add-memory  
- https://developers.openai.com/api/docs/guides/conversation-state

### Microservices Integration Patterns

Самая важная decision point здесь: **single service vs split memory/LLM services**.

Для MVP strongest recommendation:

**Single service application**
- Telegram webhook handler
- prompt assembly
- OpenAI call
- summary/profile persistence
- paywall checks

в одном Python service.

Почему:
- меньше network boundaries;
- проще отлаживать memory errors;
- проще обеспечить consistent safety behavior;
- меньше ops overhead.

**When to split later**
- отдельный async worker для summary/profile consolidation;
- отдельный memory service only if retrieval logic becomes complex;
- отдельный billing service only if payments and entitlements outgrow app logic.

Patterns вроде service discovery, saga, circuit breaker useful later, but mostly unnecessary at MVP scale.

_API Gateway Pattern:_ unnecessary for first version  
_Service Discovery:_ unnecessary for single service  
_Circuit Breaker Pattern:_ useful conceptually for provider failures, but can be implemented inside app without microservices  
_Saga Pattern:_ irrelevant for MVP

_Sources:_  
- https://docs.langchain.com/oss/python/langgraph/persistence  
- https://docs.langchain.com/langsmith/custom-checkpointer

### Event-Driven Integration

Хотя full event-driven architecture не нужна, event-style processing полезен в 3 местах:

1. **After session completed**  
   Generate structured summary  
   Extract durable profile updates  
   Save summary/profile delta

2. **Scheduled weekly insight**  
   Aggregate recent summaries  
   Detect repeated themes  
   Produce short weekly message

3. **Safety escalation events**  
   Mark red-flag session  
   route special response policy  
   optionally suppress unsafe memory promotion

Это suggests lightweight async/event pattern:
- synchronous path for user reply
- asynchronous post-processing for memory enrichment

**Publish-subscribe / message broker**
- not required initially;
- cron/jobs/background worker enough.

**Event sourcing**
- overkill for MVP. Raw session log + summaries + profile deltas already give enough traceability.

**CQRS**
- also overkill for early stage.

_Publish-Subscribe Patterns:_ optional later  
_Event Sourcing:_ too heavy for MVP  
_Message Broker Patterns:_ useful only after async workload grows  
_CQRS Patterns:_ no MVP need

_Sources:_  
- https://docs.langchain.com/langgraph-platform/configure-ttl  
- https://developers.openai.com/cookbook/examples/agents_sdk/session_memory  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization

### Integration Security Patterns

Так как продукт психологически чувствительный, integration security must not be an afterthought.

Critical patterns:

- **Bot webhook authenticity / secret handling**
- **User identity binding** to `telegram_user_id`
- **Separation of thread/session/profile scopes**
- **Encryption at rest and in transit**
- **Least-privilege access** to summaries and profiles

**OAuth 2.0 / JWT**
- Не основной вопрос на MVP, если primary channel is Telegram auth context.
- Internal admin surfaces later may need standard auth.

**API keys**
- critical for OpenAI and any third-party services.

**Sensitive memory promotion rules**
- not every session detail should become durable memory;
- red-flag or high-risk sessions may need different retention and promotion behavior.

Это последний пункт особенно важен именно для вашего продукта: memory integration must include **policy boundary**, not just storage boundary.

_OAuth 2.0 and JWT:_ low initial relevance for core user path  
_API Key Management:_ essential  
_Mutual TLS:_ unnecessary for MVP  
_Data Encryption:_ essential for DB, provider traffic, backups, logs

_Sources:_  
- https://platform.openai.com/docs/models/how-we-use-your-data  
- https://core.telegram.org/bots/faq  
- https://docs.langchain.com/oss/python/langgraph/persistence

**Preliminary Integration Recommendation for this MVP**

_High confidence:_  
Use a **single Python webhook service** with:
- Telegram webhook ingress
- application-owned `telegram_user_id` + `session_id` model
- synchronous LLM call with assembled context
- asynchronous summary/profile persistence after session milestones

Memory assembly should follow:
- current session slice
- latest relevant session summary
- compact user profile / durable facts
- optional future retrieval hook

_Medium confidence:_  
Weekly insight can be integrated as a scheduled async job, but should not block core acute-conflict MVP if scope becomes tight.

_Low confidence / not recommended for MVP:_  
Microservices-heavy design, external event bus, or vector-first retrieval in the main request path.

_Sources:_  
- https://core.telegram.org/bots/faq  
- https://developers.openai.com/api/docs/guides/conversation-state  
- https://docs.langchain.com/oss/python/langgraph/persistence  
- https://docs.langchain.com/oss/python/langgraph/add-memory  
- https://docs.langchain.com/langgraph-platform/semantic-search

## Architectural Patterns and Design

### System Architecture Patterns

Для темы `LLM memory architecture for Telegram bots` strongest architectural pattern for MVP — **modular monolith / single service with external stateful backing services**.

Почему это соответствует current best practices:
- Twelve-Factor рекомендует stateless processes и вынос любого durable state в backing services;
- LangGraph persistence docs разделяют process execution от persisted thread/store state;
- OpenAI personalization examples предполагают explicit app-owned durable memory, а не "магическую память" внутри runtime.

Для вашего кейса оптимальная форма выглядит так:

**Single Python service**
- Telegram webhook ingress
- conversation orchestration
- prompt assembly
- OpenAI call
- summary/profile persistence
- entitlement checks

**Backing services**
- Postgres for users, sessions, summaries, profiles
- optional Redis for transient cache / locks / rate limits
- optional job runner for summaries / weekly jobs

Это лучше микросервисов на старте, потому что memory logic и safety logic сильно связаны и их проще развивать в одном codebase.

_Sources:_  
- https://12factor.net/processes  
- https://12factor.net/backing-services  
- https://docs.langchain.com/oss/python/langgraph/persistence  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization

### Design Principles and Best Practices

Для memory architecture здесь важнее всего 5 design principles:

1. **State scopes must be explicit**  
   Нужно явно отделить:
   - request-local state
   - session/thread state
   - durable user profile
   - optional retrievable archive

2. **Memory promotion must be selective**  
   Не каждое сообщение должно попадать в long-term memory. Durable memory должен формироваться через summary/profile extraction rules.

3. **Prompt assembly should be deterministic**  
   Вместо "скинуть все, что есть" лучше строить fixed context layers:
   - policy/system instructions
   - current user turn
   - current session slice
   - latest summary
   - compact durable profile

4. **Unsafe or sensitive material needs retention policy**  
   Для red-flag sessions promotion в durable profile должен быть ограничен или отдельно размечен.

5. **Memory quality is an architectural concern**  
   Нужно проектировать evaluation hooks, а не только storage schema.

OpenAI personalization cookbook особенно хорошо подтверждает pattern `profile + global notes + session notes`, а LangGraph memory docs подтверждают separation between thread memory and cross-thread store.

_Sources:_  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization  
- https://docs.langchain.com/oss/python/langgraph/add-memory  
- https://docs.langchain.com/oss/python/langgraph/persistence

### Scalability and Performance Patterns

Скалирование этого продукта чаще упирается не в CPU приложения, а в:
- model latency;
- DB round-trips for memory assembly;
- summary generation overhead;
- prompt bloat.

Поэтому правильные patterns для MVP:

**Horizontal scaling for stateless app processes**
- app processes should remain replaceable/stateless;
- all durable memory in Postgres/attached services.

**Bounded context injection**
- не тянуть полный transcript every time;
- использовать compressed summaries + compact profile.

**Async post-processing**
- summary generation и profile merge можно выносить после ответа пользователю, если latency становится заметной.

**Deferred vector retrieval**
- не ставить semantic retrieval в main request path до доказанной необходимости.

**Graceful degradation**
- если async summary failed, user conversation still should succeed.

_Sources:_  
- https://12factor.net/processes  
- https://docs.langchain.com/oss/python/langgraph/persistence  
- https://developers.openai.com/cookbook/examples/agents_sdk/session_memory

### Integration and Communication Patterns

Архитектурно наиболее clean communication pattern:

- Telegram -> webhook handler
- handler -> memory assembler
- assembler -> OpenAI API
- result -> user
- post-session pipeline -> summary/profile persistence

Это по сути layered request architecture with async tail work.

Если later-stage decomposition понадобится, natural seams будут такими:
- bot ingress layer
- memory service / persistence module
- async enrichment worker
- payments/entitlements module

Но на MVP их лучше держать как internal modules, а не network-separated services.

_Sources:_  
- https://core.telegram.org/bots/faq  
- https://12factor.net/backing-services  
- https://developers.openai.com/api/docs/guides/conversation-state

### Security Architecture Patterns

Для вашего продукта security architecture должна исходить из того, что summaries и profiles — это чувствительные психологические данные.

Архитектурные требования:
- data in transit encrypted by default through HTTPS;
- data at rest in DB and backups should be encrypted;
- secrets/config must live in environment/config system, not code;
- access to profile/summaries should follow least privilege;
- logs must avoid leaking full sensitive memory payloads where possible.

Отдельный architectural principle:
**memory retention boundary is part of security architecture**.  
То есть вопрос "что мы храним надолго" — это не только product design, но и security decision.

_Sources:_  
- https://12factor.net/config  
- https://platform.openai.com/docs/models/how-we-use-your-data  
- https://12factor.net/processes

### Data Architecture Patterns

Наиболее practical data architecture для MVP:

**Core relational model**
- `users`
- `sessions`
- `session_messages` or condensed transcript records
- `session_summaries`
- `user_profile_facts`
- `profile_versions` or audit trail
- `billing_entitlements`

**Summary-centric durable state**
- every completed session produces one structured summary
- selected summary fields promote into durable profile store

**Profile as curated memory**
- profile should not be a free-form dump;
- better as typed facts/patterns/people/ongoing themes.

**Archive strategy**
- full transcripts can exist for trace/debug/compliance reasons if product policy allows;
- but runtime memory should mostly operate on summaries and curated profile.

**Vector-ready but not vector-first**
- schema can later attach embeddings to summaries/profile facts;
- but MVP should not depend on them.

Этот pattern хорошо соответствует и OpenAI personalization model, и LangGraph’s separate thread/store concepts.

_Sources:_  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization  
- https://docs.langchain.com/oss/python/langgraph/persistence  
- https://docs.langchain.com/oss/python/langgraph/add-memory  
- https://github.com/pgvector/pgvector

### Deployment and Operations Architecture

Операционно на MVP достаточно:

- one deployable Python bot service
- managed Postgres
- optional Redis
- cron / scheduler / worker for weekly jobs and background consolidation
- structured logs and prompt/version observability

Twelve-Factor patterns здесь особенно уместны:
- config in environment
- processes stateless
- backing services as attached resources
- logs as event stream

Kubernetes, event bus, CQRS/event sourcing, service mesh и full microservice decomposition сейчас не дают proportional value. AWS guidance по microservice decomposition и CQRS/event sourcing показывает, что эти patterns полезны mainly when independent services and complex distributed transactions already exist. For this MVP that is not the case.

_Sources:_  
- https://12factor.net/  
- https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/decompose-monoliths-into-microservices-by-using-cqrs-and-event-sourcing.html  
- https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/welcome.html  
- https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/implement-the-serverless-saga-pattern-by-using-aws-step-functions.html

**Architectural Recommendation for this MVP**

_High confidence:_  
Adopt a **modular monolith architecture**:
- one Python bot application
- managed Postgres as durable memory backbone
- explicit separation of session summaries and durable profile memory
- async enrichment pipeline after user-facing response
- no vector DB in the critical path

_Medium confidence:_  
Add Redis and a lightweight worker only if latency, locks, or scheduled jobs start adding operational friction.

_Low confidence / not recommended for MVP:_  
Microservices, CQRS/event sourcing, event bus orchestration, or vector-first architecture as baseline.

_Sources:_  
- https://12factor.net/processes  
- https://12factor.net/backing-services  
- https://12factor.net/config  
- https://docs.langchain.com/oss/python/langgraph/persistence  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization

## Implementation Approaches and Technology Adoption

### Technology Adoption Strategies

Для этого проекта правильная adoption strategy — **phased adoption**, а не big-bang architecture.

Практически это означает:

**Phase 1: MVP memory**
- session transcript or condensed turn history
- structured summary at session close
- durable profile updates
- prompt assembly from latest summary + compact profile

**Phase 2: retention enrichment**
- weekly insight
- profile quality improvements
- better summary extraction and evaluation

**Phase 3: advanced recall**
- embeddings for summaries/profile facts
- selective semantic retrieval
- deeper cross-session recall

Это соответствует общему engineering guidance: сначала доказать core value with minimal moving parts, затем усложнять architecture only when observed usage justifies it.

_Sources:_  
- https://12factor.net/build-release-run  
- https://developers.openai.com/cookbook/examples/agents_sdk/session_memory  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization

### Development Workflows and Tooling

Для Python MVP хороший workflow должен быть boring and strict:

- repo with clear module boundaries (`bot`, `memory`, `llm`, `billing`, `jobs`)
- Git-based code review
- CI on every push / PR
- migrations for schema changes
- prompt and summary-schema versioning

GitHub Docs рекомендуют стандартный CI workflow for Python through GitHub Actions, включая dependency install, tests and workflow templates. Для MVP этого достаточно, если добавить:
- linting;
- unit/integration tests;
- secret scanning / dependency updates later.

Если бот строится на `asyncio`, Python docs напоминают про типичные pitfalls:
- forgotten awaits;
- blocking logging handlers;
- slow callbacks;
- misuse across threads.

Это важно, потому что Telegram bot + LLM calls + async jobs very easily drift into fragile async code without discipline.

_Sources:_  
- https://docs.github.com/actions/automating-builds-and-tests/about-continuous-integration  
- https://docs.github.com/actions/guides/building-and-testing-python  
- https://docs.python.org/3.11/library/asyncio-dev.html

### Testing and Quality Assurance

Для этого продукта тестирование должно быть не только around code correctness, but around **memory correctness**.

Нужны как минимум 4 test layers:

1. **Unit tests**
- summary schema validation
- profile merge logic
- paywall gating
- red-flag routing

2. **Prompt/policy tests**
- current session summary included correctly
- irrelevant stale memory excluded
- unsafe memory not promoted by mistake

3. **Integration tests**
- Telegram update -> context assembly -> OpenAI call wrapper -> persistence
- session completion -> summary generation -> profile update

4. **Human evaluation / lightweight rubric**
- “стало ли яснее?”
- “не пришлось ли объяснять заново?”
- “ответ был бережный и неосуждающий?”

Для такого продукта testing pyramid должна быть смещена toward deterministic business logic plus small curated eval sets for memory quality.

_Sources:_  
- https://docs.github.com/actions/automating-builds-and-tests/about-continuous-integration  
- https://developers.openai.com/cookbook/examples/agents_sdk/session_memory  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization

### Deployment and Operations Practices

Операционный baseline для MVP:

- one deployable Python service
- managed Postgres
- environment-based config
- structured logs
- health checks
- graceful shutdown
- periodic jobs for summary/weekly tasks

Twelve-Factor strongly supports this operating model:
- config in env vars
- logs as event streams
- short startup / graceful shutdown
- clear build/release/run separation

Если используется async worker or internal queue, Python `asyncio.Queue` and scheduled tasks can cover early-stage async work, but for production robustness many teams later move to explicit job runners. Для MVP можно начать проще, если нагрузка невысокая.

_Sources:_  
- https://12factor.net/config  
- https://12factor.net/logs  
- https://12factor.net/disposability  
- https://12factor.net/build-release-run  
- https://docs.python.org/3/library/asyncio-queue.html

### Team Organization and Skills

Минимально достаточная team/skill shape for this MVP:

- **1 strong Python backend engineer** with async/webhook/Postgres competence
- **1 product-minded engineer or PM/founder** who can define memory schemas, prompt rules and user-facing behavior
- **optional part-time QA / evaluator** for memory quality and safety edge cases

Самый дефицитный навык здесь не "ML research", а:
- prompt/state discipline
- schema design for summaries and profile facts
- product judgment on what deserves durable memory

If the team is small, avoid architecture requiring dedicated infra, MLOps or distributed systems skills.

_Sources:_  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization  
- https://docs.python.org/3.11/library/asyncio-dev.html

### Cost Optimization and Resource Management

Cost strategy для этого проекта строится вокруг 3 рычагов:

1. **Prompt compression**
- use summaries instead of raw transcript replay
- keep profile compact and typed

2. **Asynchronous enrichment**
- not every user-facing response needs immediate heavy summarization

3. **Single operational database**
- Postgres first
- vector layer only when clearly needed

Самые вероятные cost leaks:
- слишком длинный context on every turn
- storing everything as runtime memory
- introducing vector infra before it creates measurable value

_Sources:_  
- https://developers.openai.com/cookbook/examples/agents_sdk/session_memory  
- https://github.com/pgvector/pgvector  
- https://12factor.net/backing-services

### Risk Assessment and Mitigation

Главные implementation risks:

**1. Summary drift**
- summary искажает разговор или теряет важные нюансы
- mitigation: summary schema, review samples, regression evals

**2. Over-promotion to durable profile**
- в профиль попадает то, что не должно храниться долго
- mitigation: explicit promotion rules, red-flag exceptions, typed facts only

**3. Context bloat**
- profile/summaries растут и ухудшают response quality
- mitigation: compact schema, capped fields, periodic pruning

**4. Async fragility**
- background tasks fail silently
- mitigation: observability, retry policy, idempotent jobs

**5. Safety-memory coupling**
- опасный контент попадает в reusable memory
- mitigation: memory retention policy as part of safety architecture

_Sources:_  
- https://docs.python.org/3.11/library/asyncio-dev.html  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization  
- https://developers.openai.com/cookbook/examples/agents_sdk/session_memory

## Technical Research Recommendations

### Implementation Roadmap

**Stage 1: Core session flow**
- Telegram webhook bot
- one Python service
- session loop with fast/deep mode
- Postgres schema for users/sessions/summaries/profile facts

**Stage 2: Memory quality**
- summary generation after session
- durable profile update rules
- prompt assembly with latest summary + profile slices
- post-session clarity and memory continuity measurement

**Stage 3: Retention and ops**
- optional weekly insight
- CI/CD hardening
- async job reliability
- observability for summary/profile failures

**Stage 4: v2 triggers**
- only after proven need: embeddings, pgvector, selective semantic retrieval

### Technology Stack Recommendations

- **Language:** Python
- **App shape:** modular monolith
- **Transport:** Telegram webhooks over HTTPS
- **LLM provider path:** OpenAI API with explicit app-owned memory
- **Primary storage:** PostgreSQL
- **Optional support infra:** Redis only if locking/cache/job pressure emerges
- **Memory strategy:** session summary + accumulated typed profile
- **Deferred capabilities:** vector retrieval, microservices, event bus

### Skill Development Requirements

Команде нужно особенно хорошо освоить:
- async Python discipline
- schema-first memory design
- prompt versioning and evaluation
- safety-aware memory promotion
- SQL/Postgres basics for durable state

### Success Metrics and KPIs

Для implementation layer нужно отслеживать не только product KPIs, но и technical health metrics:

- summary generation success rate
- profile update success rate
- average memory assembly latency
- percentage of sessions using stale/empty memory
- failed async job rate
- cost per completed session

Эти технические метрики должны идти рядом с product metrics вроде activation, D7 return, paid conversion and churn.

_Sources:_  
- https://docs.github.com/actions/guides/building-and-testing-python  
- https://docs.python.org/3.11/library/asyncio-dev.html  
- https://12factor.net/build-release-run  
- https://12factor.net/disposability

---

# Memory by Design: Comprehensive LLM Memory Architecture for Telegram Bots Technical Research

## Executive Summary

This technical research examined how to implement cross-session memory for a Telegram-based LLM product, with a specific goal: determine whether an MVP should rely on session summaries, retrieval-augmented generation (RAG), an accumulated user profile, or some combination of the three.

Across current primary sources from OpenAI, LangGraph/LangChain, LlamaIndex, and vector storage documentation, the most consistent conclusion is that modern memory architectures are layered rather than singular. The strongest MVP approach is not vector-first memory, but a pragmatic combination of structured session summaries and a curated long-term user profile. This yields continuity across conversations while avoiding the operational complexity, retrieval noise, and architectural overreach of a full semantic memory stack.

For a Telegram MVP focused on acute emotional conflict and continuity between sessions, the recommended architecture is a Python-based modular monolith with Telegram webhook ingress, OpenAI API calls, PostgreSQL as the durable memory backbone, and asynchronous summary/profile enrichment after user-facing responses. RAG and vector retrieval should be treated as an extension point triggered by observed need, not as a baseline requirement.

**Key Technical Findings:**

- The most practical MVP memory pattern is `session summary + accumulated profile`, not full RAG.
- Durable memory should be selectively promoted, not copied wholesale from transcripts.
- Memory scope separation is essential: request state, session state, profile memory, optional archive.
- PostgreSQL is sufficient for MVP durable memory; vector retrieval is optional later.
- A single Python service is the strongest launch architecture for this problem.

**Technical Recommendations:**

- Build MVP memory around structured session summaries and typed profile facts.
- Use Python as the primary backend language for fastest execution and lowest AI ecosystem friction.
- Keep memory logic application-owned, not provider-owned.
- Defer vector DB and semantic retrieval until continuity quality or recall depth actually demands it.
- Treat memory retention and promotion policy as part of security architecture.

## Table of Contents

1. Technical Research Introduction and Methodology
2. LLM Memory Architecture for Telegram Bots Technical Landscape and Architecture Analysis
3. Implementation Approaches and Best Practices
4. Technology Stack Evolution and Current Trends
5. Integration and Interoperability Patterns
6. Performance and Scalability Analysis
7. Security and Compliance Considerations
8. Strategic Technical Recommendations
9. Implementation Roadmap and Risk Assessment
10. Future Technical Outlook and Innovation Opportunities
11. Technical Research Methodology and Source Verification
12. Technical Appendices and Reference Materials

## 1. Technical Research Introduction and Methodology

### Technical Research Significance

Memory architecture is one of the defining technical decisions in any LLM product that expects users to return over time. In the case of a Telegram bot intended to help users unpack emotionally charged situations, memory is not a cosmetic enhancement. It is part of the product promise: the user should not need to explain their context from scratch every time, and the system should become more useful as it accumulates relevant knowledge.

This makes the choice of memory strategy strategically significant. A poor choice can create latency, noise, unsafe retention, and unnecessary infrastructure cost. A strong choice can create continuity, clarity, and monetizable product value with relatively simple technical building blocks.

_Source:_  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization  
- https://developers.openai.com/cookbook/examples/agents_sdk/session_memory

### Technical Research Methodology

This research used current public technical sources with emphasis on primary documentation and authoritative implementation guidance.

- **Technical Scope**: memory models, architecture patterns, integration patterns, implementation workflows, storage choices, and operational trade-offs
- **Primary Sources**: OpenAI documentation and Cookbook, LangGraph/LangChain documentation, LlamaIndex documentation, pgvector documentation, Telegram Bot API documentation, Twelve-Factor App guidance
- **Analysis Framework**: evaluate each option by MVP fit, implementation complexity, operational risk, scalability path, and alignment with product goals
- **Time Period**: current documentation and platform guidance as available in March 2026
- **Technical Depth**: architecture-level and implementation-level, with specific MVP recommendations

### Technical Research Goals and Objectives

**Original Technical Goals:** выбрать стратегию памяти между сессиями для MVP Telegram-бота: session summary vs RAG vs накопительный профиль, понять что реалистично для MVP, а что лучше отложить.

**Achieved Technical Objectives:**

- Identified the strongest MVP memory architecture pattern.
- Clarified when RAG/vector memory becomes justified.
- Defined the most realistic application shape for Telegram-based LLM memory.
- Produced an implementation roadmap that minimizes complexity while preserving product continuity.

## 2. LLM Memory Architecture for Telegram Bots Technical Landscape and Architecture Analysis

### Current Technical Architecture Patterns

The current technical landscape strongly favors layered memory systems over monolithic memory designs. The dominant architectural model separates:

- short-term/session memory,
- durable user profile memory,
- optional semantic retrieval memory.

OpenAI session memory guidance emphasizes trimming and summarization for controlling context growth. OpenAI personalization guidance recommends persistent structured profile-style state such as profile fields, global notes, and session notes. LangGraph and LlamaIndex both reinforce the same direction: cross-session memory should be explicit, scoped, and composable.

_Architectural Trade-offs:_
- Summary-only memory is simple and cheap but weaker at recalling distant detail.
- Profile-only memory is durable but can become too abstract if not grounded by session history.
- RAG/vector memory is powerful for semantic recall but adds infrastructure and retrieval complexity.

_Source:_  
- https://developers.openai.com/cookbook/examples/agents_sdk/session_memory  
- https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization  
- https://docs.langchain.com/oss/python/langgraph/add-memory  
- https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/

### System Design Principles and Best Practices

The strongest design principles for this domain are:

- explicit memory scopes,
- selective promotion into durable memory,
- deterministic prompt assembly,
- compact typed memory structures,
- safety-aware retention rules.

The system should not treat the entire transcript as reusable memory. Instead, each session should produce a structured summary and a small set of profile updates, and only these curated artifacts should influence future sessions.

## 3. Implementation Approaches and Best Practices

### Current Implementation Methodologies

The recommended implementation model is phased:

**Phase 1**
- Telegram bot core loop
- session persistence
- per-session summaries
- compact user profile

**Phase 2**
- profile quality refinement
- continuity metrics
- optional weekly insight

**Phase 3**
- embeddings over summaries/profile facts
- selective semantic retrieval if needed

This phased strategy reduces technical risk while preserving upgrade paths.

### Implementation Framework and Tooling

The best practical implementation baseline is:

- Python backend
- Postgres as durable store
- REST/webhook handling
- prompt/version tracking
- CI for tests and schema validation
- background job runner for async memory enrichment if needed

## 4. Technology Stack Evolution and Current Trends

### Current Technology Stack Landscape

Python and TypeScript are the strongest language ecosystems for this problem. Python has the cleanest path for an MVP due to stronger reference material and mature AI tooling around summarization, state handling, and data jobs.

PostgreSQL is the strongest durable store for MVP. It supports structured app data immediately and can later evolve into vector-capable storage through pgvector.

### Technology Adoption Patterns

The adoption trend is clear: systems are moving away from replaying raw history and toward layered memory with summary compression, curated profile memory, and selective retrieval.

## 5. Integration and Interoperability Patterns

### Current Integration Approaches

For a Telegram bot, the cleanest pattern is:

- Telegram webhook receives event
- backend resolves `telegram_user_id` and session context
- backend loads relevant summary/profile memory
- backend calls model
- backend sends response
- backend persists summary/profile delta

This is fundamentally a webhook-driven REST integration with application-owned memory.

### Interoperability Standards and Protocols

Key practical standards are:

- HTTPS + JSON for Telegram/OpenAI traffic
- app-level structured JSON schemas for summaries and profiles
- explicit user/session identifiers for memory namespace separation

## 6. Performance and Scalability Analysis

### Performance Characteristics and Optimization

The major performance risks are:
- prompt bloat,
- excess DB round-trips,
- synchronous heavy summarization,
- retrieval overreach before needed.

Optimization comes primarily from:
- summary compression,
- compact profile schema,
- async post-processing,
- keeping vector retrieval out of the hot path until justified.

### Scalability Patterns and Approaches

The right scaling pattern is:
- stateless app processes,
- durable backing services,
- horizontal app scaling if needed,
- eventual async worker split only when load requires it.

## 7. Security and Compliance Considerations

### Security Best Practices and Frameworks

Because the domain is psychologically sensitive, memory retention is itself a security issue.

Core security requirements:
- encrypted transport,
- encrypted durable storage,
- secrets in environment configuration,
- least-privilege access,
- minimized sensitive logging,
- selective retention rules.

### Compliance and Regulatory Considerations

This research did not attempt a full legal/regulatory analysis. However, the technical design should assume:
- sensitive conversational summaries deserve higher handling discipline than ordinary app logs,
- unsafe or red-flag sessions may require different retention behavior,
- product policy and technical storage policy must remain aligned.

## 8. Strategic Technical Recommendations

### Technical Strategy and Decision Framework

**Recommended MVP strategy:**
- Python
- modular monolith
- Telegram webhooks
- OpenAI API
- Postgres
- session summary + accumulated typed profile
- no vector DB in MVP critical path

### Competitive Technical Advantage

The technical advantage is not “more advanced memory infra.”  
It is the ability to deliver stable continuity with a simple, inspectable, controllable memory model that aligns with product needs and safety boundaries.

## 9. Implementation Roadmap and Risk Assessment

### Technical Implementation Framework

**Stage 1**
- Telegram webhook service
- users/sessions/summaries/profile schema
- fast/deep session modes
- explicit context assembly

**Stage 2**
- summary generation
- durable profile updates
- technical health metrics

**Stage 3**
- optional weekly insights
- reliability hardening
- async job improvements

**Stage 4**
- embeddings and selective retrieval only if real usage justifies it

### Technical Risk Management

Main risks:
- summary drift
- over-promotion into profile memory
- context bloat
- async failure invisibility
- sensitive content retention

Mitigations:
- typed summary schema
- profile promotion rules
- compact memory envelopes
- async monitoring and retry strategy
- retention policy tied to safety logic

## 10. Future Technical Outlook and Innovation Opportunities

### Near-term Technical Evolution

In 1-2 years, the likely evolution is:
- better profile extraction,
- more nuanced memory ranking,
- selective retrieval over prior summaries,
- stronger eval pipelines for memory quality.

### Medium-term Technology Trends

In 3-5 years, the strongest extension path is:
- embeddings attached to summaries/profile facts,
- retrieval over long histories,
- richer continuity across product surfaces,
- psychologist-support or white-label companion tools.

## 11. Technical Research Methodology and Source Verification

### Primary Technical Sources

- OpenAI Cookbook and API docs
- LangGraph / LangChain docs
- LlamaIndex memory docs
- Telegram Bot API docs
- pgvector docs
- Twelve-Factor App
- GitHub Actions / Python operational docs

### Technical Confidence Levels

- **High confidence**: summary + profile as MVP baseline; Python + Postgres + single service; no vector-first MVP
- **Medium confidence**: weekly insight in late MVP vs v1.1; when exactly to add Redis/worker
- **Low confidence**: any claim that full vector memory should be baseline for this use case

## 12. Technical Appendices and Reference Materials

### Architectural Pattern Comparison

- **Session summary only**
  - Lowest complexity
  - Good for continuity
  - Weak for long-range recall

- **Accumulated profile only**
  - Strong durable context
  - Too abstract alone
  - Needs session grounding

- **Summary + profile**
  - Best MVP trade-off
  - Strong continuity
  - Good controllability

- **RAG / vector-first**
  - Strong semantic recall
  - More infra and retrieval tuning
  - Better as v2

---

## Technical Research Conclusion

### Summary of Key Technical Findings

The core conclusion is straightforward: for a Telegram-based LLM product that promises continuity between emotionally sensitive sessions, the MVP should not start with vector-first memory. It should start with a controlled, inspectable, application-owned memory design built from structured session summaries and a compact accumulated user profile.

This architecture is the best fit because it aligns with:
- the product’s value proposition,
- the realities of Telegram bot implementation,
- the operational simplicity required for MVP,
- and the safety constraints of sensitive user data.

### Final Technical Recommendation

**Recommended MVP architecture:**
- Python
- Telegram webhook bot
- modular monolith
- OpenAI API
- PostgreSQL
- summary-per-session + accumulated typed profile
- async post-session enrichment
- vector retrieval deferred until real recall depth demands it

<!-- Content will be appended sequentially through research workflow steps -->
