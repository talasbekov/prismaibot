---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
inputDocuments:
  - /home/erda/Музыка/goals/_bmad-output/planning-artifacts/product-brief-goals-2026-03-09.md
  - /home/erda/Музыка/goals/_bmad-output/planning-artifacts/research/technical-llm-memory-architecture-for-telegram-bots-research-2026-03-09.md
  - /home/erda/Музыка/goals/_bmad-output/brainstorming/brainstorming-session-2026-03-08-231431.md
workflowType: 'prd'
documentCounts:
  briefCount: 1
  researchCount: 1
  brainstormingCount: 1
  projectDocsCount: 0
classification:
  projectType: api_backend
  domain: mental wellness / psychology-adjacent
  complexity: high
  projectContext: greenfield
---

# Product Requirements Document - goals

**Author:** Bratan
**Date:** 2026-03-10

## Executive Summary

goals is a Telegram-first conversational backend product in the mental wellness / psychology-adjacent domain. It is designed for moments of acute interpersonal conflict and internal emotional overload, when users need immediate help to understand what is happening before they escalate the situation further, send the wrong message, or make a decision they will later regret.

The product does not aim to replace therapy or provide medical advice. Its purpose is to help users regain clarity through a fast, structured, nonjudgmental conversation that turns emotional confusion into a clearer understanding of the situation and a more grounded next step.

The core user is someone in an emotionally charged moment: after a fight with a partner, during unresolved tension at work, or while stuck in repetitive internal loops. Existing alternatives fail in predictable ways. Friends are biased and inconsistent. General-purpose AI tools answer prompts but do not reliably structure emotional context or continuity between sessions. Journaling provides release but not feedback. The product fills this gap through a low-friction Telegram experience that listens first, clarifies context, reflects the situation back more clearly than the user could articulate alone, and helps the user calmly `разобраться` before the situation worsens.

The MVP is intentionally narrow. It launches inside Telegram, uses a lightweight durable memory model based on session summaries and accumulated typed profile facts, and focuses on acute conflict reflection as the primary wedge. Retention and monetization depend on the product becoming more useful over time by remembering important context and recurring patterns without forcing the user to start from zero each session.

### What Makes This Special

This product is differentiated by one core insight: in emotionally acute situations, users usually do not need advice first. They need a fast, nonjudgmental, structured view of their situation that helps them see it clearly before they act impulsively. That insight changes both the conversation design and the product promise.

What makes goals special is not that it “talks about psychology,” but that it is purpose-built to help users `разобраться` in difficult situations. Instead of providing generic answers, it guides the user through a structured breakdown of the situation and returns a cleaner, calmer picture of what is happening.

Compared with friends, the product is neutral, available, and consistent. Compared with general-purpose AI tools, it is built specifically for emotional conflict reflection and continuity between sessions. Compared with therapy, it is immediate, lightweight, and available in the exact moment of need. Its long-term advantage comes from remembering important context and recurring patterns so that each new session starts from understanding, not from scratch.

## Project Classification

- **Project Type:** API/backend conversational bot
- **Domain:** mental wellness / psychology-adjacent
- **Complexity:** high
- **Project Context:** greenfield

## Success Criteria

### User Success

Продукт считается полезным для пользователя, если после сессии он выходит с более ясной картиной своей ситуации, чем заходил. Главный пользовательский результат — остановка внутренней руминации: мысли перестают ходить по кругу, а ситуация становится более понятной и структурированной.

Второй критический критерий — пользователь чувствует, что его поняли без осуждения. Это особенно важно для продукта в эмоционально чувствительном контексте: полезность определяется не только качеством разбора, но и тем, ощущается ли разговор бережным, нейтральным и безопасным.

Третий критерий — пользователь получает конкретный следующий шаг. Это не обязательно большое решение; даже маленькое, но понятное действие считается успешным исходом, если оно помогает человеку выйти из состояния зависания и двигаться дальше.

### Business Success

Первый ключевой бизнес-сигнал — **D7 Return**: пользователь возвращается в продукт в течение 7 дней после первой полезной сессии. Это показывает, что продукт создает повторяемую ценность, а не только разовый интерес.

Второй ключевой сигнал — **Paid Conversion** после 2–3 сессий. Для этого продукта оплата должна происходить не из любопытства, а потому что пользователь не хочет терять continuity, память о контексте и более глубокий формат разбора.

Третий ключевой сигнал — **Organic Referral**: пользователь сам рекомендует продукт близкому человеку, например отправляя сообщение в духе “попробуй это”. Для данного сегмента это особенно сильный validation signal, потому что рекомендация здесь строится на доверии и реальной пережитой пользе.

### Technical Success

Первый технический критерий — **memory correctness**. Session summary должен точно отражать содержание сессии, не искажать смысл и не добавлять галлюцинации. Память считается успешной только если она помогает continuity, а не вносит ошибки в будущие разговоры.

Второй критерий — **red-flag routing reliability**. Система должна стабильно обнаруживать кризисные сигналы и корректно включать режим мягкой эскалации. При этом она не должна слишком часто давать ложные срабатывания, которые ломают доверие и обычный user flow.

Третий критерий — **acceptable latency**. Ответ должен приходить достаточно быстро, чтобы поддерживать ощущение живого разговора. Для MVP ориентир — 5–8 секунд на основной ответ в типичном interaction path.

Четвертый критерий — **summary/profile pipeline reliability**. Генерация summary и обновление profile facts должны отрабатывать стабильно и быть наблюдаемыми как отдельный технический контур.

### Measurable Outcomes

- Пользователь доходит до конца первой сессии и получает итоговый ответ.
- Пользователь возвращается в течение 7 дней после первой полезной сессии.
- Пользователь переходит в платную модель после 2–3 сессий, когда начинает ценить continuity and memory.
- Session summaries сохраняются без критических смысловых искажений.
- Red-flag routing стабильно срабатывает на кризисных сигналах.
- Основной ответ укладывается в приемлемый latency window 5–8 секунд.
- Organic referrals появляются как сильный признак доверия и полезности.
- Summary/profile pipeline работает без существенных сбоев.

## Product Scope

### MVP - Minimum Viable Product

MVP должен включать только то, что необходимо для доказательства core value:

- core loop сессии: выслушать -> уточнить -> разложить ситуацию -> дать следующий шаг -> подвести итог;
- память между сессиями через summary-based continuity;
- два режима использования: быстрый и глубокий;
- paywall после 2–3 полноценных сессий;
- red-flag эскалацию для кризисных сценариев.

### Late MVP / Early Growth

- weekly insight как retention-механизм, если core flow уже доказал свою ценность;
- первичная реферальная механика с бонусом за реальную активацию приглашенного пользователя.

### Growth Features (Post-MVP)

- карта паттернов и динамики изменений;
- детектор повторяющихся ошибок и сценариев;
- персонализация тона общения под пользователя.

### Vision (Future)

- white-label или companion model для психологов;
- голосовой интерфейс;
- парная работа или совместные сценарии.

## User Journeys

### Journey 1: Маша - Primary User Success Path

Маша, 31 год, живет с партнером и приходит в продукт после ссоры, которая формально закончилась, но внутренне не отпустила. Мы встречаем ее в момент эмоциональной мути: ей стыдно снова писать подруге, к психологу идти "слишком рано", а в голове крутится один и тот же вопрос - она слишком остро реагирует или в отношениях реально что-то не так.

Она открывает Telegram-бота и не сталкивается с friction-heavy onboarding. Вместо длинных форм бот сразу спрашивает: "Что случилось?" После первого сообщения бот не начинает допрос и не дает ранний совет. Правильный ритм первого использования: короткое отражение -> 1-2 точных уточнения -> затем более структурный разбор. Это снижает напряжение и удерживает ее в разговоре.

По мере сессии бот отделяет факты от эмоций, показывает, где Маша может интерпретировать ситуацию слишком болезненно, а где действительно есть повод для обиды. Ключевой момент наступает тогда, когда бот формулирует ее ситуацию яснее, чем она могла сама. Это основной aha-moment продукта: не совет, а ясность.

К концу сессии Маша чувствует три вещи: мысли больше не крутятся хаотично, ее не осудили, и у нее есть понятный следующий шаг - например, что именно сказать партнеру или что пока не делать. Monetization moment возникает позже, когда происходит новый конфликт, а ей не нужно заново объяснять отношения, прошлый эпизод и свои типичные триггеры. Именно continuity between sessions становится причиной платить.

### Journey 2: Red-Flag User - Primary User Edge Case

Пользователь приходит в продукт не просто в состоянии конфликта, а в кризисной эмоциональной точке. В тексте появляются признаки self-harm ideation, тяжелой депрессии, опасного абьюза или другого red-flag состояния. Это самый критичный edge case во всем продукте, потому что здесь ошибка разрушает не только UX, но и доверие, безопасность и репутацию.

Система должна распознать, что обычный conversational flow здесь недостаточен. Вместо стандартного разбора бот переключается в режим мягкой эскалации: сохраняет бережный тон, не бросает пользователя без ответа, но перестает вести разговор как обычную reflective session. Он признает серьезность состояния, не делает вид, что может решить проблему сам, и направляет пользователя к более подходящей форме помощи.

Успешный outcome этого journey - не "хороший разбор", а корректная смена режима: crisis flow triggered, standard advice flow interrupted, escalation copy delivered, and operator alert surfaced if policy requires it. Неуспех этого journey означает прямой product and trust failure.

### Journey 3: Основатель / Оператор - Ops and Oversight Journey

В MVP нет отдельной support-команды, поэтому роль внутреннего пользователя выполняет сам основатель/оператор продукта. Мы встречаем его не в обычном customer support context, а как человека, который отвечает за качество системы, red-flag обработку и продуктовую устойчивость.

Оператор регулярно проверяет red-flag alerts, смотрит на аномалии в поведении сессий, оценивает качество summary generation и замечает, когда память начинает искажать контекст или когда продукт отвечает слишком слабо, слишком резко или слишком шаблонно. Его задача - не читать все подряд, а видеть точки, где система может навредить, потерять доверие или сломать core value.

Ценность продукта для этого пользователя проявляется в наличии достаточной наблюдаемости: оператор понимает, какие сессии попали в crisis routing, где summary pipeline дает сбой, где растет latency, и где пользователи бросают диалог без завершения. Успешный ops journey означает, что продукт управляем, а не является черным ящиком.

### Journey 4: Лена - Retention and Subscription Journey

Лена, 29 лет, впервые пришла в продукт в момент конфликта, но осталась не из-за одного удачного ответа. У нее нет постоянного острого кризиса, однако есть фоновая тревожность и склонность к руминации. После первого полезного опыта продукт становится для нее не emergency tool, а регулярным инструментом эмоциональной разгрузки.

Мы встречаем ее уже не в момент пика боли, а в более спокойный период. Она возвращается, потому что продукт помнит важный контекст и повторяющиеся паттерны. Ей не нужно каждый раз заново объяснять свои отношения, типовые триггеры и внутренние циклы. Это и есть переход от разовой ценности к подписочной.

Ключевой retention moment возникает, когда continuity between sessions помогает заметить повторения, динамику и изменение реакции на похожие ситуации. Позже это может быть усилено weekly reflection layer, но базовая подписочная ценность начинается именно с continuity. Она платит не за "еще один чат", а за ощущение, что система удерживает нить ее внутренней динамики. Успешный outcome этого journey - регулярное возвращение, рост доверия к памяти продукта и готовность оставаться на подписке.

### Journey Requirements Summary

Эти journeys выявляют следующие capability areas:

- low-friction Telegram onboarding;
- core conversational loop с ясным aha-moment;
- structured reflection instead of generic advice;
- reliable red-flag detection and soft escalation flow;
- operator visibility into quality, safety, and anomalies;
- continuity between sessions through summary-based memory;
- retention layer через repeat usage and context-based value;
- monetization through preserved context, not through raw message limits.

## Domain-Specific Requirements

### Compliance & Regulatory

Продукт должен быть позиционирован как **non-medical self-reflection tool with safety disclaimers**, а не как медицинский сервис, психологическая практика или диагностическая система. Это означает, что в onboarding, footer и ключевых trust surfaces должно быть явно сказано, что продукт:

- не является психологом или врачом;
- не ставит диагнозов;
- не заменяет специалиста.

Интерфейс и copywriting не должны использовать медицинскую терминологию, создающую ложные ожидания о клинической точности или терапевтическом статусе продукта. Важный принцип: safe positioning обеспечивается не только дисклеймерами, но и самим conversational behavior, tone rules и запретом на doctor-like outputs.

С юридической точки зрения MVP рассматривается как обычный SaaS-продукт с повышенными требованиями к конфиденциальности и safety communication, а не как regulated medical software. При этом требования к приватности и handling sensitive conversations должны проектироваться строже, чем у обычного consumer chat product.
Эта граница должна регулярно пересматриваться по мере развития продукта, чтобы новые фичи, copy или retention-механики не переводили продукт в фактическое medical-like positioning.

### Technical Constraints

Из-за чувствительности пользовательских разговоров в MVP обязательны следующие технические ограничения:

- шифрование данных в хранилище;
- удаление истории по запросу пользователя;
- минимизация логов и отказ от долгого хранения сырых сообщений;
- хранение structured summary после сессии при отказе от длительного хранения полного сырого диалога;
- operator access по умолчанию только к агрегированным метрикам и системным сигналам, без routine access к содержимому сессий;
- controlled, policy-governed exceptional access path для расследования серьезных инцидентов.

Это формирует важный architectural principle: **summary is the durable memory artifact, raw conversation is transient processing input**.

### Integration Requirements

В MVP domain-specific perimeter intentionally small:

- **Telegram** как основная пользовательская платформа;
- **payments** через Telegram Stars или ЮKassa;
- **crisis links** как статический список телефонов доверия и ссылок на помощь, используемый при red-flag эскалации.

Другие внешние интеграции в MVP не требуются.

### Risk Mitigations

#### 1. Бот звучит как врач

Главный риск — продукт начинает звучать как диагност или терапевт, а не как инструмент разбора. Это снижает trust correctness и повышает юридический и этический риск.

**Mitigation:**

- жесткие prompt and policy rules против медицинской терминологии;
- tone guidelines, запрещающие уверенные диагнозы и лечебные обещания;
- review of sample outputs against “doctor-like tone” failure mode.

#### 2. Пропуск кризисного сигнала

Если система не распознает red flag и продолжает обычный reflective flow, это приводит к safety failure.

**Mitigation:**

- dedicated red-flag detection layer;
- soft escalation flow вместо обычного session flow;
- operator alerting for crisis-routed cases if policy requires;
- регулярная проверка false-negative и false-positive patterns.

#### 3. Память галлюцинирует

Если summary содержит то, чего не было в сессии, пользователь быстро теряет доверие ко всей continuity model.

**Mitigation:**

- typed summary schema;
- conservative summary generation;
- memory quality review and monitoring;
- запрет на агрессивную автоматическую promotion logic в durable profile.

#### 4. Утечка переписок

Чувствительные разговоры пользователя не должны попадать в лишние логи, внутренние панели или внешние каналы.

**Mitigation:**

- encrypted storage;
- log minimization;
- raw transcript retention minimization;
- restricted operator access model;
- explicit deletion workflows.

#### 5. Эскалация воспринимается как отказ

Если referral to crisis help звучит как холодное “я не могу помочь”, пользователь может воспринять это как отвержение в уязвимом состоянии.

**Mitigation:**

- soft escalation wording;
- сохранение человеческого и бережного тона;
- guidance, которое сначала признает состояние пользователя, а уже потом предлагает более подходящую помощь.

### Domain Design Principles

Из этого домена вытекают следующие продуктовые принципы:

- продукт должен быть полезным, но не притворяться клиническим;
- память должна быть ограниченной, контролируемой и заслуживающей доверия;
- safety важнее полноты разбора в crisis scenarios;
- privacy architecture является частью product trust, а не только technical hygiene;
- escalation должна ощущаться как поддержка, а не как отказ;
- investigability should exist without routine exposure to sensitive content.

## Innovation & Novel Patterns

### Detected Innovation Areas

Инновация в этом продукте не заключается в одном отдельном техническом прорыве. Telegram-боты, emotional support chats, AI memory patterns и self-reflection tools уже существуют по отдельности. Новизна возникает в их конкретной комбинации:

- Telegram-first delivery model;
- acute conflict reflection as the primary wedge;
- clarity-first conversational method instead of advice-first or therapy-like interaction;
- curated continuity memory as durable product value.

Главная инновационная ставка здесь — не tech novelty, а **JTBD reframing plus product recombination**. Продукт переопределяет immediate emotional help как structured clarity in the moment, delivered through Telegram and reinforced by continuity across sessions.

### Market Context & Competitive Landscape

Существующие решения обычно попадают в одну из нескольких категорий:

- general-purpose AI chat;
- therapy or therapist marketplace;
- journaling or notes tools;
- emotional support / wellness content.

Продукт берет элементы из нескольких категорий и собирает их под другой moment-of-use: immediate conflict reflection in Telegram. Пользователь приходит не "заниматься психологией", а `разобраться прямо сейчас`, до того как ситуация ухудшится.

Главная assumption, которую продукт оспаривает, звучит так:
**"Если человеку плохо, ему нужен психолог или друг."**
Продукт предлагает другой JTBD: в момент острого конфликта человеку часто нужна не терапия и не сочувствие, а быстрая, нейтральная, неосуждающая структурная ясность.

### Validation Approach

Инновационная гипотеза продукта должна валидироваться не через красивый positioning alone, а через конкретные qualitative, behavioral, and economic signals.

**Qualitative proof:** пользователь субъективно формулирует ценность как "бот сформулировал мою ситуацию точнее, чем я сам мог". Это показывает, что clarity-first conversational method действительно работает и дает тот outcome, на котором строится дифференциация.

**Behavioral proof:** пользователь возвращается после первой полезной сессии и не начинает снова с нуля, потому что continuity работает в реальном use case.

**Economic proof:** пользователь платит именно затем, чтобы не потерять контекст между сессиями. Это показывает, что memory continuity работает как реальная ценность, а не как техническая фича.

Вместе эти сигналы проверяют обе стороны инновационной гипотезы:

- clarity-first reflection как differentiated user value;
- continuity как monetizable utility.

### Risk Mitigation

Главный риск innovation framing в том, что продукт может начать претендовать на слишком громкую category claim, которую рынок не подтвердит. В этом случае важно не переоценить novelty и не строить стратегию на искусственной уникальности.

Если innovation hypothesis не подтверждается полностью, fallback остается сильным:

- продукт сохраняет ценность как Telegram-based self-reflection tool;
- differentiation строится на UX quality, safety, clarity, and continuity;
- бизнес может развиваться как disciplined niche mental wellness product без необходимости доказывать новую категорию.

Это хороший fallback, потому что он не означает провал. Он означает переход от “category innovation claim” к “high-quality product execution in a valuable niche”.

## API Backend Specific Requirements

### Project-Type Overview

goals is not a public API platform. For MVP, it should be treated as a **private Telegram bot backend** with a small set of operational interfaces and provider-facing callbacks. The backend exists to receive user input from Telegram, orchestrate conversational flows, process payments, manage memory continuity, trigger safety handling, and support a minimal operator workflow.

This distinction matters because the technical requirements are closer to a secure conversational service than to a developer-facing API product. There is no need in MVP for SDKs, external developer documentation, or public API version lifecycle management.
Even with the `api_backend` classification, this PRD intentionally retains user journeys because the backend is being specified in service of a user-facing conversational product rather than as a standalone API platform.

### Technical Architecture Considerations

The backend should be organized around a narrow ingress model and a small set of internal operational capabilities.

**External ingress:**

- Telegram webhook as the primary entry point for all user messages;
- payment provider callbacks for subscription and purchase events.

**Internal operational capabilities:**

- health monitoring;
- user data deletion capability;
- operator alert routing for red-flag and anomaly events.

This architecture supports the product’s core value while keeping the external interface surface intentionally small. Reliability, idempotency, and secure callback handling matter more than broad API flexibility.

### Endpoint Specifications

The MVP requires the following endpoint groups or equivalent capabilities:

- **Telegram webhook**: primary ingress for all incoming user messages and Telegram events.
- **Payments callback**: callback handling for Telegram Stars and/or ЮKassa events.
- **Healthcheck**: monitoring endpoint for deployment and uptime checks.
- **Delete-my-data capability**: user-triggered or operator-assisted deletion flow for history removal, which may be bot-driven rather than exposed as a public REST route.
- **Operator alert delivery channel**: operational notification path for red-flag and anomaly alerts routed to the founder/operator.

No public product API should be exposed in MVP.

### Authentication Model

Authentication and request verification should be lightweight but strict:

- **Telegram webhook** should use Telegram secret token verification.
- **Admin-facing endpoints or operator actions** should use a simple secret header token in MVP.
- **Payments callback endpoints** must verify provider signatures or equivalent authenticity checks.

This model is sufficient for the early-stage service perimeter and should be revisited only if the operator surface or integration surface expands.

### Data Schemas and Formats

The backend should standardize on **JSON everywhere** for inbound and outbound internal application data.

MVP scope is **text-only**:

- no voice messages;
- no file uploads;
- no attachment processing;
- no media ingestion pipeline.

This keeps the request/response model simple, the summarization pipeline predictable, and the moderation/safety surface smaller.

### Error Codes and Operational Responses

Even without a public API, the system should maintain consistent internal and operational response patterns:

- webhook acknowledgements must be deterministic;
- duplicate Telegram updates must be safely ignored or replay-safe;
- payment callback failures must be observable and retry-safe;
- deletion requests must produce explicit success/failure outcomes for internal tracking;
- alert routing failures must not silently disappear.

The emphasis is on operational correctness rather than developer-facing API ergonomics.

### Rate Limits and Abuse Controls

The MVP should include baseline protection against misuse and accidental overload:

- **per-user message rate limits** to reduce flooding and runaway usage;
- **idempotent Telegram update handling** for webhook retries and duplicate deliveries;
- **abuse control rules** to detect and temporarily block anomalous activity patterns.

These controls are essential not just for infrastructure protection but also for product stability, trust, and cost control in an LLM-backed system.

### Versioning Strategy

Formal `/v1` endpoint versioning is not required in MVP. A simple route structure is sufficient because the backend is not being exposed as a public developer product.

Versioning should be introduced later only if:

- a broader external API surface appears;
- third-party integrations are added;
- multiple clients need explicit compatibility guarantees.

### SDK / Public API Position

The MVP should explicitly **not** include:

- public API access;
- SDKs;
- external developer documentation for integrations.

The backend exists only to serve:

- Telegram bot traffic;
- payment provider callbacks;
- minimal operator workflows.

This keeps the implementation focused on product value instead of premature platformization.

### Implementation Considerations

For this project type, the most important implementation concerns are:

- secure webhook handling;
- idempotent event processing;
- simple but auditable authentication for operator flows;
- predictable JSON schemas for message, summary, and payment events;
- internal observability for failures in alerts, payments, and memory workflows;
- a clear billing boundary so provider-specific payment logic does not leak into the conversation core.

The backend should be designed as a private operational service with strong reliability and narrow interfaces, not as a general-purpose API product.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** problem-solving MVP focused on validated user usefulness.

Первая версия продукта должна доказать, что в момент acute conflict пользователи действительно получают ясность, чувствуют пользу от structured reflection, возвращаются повторно и начинают ценить continuity between sessions. Revenue, fundraising, and broader growth are secondary outcomes that should follow only after core usefulness is validated.

Это означает, что MVP не должен быть feature showcase, platform play, or polished wellness ecosystem. Он должен быть узким, надежным и ориентированным на то, чтобы пользователь сказал: "это реально помогло мне разобраться".

Важно: этот MVP lean по feature surface, но **not cheap in quality requirements**. Trust, memory correctness, safety handling, and conversational usefulness are non-negotiable even in the first version.

**Resource Requirements:** solo founder plus one backend/bot contractor.

На этапе MVP достаточно минимальной команды:

- founder owns product, conversation design, prompting, safety policy, and product iteration;
- one backend/bot contractor builds and stabilizes the Telegram bot backend, memory flow, payment integration, and operational surfaces.

This is viable only if scope remains strict and nonessential surfaces stay out of MVP.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**

- Маша: primary success path for acute relationship conflict;
- red-flag user: critical safety edge case;
- базовая continuity path between sessions to support early monetization.

**Core Experience Must-Have Capabilities:**

- frictionless onboarding with one starting prompt;
- core conversation loop: listen -> clarify -> break down -> next step -> summary;
- summary-based memory continuity between sessions;
- red-flag detection with soft escalation.

**Business Validation Must-Have Capability:**

- paywall after 2–3 full sessions.

Эти capability blocks вместе определяют MVP. Без core experience capabilities продукт не проверяет user usefulness. Без paywall он не проверяет monetization through continuity.

### Manual-First Operations

To keep MVP lean, several capabilities can be manual or semi-manual initially:

- red-flag alert review by the founder/operator;
- static crisis links list instead of dynamic or API-driven crisis routing;
- manual handling of deletion requests initiated through the bot;
- selective manual quality review of session outcomes and summary quality.

This manual-first approach is acceptable for a low-volume MVP, but any manual workflow tied to safety or data deletion must have explicit checklist and traceability.

### Post-MVP Features

**Phase 2 (Post-MVP / Retention):**

- weekly insight / reflection layer;
- repeat-use reinforcement features to strengthen calm-period retention.

**Phase 3 (Growth / Acquisition):**

- early referral mechanic with activation-based reward;
- growth loops that amplify trusted word-of-mouth without distorting the core product promise.

**Phase 4 (Expansion):**

- pattern map and change-over-time visibility;
- repeated-mistake or recurring-pattern detection;
- tone personalization based on user style and history;
- white-label or therapist companion model;
- voice interface;
- pair or partner mode.

This phased roadmap preserves the core logic of the product: usefulness first, retention second, acquisition third, and expansion later.

### Risk Mitigation Strategy

**Technical Risks:**  
The biggest technical risk is memory inaccuracy. If the generated summary misrepresents the session, the user will quickly lose trust in continuity and therefore in one of the product’s main monetization drivers.

**Mitigation Approach:**  
Start with conservative typed summaries, narrow memory scope, manual review of early outputs, and explicit monitoring of summary correctness before expanding memory sophistication.

**Market Risks:**  
The biggest market risk is that acute conflict may be a strong acquisition wedge but a weak retention foundation. Users may come once in pain but fail to return in calmer periods, weakening subscription economics.

**Mitigation Approach:**  
First validate the acute-conflict wedge, then test whether continuity expands the use case from episodic to recurring and creates repeat value beyond peak emotional moments.

**Resource Risks:**  
The biggest resource risk is founder overload. Conversation design, backend direction, safety logic, and product iteration can easily become too much for a solo founder to manage alone.

**Mitigation Approach:**  
Keep the feature set narrow, allow operational workflows to remain manual, and rely on a backend/bot contractor who supports not just initial implementation but ongoing operational reliability after launch.

## Functional Requirements

### User Access & Session Start

- FR1: User can start using the product from Telegram without creating a separate account or completing a registration flow.
- FR2: User can begin a new session from a single opening prompt without completing a multi-step onboarding flow.
- FR3: User can choose between a fast reflection mode and a deep reflection mode when starting a session.
- FR4: User can resume using the product in later sessions without re-explaining all prior context from scratch.

### Guided Reflection Experience

- FR5: User can describe a current conflict, emotionally difficult situation, or internal mental loop in free-form text.
- FR6: Product can guide the user through a structured reflection flow that begins with listening and reflecting before deeper clarification, and includes clarification, situation breakdown, next-step guidance, and session closure.
- FR7: Product can reflect the user’s situation back as a structured interpretation that summarizes the main facts, emotions, and tensions raised in the session.
- FR8: Product can help the user distinguish between facts, emotions, interpretations, and possible misunderstandings within a situation.
- FR9: Product can offer up to three next-step options at the end of a session.
- FR10: User can receive an end-of-session takeaway that includes a short situation summary and a next-step recommendation.

### Continuity & Memory

- FR11: Product can generate a structured summary after each completed session.
- FR12: Product can retain relevant continuity information from prior sessions for future use.
- FR13: Product can use prior summaries and accumulated user context to improve the relevance of later sessions.
- FR14: User can continue a later session with awareness of important prior context and recurring patterns.
- FR15: Product can maintain continuity using retained memory artifacts without requiring long-term retention of full raw transcripts.

### Safety & Crisis Escalation

- FR16: Product can detect red-flag signals in user messages that indicate crisis, self-harm risk, dangerous abuse, or similarly sensitive situations.
- FR17: Product can shift from normal reflection flow to a crisis-aware escalation flow when red-flag signals are detected.
- FR18: Product can provide escalation messaging that acknowledges the user's state, explains the product boundary, and presents a more appropriate support option.
- FR19: Product can present crisis-help resources or support links when escalation is triggered.
- FR20: Product can prevent standard reflective guidance from continuing unchanged when a crisis pattern has been detected.

### Subscription, Access & Billing

- **FR21:** Пользователю предоставляется **один полный цикл** (рефлексия или брейншторм) бесплатно, чтобы он мог полностью ощутить ценность продукта.
- **FR22:** Пейволл (Paywall) срабатывает при попытке начать **вторую сессию** после завершения первого полного цикла.
- **FR23:** Пользователь может оформить **ежемесячную подписку (3000 тг)** с автопродлением через поддерживаемую платежную систему.
- **FR24:** Система корректно обрабатывает успешные и неудачные платежи, обновляя статус доступа.
- **FR25:** Пользователь может видеть текущий статус своей подписки и дату следующего списания.
- **FR26:** Пользователь может отменить подписку; в этом случае **доступ остается активным до конца оплаченного 30-дневного периода**.
- **FR27:** Продукт сохраняет непрерывность данных (continuity) и Premium-функции (память) при переходе между состояниями подписки.
- **FR28:** Ограничения бесплатного доступа и ценность Premium (безлимит и память) четко коммуницируются пользователю.
- **FR44:** Система автоматически обрабатывает продление подписки (рекуррентные платежи) через адаптер платежного провайдера.
- **FR45:** Система предоставляет **льготный период (Grace Period) — 1 день (24 часа)** для неудачных продлений, прежде чем Premium-доступ будет ограничен.

### Retention & Ongoing Engagement

- FR29: Product can send users a periodic reflective insight based on prior sessions and retained context.
- FR30: User can receive a weekly insight without needing to manually restart a new session.
- FR31: Product can use continuity across sessions to support repeat usage outside of acute conflict moments.

### Privacy & Data Control

- FR32: User can request deletion of their stored data.
- FR33: Product can fulfill user data deletion requests and remove retained user memory artifacts.
- FR34: Product can minimize routine retention of raw conversational content while preserving required continuity artifacts.

### Operator Oversight & Operational Control

- FR35: Operator can receive alerts when red-flag sessions are detected.
- FR36: Operator can receive red-flag alerts without routine exposure to full session content.
- FR37: Operator can monitor core operational signals such as active usage, session activity, payment events, and product errors.
- FR38: Operator can execute or confirm user data deletion requests.
- FR39: Operator can review payment issues and subscription-state problems.
- FR40: Operator can investigate critical failures through a controlled and policy-governed operational path.

### Payment & Service Operations

- FR41: Product can process inbound payment-provider events related to purchase, renewal, failure, or cancellation states.
- FR42: Product can maintain service health visibility for monitoring and operational response.
- FR43: Product can handle duplicate or repeated inbound service events without creating incorrect user state changes.

## Non-Functional Requirements

### Performance

- Основной пользовательский ответ бота должен возвращаться в пределах **8 секунд p95** для typical interaction path.
- Генерация session summary не должна блокировать основной пользовательский ответ.
- Healthcheck endpoint должен отвечать в пределах **200 мс** при нормальном состоянии системы.
- Weekly insight delivery job должна завершать рассылку по всей пользовательской базе в пределах **1 часа**.

### Security & Privacy

- Все пользовательские и системные данные должны быть защищены **encryption in transit** и **encryption at rest**.
- Сырые пользовательские сообщения не должны храниться дольше processing window, необходимого для ответа и генерации summary.
- Секреты и ключи интеграций не должны храниться в кодовой базе и должны управляться через защищенный operational process.
- Операторский доступ по умолчанию не должен включать содержимое сессий; оператор должен иметь доступ только к агрегированным метрикам, operational statuses и alert signals, кроме controlled incident path.
- Операции удаления пользовательских данных должны оставлять **audit trail**.
- Платежные данные не должны храниться внутри продукта; хранение и обработка платежных реквизитов должны оставаться на стороне платежного провайдера.

### Reliability

- Telegram webhook processing должен быть **идемпотентным** для повторных updates и retries.
- Payment callbacks должны использовать проверку подлинности и не должны изменять access state без подтвержденного payment event.
- Summary pipeline не должен приводить к потере пользовательской сессии при сбое; при ошибке должен существовать retry or fallback behavior.
- Red-flag alerting должен использовать **best-effort delivery** с созданием operator-visible failure signal при недоставке.
- Data deletion requests должны исполняться в пределах **72 часов** и подтверждаться пользователю.

### Scalability

- MVP должен поддерживать стартовую нагрузку в диапазоне **100-500 активных пользователей** без архитектурной переработки.
- Система должна выдерживать не менее **50 одновременных активных сессий** в пиковый момент.
- Архитектура должна допускать **10x growth within 12 months** without requiring a full rewrite if the product succeeds.
- Request handling should support horizontal scaling when traffic increases without requiring a redesign of the product core.

### Accessibility

- Core product flow должен оставаться **text-first** и не должен зависеть от обязательного нажатия UI buttons для прохождения основной сессии.
- Основные пользовательские действия должны быть доступны через понятное текстовое взаимодействие внутри Telegram.

### Integration Reliability

- Telegram integration должна обеспечивать graceful handling of Telegram API disruption without silently losing durable user state or corrupting session continuity.
- Payment provider integration должна корректно обрабатывать timeouts, failures, and delayed confirmations.
- При ошибках платежной интеграции пользователь должен получать понятный статус доступа или статуса оплаты, а не молчаливую ошибку.
