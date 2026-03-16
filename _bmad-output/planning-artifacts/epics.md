---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - /home/erda/Музыка/goals/_bmad-output/planning-artifacts/prd.md
  - /home/erda/Музыка/goals/_bmad-output/planning-artifacts/architecture.md
  - /home/erda/Музыка/goals/_bmad-output/planning-artifacts/ux-design-specification.md
  - /home/erda/Музыка/goals/_bmad-output/brainstorming/brainstorming-session-2026-03-08-231431.md
  - /home/erda/Музыка/goals/_bmad-output/planning-artifacts/research/technical-llm-memory-architecture-for-telegram-bots-research-2026-03-09.md
---

# goals - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for goals, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: User can start using the product from Telegram without creating a separate account or completing a registration flow.
FR2: User can begin a new session from a single opening prompt without completing a multi-step onboarding flow.
FR3: User can choose between a fast reflection mode and a deep reflection mode when starting a session.
FR4: User can resume using the product in later sessions without re-explaining all prior context from scratch.
FR5: User can describe a current conflict, emotionally difficult situation, or internal mental loop in free-form text.
FR6: Product can guide the user through a structured reflection flow that begins with listening and reflecting before deeper clarification, and includes clarification, situation breakdown, next-step guidance, and session closure.
FR7: Product can reflect the user’s situation back as a structured interpretation that summarizes the main facts, emotions, and tensions raised in the session.
FR8: Product can help the user distinguish between facts, emotions, interpretations, and possible misunderstandings within a situation.
FR9: Product can offer up to three next-step options at the end of a session.
FR10: User can receive an end-of-session takeaway that includes a short situation summary and a next-step recommendation.
FR11: Product can generate a structured summary after each completed session.
FR12: Product can retain relevant continuity information from prior sessions for future use.
FR13: Product can use prior summaries and accumulated user context to improve the relevance of later sessions.
FR14: User can continue a later session with awareness of important prior context and recurring patterns.
FR15: Product can maintain continuity using retained memory artifacts without requiring long-term retention of full raw transcripts.
FR16: Product can detect red-flag signals in user messages that indicate crisis, self-harm risk, dangerous abuse, or similarly sensitive situations.
FR17: Product can shift from normal reflection flow to a crisis-aware escalation flow when red-flag signals are detected.
FR18: Product can provide escalation messaging that acknowledges the user's state, explains the product boundary, and presents a more appropriate support option.
FR19: Product can present crisis-help resources or support links when escalation is triggered.
FR20: Product can prevent standard reflective guidance from continuing unchanged when a crisis pattern has been detected.
FR21: Product can allow limited free usage before paid access is required.
FR22: Product can enforce a paywall after the defined free-usage threshold is reached.
FR23: User can unlock paid access through a supported payment flow.
FR24: Product can recognize successful and failed payments and update access accordingly.
FR25: User can view their current subscription or access status.
FR26: User can request cancellation or non-renewal of paid access.
FR27: Product can preserve continuity and premium access distinctions across free and paid usage states.
FR28: User can understand access limits and paid-access benefits when free usage is exhausted.
FR29: Product can send users a periodic reflective insight based on prior sessions and retained context.
FR30: User can receive a weekly insight without needing to manually restart a new session.
FR31: Product can use continuity across sessions to support repeat usage outside of acute conflict moments.
FR32: User can request deletion of their stored data.
FR33: Product can fulfill user data deletion requests and remove retained user memory artifacts.
FR34: Product can minimize routine retention of raw conversational content while preserving required continuity artifacts.
FR35: Operator can receive alerts when red-flag sessions are detected.
FR36: Operator can receive red-flag alerts without routine exposure to full session content.
FR37: Operator can monitor core operational signals such as active usage, session activity, payment events, and product errors.
FR38: Operator can execute or confirm user data deletion requests.
FR39: Operator can review payment issues and subscription-state problems.
FR40: Operator can investigate critical failures through a controlled and policy-governed operational path.
FR41: Product can process inbound payment-provider events related to purchase, renewal, failure, or cancellation states.
FR42: Product can maintain service health visibility for monitoring and operational response.
FR43: Product can handle duplicate or repeated inbound service events without creating incorrect user state changes.

### NonFunctional Requirements

NFR1: Основной пользовательский ответ бота должен возвращаться в пределах 8 секунд p95 для typical interaction path.
NFR2: Генерация session summary не должна блокировать основной пользовательский ответ.
NFR3: Healthcheck endpoint должен отвечать в пределах 200 мс при нормальном состоянии системы.
NFR4: Weekly insight delivery job должна завершать рассылку по всей пользовательской базе в пределах 1 часа.
NFR5: Все пользовательские и системные данные должны быть защищены encryption in transit и encryption at rest.
NFR6: Сырые пользовательские сообщения не должны храниться дольше processing window, необходимого для ответа и генерации summary.
NFR7: Секреты и ключи интеграций не должны храниться в кодовой базе и должны управляться через защищенный operational process.
NFR8: Операторский доступ по умолчанию не должен включать содержимое сессий; оператор должен иметь доступ только к агрегированным метрикам, operational statuses и alert signals, кроме controlled incident path.
NFR9: Операции удаления пользовательских данных должны оставлять audit trail.
NFR10: Платежные данные не должны храниться внутри продукта; хранение и обработка платежных реквизитов должны оставаться на стороне платежного провайдера.
NFR11: Telegram webhook processing должен быть идемпотентным для повторных updates и retries.
NFR12: Payment callbacks должны использовать проверку подлинности и не должны изменять access state без подтвержденного payment event.
NFR13: Summary pipeline не должен приводить к потере пользовательской сессии при сбое; при ошибке должен существовать retry or fallback behavior.
NFR14: Red-flag alerting должен использовать best-effort delivery с созданием operator-visible failure signal при недоставке.
NFR15: Data deletion requests должны исполняться в пределах 72 часов и подтверждаться пользователю.
NFR16: MVP должен поддерживать стартовую нагрузку в диапазоне 100-500 активных пользователей без архитектурной переработки.
NFR17: Система должна выдерживать не менее 50 одновременных активных сессий в пиковый момент.
NFR18: Архитектура должна допускать 10x growth within 12 months without requiring a full rewrite if the product succeeds.
NFR19: Request handling should support horizontal scaling when traffic increases without requiring a redesign of the product core.
NFR20: Core product flow должен оставаться text-first и не должен зависеть от обязательного нажатия UI buttons для прохождения основной сессии.
NFR21: Основные пользовательские действия должны быть доступны через понятное текстовое взаимодействие внутри Telegram.
NFR22: Telegram integration должна обеспечивать graceful handling of Telegram API disruption without silently losing durable user state or corrupting session continuity.
NFR23: Payment provider integration должна корректно обрабатывать timeouts, failures, and delayed confirmations.
NFR24: При ошибках платежной интеграции пользователь должен получать понятный статус доступа или статуса оплаты, а не молчаливую ошибку.

### Additional Requirements

- Epic 1 Story 1 должна учитывать greenfield-инициализацию: минимальная FastAPI backend foundation с явной modular monolith structure, Railway как базовый managed deployment и Render как эквивалентная альтернатива.
- MVP должен использовать Python, FastAPI, PostgreSQL, SQLAlchemy 2, Pydantic v2 и Alembic в рамках одного deployable service без раннего microservices split.
- Durable memory в MVP строится на session summary плюс typed profile facts; vector-first retrieval и full RAG не входят в критический путь MVP.
- Raw transcripts должны оставаться transient processing input, а session summaries и curated profile facts являются durable memory artifacts.
- Summary/profile enrichment должен выполняться после основного ответа через async seam, чтобы continuity work не блокировал trust-critical first response.
- Telegram webhook ingress и payment callbacks должны быть authenticated, idempotent и retry-safe, без порчи session state, access state или memory state при дублях.
- Billing должен оставаться за provider adapter boundary, чтобы логика Telegram Stars и/или ЮKassa не протекала в conversation domain.
- Operator surface для MVP должен оставаться минимальным: alerts, deletion handling, health/status visibility и restricted operational actions.
- Исключен routine operator access к содержимому сессий; exceptional access path должен быть policy-governed и auditable.
- UX должен быть Telegram-native и mobile-first: text-first interaction, sparse inline buttons, readable chunking длинных ответов и typing indicators как обязательный feedback pattern.
- Первый meaningful reply является главным trust-making moment и должен сначала отражать и структурировать ситуацию, а не советовать.
- Memory references в UX должны быть tentative и correctable; при неверном recall бот должен спокойно уступать коррекции пользователя без defensive phrasing.
- Silence and re-entry должны считаться first-class UX states с мягким возвратом без чувства вины, наказания или сломанного flow.
- Safety transition должен прерывать normal reflection flow и переводить пользователя в soft escalation с humane, calm, supportive phrasing и возможностью graceful step-down после false positive.
- Paywall и premium framing должны появляться только после felt value; premium value нужно объяснять через continuity и reduced emotional setup cost, а не через raw message limits.
- Accessibility в Telegram здесь в первую очередь cognitive and textual: без wall-of-text output, с низкой decision burden и touch-friendly sparse controls.
- Weekly insight является late-MVP/post-MVP retention layer, но architecture должна заранее сохранить scheduler/job seam для нее.
- Нужны structured JSON schemas для summaries, profiles, payment events и internal operational responses; internal HTTP surfaces должны придерживаться единых response envelopes.
- Logging and observability не должны опираться на routine sensitive-content logging; нужны sanitized provider payloads и operator-visible signals по payment failures, summary failures, alert delivery failures и deletion failures.
- Product boundary должен быть явно non-medical в copy и поведении: без doctor-like language, без implied diagnosis и без treatment claims.
- Нужны conservative memory-promotion rules: не каждый фрагмент сессии должен становиться durable memory, а high-risk content требует ограниченного продвижения или отдельной обработки.

### FR Coverage Map

FR1: Epic 1 - вход в продукт через Telegram без отдельной регистрации
FR2: Epic 1 - старт сессии с одного opening prompt
FR3: Epic 1 - выбор fast/deep режима
FR4: Epic 2 - повторный вход без объяснения с нуля
FR5: Epic 1 - свободный ввод ситуации
FR6: Epic 1 - structured reflection flow
FR7: Epic 1 - structured interpretation ответа
FR8: Epic 1 - различение фактов, эмоций и интерпретаций
FR9: Epic 1 - до трех next-step options
FR10: Epic 1 - end-of-session takeaway
FR11: Epic 2 - session summary
FR12: Epic 2 - хранение continuity info
FR13: Epic 2 - использование prior summaries/profile
FR14: Epic 2 - awareness of prior context and patterns
FR15: Epic 2 - continuity без long-term raw transcripts
FR16: Epic 3 - red-flag detection
FR17: Epic 3 - crisis-aware escalation flow
FR18: Epic 3 - escalation messaging
FR19: Epic 3 - crisis resources
FR20: Epic 3 - остановка standard reflective guidance
FR21: Epic 4 - limited free usage
FR22: Epic 4 - paywall enforcement
FR23: Epic 4 - supported payment flow
FR24: Epic 4 - payment result handling
FR25: Epic 4 - subscription/access status
FR26: Epic 4 - cancellation/non-renewal request
FR27: Epic 4 - continuity across free and paid states
FR28: Epic 4 - clear communication of limits and premium value
FR29: Epic 5 - periodic reflective insight
FR30: Epic 5 - weekly insight delivery
FR31: Epic 5 - repeat usage outside acute conflict
FR32: Epic 6 - user data deletion request
FR33: Epic 6 - deletion fulfillment and memory removal
FR34: Epic 2 - minimized raw retention with durable continuity artifacts
FR35: Epic 3 - operator red-flag alerts
FR36: Epic 3 - alerts without routine session exposure
FR37: Epic 6 - operational monitoring
FR38: Epic 6 - execute/confirm deletions
FR39: Epic 6 - payment/subscription issue review
FR40: Epic 3 - controlled investigation path for critical failures
FR41: Epic 4 - inbound payment-provider events
FR42: Epic 6 - service health visibility
FR43: Epic 6 - idempotent handling of repeated service events

## Epic List

### Epic 1: Первая полезная reflective-сессия в Telegram
Пользователь может зайти в бот, быстро описать ситуацию, пройти базовый reflective flow и получить ясный итог со следующим шагом без регистрации и тяжелого onboarding.
**FRs covered:** FR1, FR2, FR3, FR5, FR6, FR7, FR8, FR9, FR10

### Epic 2: Continuity и память между сессиями
Пользователь может вернуться позже и продолжить разговор без повторного полного объяснения контекста, а продукт сохраняет только нужную durable memory.
**FRs covered:** FR4, FR11, FR12, FR13, FR14, FR15, FR34

### Epic 3: Safety и мягкая эскалация кризисных сценариев
Продукт распознает red flags, корректно прерывает обычный flow, мягко переводит пользователя в safer path и уведомляет оператора без routine exposure к содержимому.
**FRs covered:** FR16, FR17, FR18, FR19, FR20, FR35, FR36, FR40

### Epic 4: Монетизация, доступ и continuity-based premium
Пользователь получает ограниченный free experience, затем понятный premium boundary, может оплатить доступ и понимать свой текущий access state.
**FRs covered:** FR21, FR22, FR23, FR24, FR25, FR26, FR27, FR28, FR41

### Epic 5: Retention и повторное возвращение (Post-MVP / Phase 2)
Пользователь получает дополнительную ценность вне acute момента за счет weekly insight и continuity-driven repeat usage.
**FRs covered:** FR29, FR30, FR31

### Epic 6: Privacy, operator operations и надежность сервиса
Пользователь может запросить удаление данных, а оператор может безопасно поддерживать работу продукта, отслеживать health, инциденты и проблемные платежные/операционные события.
**FRs covered:** FR32, FR33, FR37, FR38, FR39, FR42, FR43

<!-- Repeat for each epic in epics_list (N = 1, 2, 3...) -->

## Epic 1: Первая полезная reflective-сессия в Telegram

Пользователь может зайти в бот, быстро описать ситуацию, пройти базовый reflective flow и получить ясный итог со следующим шагом без регистрации и тяжелого onboarding.

### Story 1.1: Инициализация проекта из starter template для Telegram-first backend

As a developer setting up the MVP foundation,
I want развернуть проект из выбранного starter approach и подготовить минимальную рабочую backend-основу,
So that дальнейшие пользовательские истории Telegram-бота могут реализовываться на согласованной архитектурной базе.

**Enables:** Epic 1 implementation baseline

**Acceptance Criteria:**

**Given** Architecture document задает greenfield starter approach для MVP
**When** начинается реализация проекта
**Then** initial codebase создается на основе minimal FastAPI backend foundation с modular monolith structure
**And** setup соответствует выбранному starter approach without introducing unnecessary full-stack or microservice scaffolding

**Given** starter foundation подготавливается для Telegram-first продукта
**When** initial project structure и dependencies инициализированы
**Then** проект включает минимально необходимую app structure, configuration model и dependency set для bot ingress, conversation flow and persistence evolution
**And** setup не создает upfront domain tables, modules or infrastructure beyond what first implementation stories actually need

**Given** проект должен быть готов к дальнейшим Epic 1 user-facing stories
**When** starter initialization завершена
**Then** development environment, dependency installation and baseline configuration reproducibly work
**And** foundation пригодна для реализации Telegram session entry without redoing the project skeleton

**Given** deployment baseline в Architecture задан как managed single-service path
**When** starter project configuration подготавливается
**Then** foundation остается compatible with Railway-first or Render-equivalent deployment model
**And** secrets, environment configuration and provider integrations remain externalized from source code

**Given** initial setup завершилась ошибкой или inconsistent starter state
**When** команда пытается использовать foundation for follow-on stories
**Then** issue становится observable на уровне setup workflow
**And** project is not treated as ready if the starter baseline is only partially initialized

### Story 1.1a: Базовый CI/CD, staging и migration-safe deployment path

As a developer operating a trust-sensitive MVP backend,
I want настроить минимальный CI/CD pipeline, staging environment и migration-safe deployment discipline,
So that ранняя разработка и выкладка не ломают webhook, billing, deletion или safety-critical flows.

**Enables:** Safe greenfield implementation and deployment readiness

**Acceptance Criteria:**

**Given** проект уже инициализирован на выбранной архитектурной базе
**When** команда настраивает delivery baseline
**Then** существуют отдельные `local`, `staging` и `production` environment configurations
**And** secrets и environment-specific settings не смешиваются между собой

**Given** changes are pushed for validation
**When** CI pipeline запускается
**Then** pipeline выполняет automated tests, linting/type checks и базовую migration-aware verification
**And** build не считается green if critical validation failed

**Given** staging используется для доверительно-чувствительных flows
**When** команда проверяет pre-production deployment path
**Then** Telegram webhook behavior, payment callback wiring и operator-only endpoints могут быть проверены вне production
**And** deploy workflow не требует ad hoc ручных шагов, известных только одному человеку

**Given** schema change включена в release
**When** deployment запускается
**Then** migration execution follows a controlled path compatible with the selected hosting model
**And** product is not treated as deploy-ready if schema and app state may drift silently

**Given** CI/CD or staging setup частично сломаны или не покрывают trust-critical paths
**When** команда пытается использовать pipeline as operational baseline
**Then** limitation становится observable
**And** setup не считается sufficient only because code can still be deployed manually

### Story 1.2: Начало сессии через Telegram и мгновенный вход в разговор

As a пользователь в эмоционально нагруженном состоянии,
I want начать разговор с ботом сразу после входа в Telegram без регистрации и лишних шагов,
So that я могу быстро выговориться и получить первый полезный отклик без дополнительного friction.

**Implements:** FR1, FR2, FR5

**Acceptance Criteria:**

**Given** пользователь впервые открывает Telegram-бота или возвращается после долгого перерыва
**When** бот становится доступен для взаимодействия
**Then** пользователь может начать сессию без отдельной регистрации, логина или внешнего onboarding flow
**And** бот предлагает один понятный opening prompt, который приглашает сразу описать ситуацию в свободной форме

**Given** пользователь отправляет первое свободное текстовое сообщение о своей ситуации
**When** сообщение принимается ботом
**Then** система создает новую сессию, связывает ее с `telegram_user_id` и сохраняет минимальный session context, необходимый для продолжения разговора
**And** пользователю не требуется повторно подтверждать старт сессии через дополнительный обязательный шаг

**Given** пользователь находится в основном happy path Epic 1
**When** первая сессия начинается
**Then** основной flow остается text-first внутри Telegram
**And** критически важное продвижение по сессии не зависит от обязательного нажатия inline buttons

**Given** пользователь начал разговор
**When** бот готовит первый ответ
**Then** система показывает typing indicator или эквивалентный Telegram feedback signal
**And** первый meaningful response подготавливается в пределах latency envelope MVP без блокировки на несущественных пост-обработках

**Given** пользователь прислал пустой, слишком короткий или неясный первый ввод
**When** бот не может безопасно перейти к structured reflection
**Then** бот отвечает коротким, спокойным clarifying prompt
**And** не сваливается в ошибку, длинный system message или advice-first response

### Story 1.3: Выбор и запуск fast/deep reflective mode

As a пользователь, который хочет либо быстро выговориться, либо глубже разобрать ситуацию,
I want выбрать подходящий режим reflective-сессии без сложной настройки,
So that формат разговора соответствует моей текущей эмоциональной и когнитивной нагрузке.

**Implements:** FR3

**Acceptance Criteria:**

**Given** пользователь начал новую сессию и находится в ранней фазе разговора
**When** продукт предлагает выбрать режим взаимодействия
**Then** пользователь может выбрать `fast` или `deep` mode через простой Telegram-native interaction
**And** отсутствие выбора не блокирует продолжение базового user flow

**Given** пользователь выбирает `fast` mode
**When** выбор подтвержден системой
**Then** сессия переходит в более короткий reflective path с меньшим числом уточняющих шагов
**And** продукт по-прежнему обязан довести пользователя до structured takeaway и next-step recommendation

**Given** пользователь выбирает `deep` mode
**When** выбор подтвержден системой
**Then** сессия переходит в более подробный reflective path с большим числом уточнений и более глубоким разбором ситуации
**And** система сохраняет спокойный, неинтеррогационный tone без перегруза пользователя

**Given** пользователь не выбрал режим явно и просто продолжил писать свободным текстом
**When** система определяет, что пользовательский flow уже начался
**Then** продукт продолжает разговор без forced interruption на mode selection
**And** применяет безопасный mode default, который не ломает trust-making early experience

**Given** пользователь уже начал сессию в одном режиме
**When** продукт продолжает обрабатывать сообщения внутри этой сессии
**Then** выбранный режим сохраняется как часть session context для текущей сессии
**And** дальнейший flow и глубина follow-up вопросов соответствуют выбранному режиму

**Given** режим недоступен, не распознан или Telegram interaction с выбором не сработал
**When** продукт не может надежно применить explicit mode selection
**Then** сессия продолжает работать в безопасном fallback режиме
**And** пользователь не получает техническую ошибку, ломающую начало разговора

### Story 1.4: Первый trust-making ответ с отражением ситуации

As a пользователь в эмоционально сложной ситуации,
I want получить первый ответ, который показывает, что бот меня понял, прежде чем начнет советовать или направлять,
So that я чувствую доверие к разговору и готов продолжать сессию.

**Implements:** FR6, FR7

**Acceptance Criteria:**

**Given** пользователь уже отправил первичное описание своей ситуации
**When** система формирует первый meaningful response
**Then** ответ начинается с короткого human-feeling reflection of the situation
**And** не начинается с прямого совета, диагноза, moral judgment или therapy-like exercise

**Given** пользователь описал конфликт, тревожную ситуацию или внутренний loop в свободной форме
**When** бот отвечает первым substantive message
**Then** ответ отражает как минимум один значимый factual or situational element и один эмоциональный or tension element из сообщения пользователя
**And** формулировка звучит nonjudgmental, calm и grounded in the user context

**Given** первый meaningful response должен создать trust
**When** сообщение отправляется пользователю в Telegram
**Then** ответ остается readable и chunked для Telegram consumption
**And** не превращается в длинную wall of text, ухудшающую восприятие в стрессовом состоянии

**Given** система уверена недостаточно или пользовательский ввод слишком хаотичный для сильной интерпретации
**When** бот формирует первый meaningful response
**Then** он использует осторожную, tentative phrasing и добавляет 1 ясный follow-up question для уточнения
**And** не выдает overly confident interpretation, будто бот уже точно понял всю ситуацию

**Given** пользователь находится в normal reflective path и в сообщении нет явного crisis escalation trigger
**When** отправляется первый meaningful response
**Then** продукт сохраняет reflective flow и делает мягкий переход к следующему clarification step
**And** response design поддерживает дальнейший разбор, а не пытается закрыть разговор слишком рано

**Given** продукт позиционируется как non-medical self-reflection tool
**When** генерируется первый meaningful response
**Then** в ответе отсутствует doctor-like, diagnostic или treatment-oriented language
**And** сообщение не создает ложного впечатления, что продукт ставит диагноз или заменяет специалиста

### Story 1.5: Clarification и разбор фактов, эмоций и интерпретаций

As a пользователь, который пытается разобраться в конфликте или внутреннем напряжении,
I want чтобы бот помог мне отделить факты, эмоции и мои интерпретации через уточняющие вопросы и структурированный разбор,
So that ситуация становится яснее и менее хаотичной.

**Implements:** FR6, FR8

**Acceptance Criteria:**

**Given** пользователь получил первый trust-making response и продолжает сессию
**When** продукт переходит к clarification phase
**Then** бот задает ограниченное число релевантных follow-up questions, которые помогают уточнить контекст
**And** не превращает разговор в допрос или rigid questionnaire

**Given** в пользовательском описании смешаны факты, эмоции, допущения и возможные искажения
**When** бот продолжает reflective flow
**Then** система помогает явно различить factual elements, emotional reactions и interpretation layers
**And** делает это в обычном conversational format, а не в сухом analytic dump

**Given** пользователь делится дополнительными деталями по ситуации
**When** система обрабатывает новые сообщения в рамках active session
**Then** продукт обновляет текущий conversational understanding of the situation
**And** последующие follow-up prompts и промежуточные reflections остаются согласованными с уже собранным контекстом

**Given** пользователь находится в `fast` mode
**When** идет clarification and breakdown flow
**Then** количество уточняющих шагов остается ограниченным и ориентированным на быстрое достижение ясности
**And** продукт не затягивает сессию глубиной, не соответствующей выбранному режиму

**Given** пользователь находится в `deep` mode
**When** идет clarification and breakdown flow
**Then** система может пройти через более подробный reflective path с дополнительными уточнениями и deeper interpretation support
**And** глубина разбора остается связанной с пользовательским контекстом, а не с шаблонным сценарием

**Given** пользователь отвечает расплывчато, противоречиво или эмоционально перегруженно
**When** бот не может надежно продолжить breakdown
**Then** система задает следующий вопрос или промежуточное отражение в мягкой и уточняющей форме
**And** не делает резких выводов, не обвиняет пользователя и не теряет conversational coherence

**Given** пользователь замолкает в середине reflective flow или возвращается после паузы
**When** продукт обрабатывает прерванную сессию или re-entry
**Then** silence не трактуется как ошибка, отказ или провал сценария
**And** пользователь получает low-pressure path to continue or restart without guilt-inducing language

**Given** пользователь уводит разговор в тему, не связанную напрямую с self-reflection, конфликтом или текущей жизненной ситуацией
**When** система определяет, что запрос выходит за продуктовую рамку
**Then** бот мягко обозначает границу продукта и предлагает вернуться к разбору ситуации пользователя
**And** не переключается в режим general-purpose assistant по технологиям, бизнесу или другим произвольным темам

**Given** пользователь затрагивает тему работы, бизнеса, денег или технологий как часть своей текущей жизненной ситуации
**When** система определяет, что эта тема помогает лучше разобрать пользовательский контекст
**Then** бот продолжает reflective flow через призму ситуации пользователя
**And** не отклоняет запрос только по ключевым словам без учета контекста

### Story 1.6: Завершение сессии с takeaway и next-step options

As a пользователь, который прошел через reflective conversation,
I want получить ясное завершение с кратким takeaway и несколькими следующими шагами,
So that я выхожу из сессии с большей ясностью и понимаю, что делать дальше.

**Implements:** FR9, FR10

**Acceptance Criteria:**

**Given** пользователь прошел основной reflective flow текущей сессии
**When** продукт определяет, что разговор достиг suitable closure point
**Then** бот выдает end-of-session takeaway, который кратко отражает суть ситуации
**And** takeaway остается понятным, calm и grounded in the session context

**Given** сессия подходит к завершению
**When** бот формирует финальный ответ
**Then** пользователь получает от 1 до 3 next-step options or recommendations
**And** эти варианты выглядят реалистично, неосуждающе и соответствуют разобранной ситуации

**Given** продукт завершает текущую reflective session
**When** финальное сообщение отправляется пользователю
**Then** ответ содержит ощущение closure and orientation rather than abrupt stop
**And** не сводится только к generic summary без actionable next-step guidance

**Given** в течение сессии пользователь так и не пришел к полной определенности
**When** продукт формирует final takeaway
**Then** бот может признать сохраняющуюся неопределенность или ambiguity
**And** все равно предлагает безопасный и понятный ближайший шаг вместо ложной уверенности

**Given** пользователь находился в `fast` mode
**When** сессия завершается
**Then** финальный takeaway и next steps остаются краткими и low-burden
**And** итог не требует от пользователя дополнительного длинного взаимодействия для получения value

**Given** пользователь находился в `deep` mode
**When** сессия завершается
**Then** финальный takeaway может быть более подробным и отражать deeper reflective work
**And** структура closure все равно остается readable для Telegram и не превращается в wall of text

## Epic 2: Continuity и память между сессиями

Пользователь может вернуться позже и продолжить разговор без повторного полного объяснения контекста, а продукт сохраняет только нужную durable memory.

### Story 2.1: Генерация session summary после завершения сессии

As a пользователь, который завершил reflective session,
I want чтобы продукт создавал краткое структурированное summary моей сессии,
So that в будущем разговор может продолжиться с учетом уже разобранного контекста.

**Implements:** FR11

**Acceptance Criteria:**

**Given** пользователь завершил сессию и продукт определил suitable closure point
**When** основной финальный ответ уже отправлен пользователю
**Then** система запускает генерацию session summary как post-response process
**And** этот процесс не блокирует user-facing reply path

**Given** summary generation запускается после завершения сессии
**When** система формирует durable summary artifact
**Then** summary сохраняет ключевые факты, основные эмоциональные напряжения и релевантный next-step context из сессии
**And** не превращается в сырой transcript dump или длинный свободный пересказ всего диалога

**Given** продукт использует summary-based continuity
**When** session summary создается
**Then** summary соответствует предсказуемой structured schema
**And** artifact пригоден для дальнейшего машинного использования в future session recall

**Given** пользовательская сессия содержит шум, противоречия или не до конца проясненные детали
**When** summary generation завершается
**Then** summary использует осторожную формулировку для uncertain points
**And** не фиксирует неоднозначные выводы как достоверные факты

**Given** generation pipeline завершилась с ошибкой или частичным сбоем
**When** система не может успешно сохранить summary
**Then** сбой не ломает уже завершенную пользовательскую сессию
**And** система создает retry or failure signal для последующей обработки без silent loss

**Given** продукт работает в доверительном и privacy-sensitive домене
**When** summary сохраняется как durable memory artifact
**Then** оно содержит только информацию, нужную для continuity
**And** не хранит избыточные raw message fragments без явной необходимости

### Story 2.2: Сохранение durable memory без долгого хранения raw transcript

As a пользователь, который возвращается к продукту со временем,
I want чтобы система сохраняла только нужную continuity memory, а не полный сырой диалог,
So that мой контекст остается доступным без лишнего накопления чувствительных данных.

**Implements:** FR12, FR15, FR34

**Acceptance Criteria:**

**Given** session summary успешно создано после завершения сессии
**When** система записывает continuity memory в durable storage
**Then** сохраняются structured summary data и разрешенные profile facts, нужные для future recall
**And** full raw transcript не используется как основной durable memory artifact

**Given** пользовательская сессия содержит raw messages, промежуточные уточнения и эмоционально чувствительные fragments
**When** система завершает processing window этой сессии
**Then** raw conversational content не удерживается дольше срока, необходимого для ответа и summary generation
**And** durable storage boundary остается построенной вокруг summary/profile model

**Given** продукт использует accumulated memory across sessions
**When** continuity data сохраняется в persistent layer
**Then** summary artifacts и profile facts хранятся в отдельных, понятных memory scopes
**And** система не смешивает их с transient message-processing data

**Given** оператор или внутренняя система работают с continuity data
**When** происходит обычный operational access
**Then** доступ строится вокруг summary/profile artifacts и metadata
**And** routine workflows не требуют раскрытия полного session transcript

**Given** система должна поддерживать privacy-sensitive deletion and retention rules
**When** memory artifacts сохраняются после сессии
**Then** они помечаются так, чтобы их можно было удалить или обновить в рамках user data lifecycle
**And** retention model остается совместимой с future deletion workflows

**Given** durable memory persistence дала сбой
**When** session summary уже была создана, но запись в persistent layer не завершилась корректно
**Then** система создает observable failure signal и safe retry path
**And** не заменяет durable persistence fallback хранением полного transcript на неопределенный срок

### Story 2.3: Использование prior memory при старте новой сессии

As a пользователь, который возвращается в продукт позже,
I want чтобы бот помнил важный контекст из прошлых сессий и использовал его в новом разговоре,
So that мне не нужно каждый раз заново объяснять свою ситуацию с нуля.

**Implements:** FR4, FR13, FR14

**Acceptance Criteria:**

**Given** пользователь уже имеет сохраненные summary artifacts или profile facts из прошлых сессий
**When** он начинает новую сессию в Telegram
**Then** система может загрузить релевантную prior memory для этого пользователя
**And** использует ее как continuity context для новой reflective session

**Given** prior memory найдена для returning user
**When** продукт формирует ранние шаги новой сессии
**Then** бот учитывает важный ранее сохраненный контекст и recurring patterns
**And** не требует от пользователя повторно пересказывать уже известные ключевые элементы без необходимости

**Given** сохраненная memory относится только к части текущей ситуации или устарела
**When** новая сессия начинается
**Then** система использует prior context как вспомогательную, а не абсолютную основу
**And** не предполагает автоматически, что старая memory полностью описывает текущую ситуацию

**Given** пользователь возвращается после предыдущей полезной сессии
**When** продукт продолжает новый reflective flow
**Then** continuity повышает релевантность follow-up prompts, reflections и next-step framing
**And** новая сессия ощущается как продолжение, а не старт с полного нуля

**Given** у пользователя нет prior memory или релевантная continuity data отсутствует
**When** новая сессия стартует
**Then** продукт корректно работает как clean-session experience
**And** отсутствие памяти не ломает основной user flow

**Given** retrieval или memory loading для returning user завершились ошибкой
**When** система не может надежно получить prior context
**Then** сессия продолжает работать без continuity enhancement
**And** пользователь не видит техническую ошибку или ложное заявление о том, что система что-то помнит

### Story 2.4: Tentative memory recall и корректировка пользователем

As a returning user,
I want чтобы бот вспоминал прошлый контекст осторожно и позволял мне легко его скорректировать,
So that continuity feels helpful rather than creepy or overconfident.

**Implements:** FR13, FR14

**Acceptance Criteria:**

**Given** продукт использует prior memory в новой сессии
**When** бот ссылается на ранее сохраненный контекст
**Then** memory recall phrasing звучит tentative rather than absolute
**And** не создает впечатления всеведущего или surveillance-like memory behavior

**Given** бот упоминает сохраненный ранее контекст
**When** пользователь явно или неявно показывает, что память неточна, устарела или не подходит к текущей ситуации
**Then** система принимает эту коррекцию без defensive response
**And** immediately yields to the user’s new framing of the situation

**Given** memory recall оказалось частично неверным
**When** пользователь продолжает новую сессию после коррекции
**Then** дальнейший reflective flow строится уже на обновленном пользовательском контексте
**And** бот не продолжает повторять ошибочную memory as if it were true

**Given** confidence в retrieved memory низкая или context relevance uncertain
**When** система решает, использовать ли prior memory в разговоре
**Then** продукт либо использует более осторожную phrasing, либо не поднимает эту memory явно
**And** не делает сильных continuity claims при низкой уверенности

**Given** у пользователя есть чувствительность к тому, как продукт “помнит” прошлое
**When** бот ссылается на prior context
**Then** recall language остается supportive, humble and low-pressure
**And** continuity experience уменьшает effort for the user, а не усиливает дискомфорт или ощущение слежки

**Given** система не уверена, что memory recall уместен именно в этом моменте диалога
**When** новый session flow уже развивается естественно без необходимости explicit recall
**Then** продукт может использовать память только internally to improve relevance
**And** не обязан каждый раз явно озвучивать, что он что-то помнит

### Story 2.5: Conservative memory promotion и safe handling sensitive context

As a пользователь, который делится личным и чувствительным контекстом,
I want чтобы продукт сохранял в durable memory только действительно полезные и безопасные элементы,
So that continuity remains trustworthy and does not overstore risky or intimate details.

**Implements:** FR12, FR13, FR14, FR15, FR34

**Acceptance Criteria:**

**Given** session summary и candidate profile facts сформированы после сессии
**When** система решает, что из этого может стать durable memory
**Then** в persistent continuity layer попадают только элементы, полезные для future relevance and support
**And** не every session detail автоматически промотируется в long-term memory

**Given** пользовательская сессия содержит highly sensitive, crisis-related или ambiguous content
**When** система оценивает memory promotion eligibility
**Then** high-risk content либо не промотируется в standard durable memory, либо получает ограниченный handling path
**And** продукт не использует такую информацию бездумно как обычный continuity context

**Given** candidate memory artifact основан на uncertain interpretation или weak evidence
**When** система применяет promotion rules
**Then** такой контент не фиксируется как durable fact without stronger confidence
**And** ambiguous inferences остаются outside trusted long-term profile memory

**Given** continuity model включает profile facts alongside session summaries
**When** система добавляет новый profile fact
**Then** fact сохраняется в typed and reviewable structure
**And** его происхождение остается совместимым с later correction, deletion or replacement

**Given** продукт использует promoted memory в будущих сессиях
**When** ранее сохраненный факт или summary element позже оказывается неверным, устаревшим или больше неуместным
**Then** система должна позволять его обновление, downgrade или removal from continuity use
**And** durable memory model не предполагает необратимость once saved

**Given** memory promotion pipeline сталкивается с ошибкой rules evaluation или persistence
**When** система не может надежно решить, что безопасно сохранять надолго
**Then** default behavior остается conservative
**And** продукт предпочитает сохранить меньше memory rather than overstore sensitive or low-confidence content

## Epic 3: Safety и мягкая эскалация кризисных сценариев

Продукт распознает red flags, корректно прерывает обычный flow, мягко переводит пользователя в safer path и уведомляет оператора без routine exposure к содержимому.

### Story 3.1: Обнаружение red-flag сигналов в пользовательских сообщениях

As a пользователь в потенциально кризисном состоянии,
I want чтобы продукт распознавал признаки self-harm risk, dangerous abuse и других высокорисковых состояний,
So that обычный reflective flow не продолжался там, где нужен более безопасный сценарий.

**Implements:** FR16

**Acceptance Criteria:**

**Given** пользователь отправляет новое сообщение в рамках active or newly started session
**When** система обрабатывает текст сообщения
**Then** продукт оценивает его на наличие red-flag signals before continuing the normal reflective flow
**And** эта проверка происходит в основном conversational path без отдельного ручного запуска

**Given** сообщение содержит явные или достаточно сильные признаки crisis, self-harm ideation, dangerous abuse или сопоставимого safety risk
**When** система завершает red-flag evaluation
**Then** сообщение помечается как requiring crisis-aware handling
**And** normal reflective continuation не считается безопасным default path

**Given** пользовательский текст может быть эмоционально тяжелым, но не обязательно crisis-level
**When** система выполняет red-flag detection
**Then** продукт различает обычную эмоциональную перегрузку и более опасные safety patterns
**And** не эскалирует каждый emotionally intense message как crisis by default

**Given** система находит uncertain or borderline signal
**When** confidence недостаточна для жесткого crisis decision
**Then** результат detection остается пригодным для более осторожного next-step handling
**And** продукт не обязан сразу вести себя так, будто severe crisis уже точно установлен

**Given** пользователь отправляет несколько сообщений подряд в одной сессии
**When** новые сообщения продолжают поступать
**Then** red-flag detection применяется к новым входящим сообщениям throughout the conversation
**And** ранее безопасная сессия может быть переведена в crisis-aware path при появлении нового risk signal

**Given** detection step дает ошибку или не может надежно завершиться
**When** система не уверена в результате проверки
**Then** failure становится observable для системы
**And** продукт не должен silently assume full safety if critical detection failed

### Story 3.2: Переключение из normal flow в crisis-aware escalation flow

As a пользователь, у которого в сообщении обнаружены кризисные сигналы,
I want чтобы продукт корректно переключал разговор из обычного reflective режима в более безопасный crisis-aware flow,
So that система не продолжает неподходящий normal conversation path в момент повышенного риска.

**Implements:** FR17, FR20

**Acceptance Criteria:**

**Given** red-flag detection пометила текущее сообщение или сессию как requiring crisis-aware handling
**When** продукт выбирает следующий conversational step
**Then** normal reflective flow прерывается
**And** система переходит в dedicated crisis-aware escalation path

**Given** кризисный сигнал обнаружен в середине уже идущей reflective session
**When** система формирует следующий ответ
**Then** ранее активный normal flow больше не продолжается как ни в чем не бывало
**And** transition происходит в рамках той же пользовательской сессии без сломанного или противоречивого state

**Given** пользователь до этого находился в `fast` или `deep` mode
**When** crisis-aware path активирован
**Then** прежний conversational mode перестает управлять следующим unsafe step
**And** safety routing получает приоритет над mode-specific flow logic

**Given** detection result имеет high enough confidence для escalation
**When** система переключает flow
**Then** дальнейшее response generation использует crisis-aware handling rules
**And** не выдает стандартный situation breakdown, обычные next-step suggestions или routine reflective prompts

**Given** кризисный trigger активировал escalation path
**When** система завершает routing decision
**Then** внутреннее состояние сессии отражает, что она находится в crisis-aware mode
**And** последующие downstream actions могут опираться на этот state для messaging, resources and alerts

**Given** flow switching step не смог завершиться корректно
**When** продукт не может надежно перевести сессию в crisis-aware path
**Then** failure становится observable и трактуется как safety-relevant issue
**And** система не должна silently fall back to ordinary reflective continuation

### Story 3.3: Humane escalation messaging и объяснение границ продукта

As a пользователь в кризисном или потенциально опасном состоянии,
I want чтобы продукт отвечал бережно, серьезно и честно о своих границах,
So that я не чувствую отвержения и понимаю, что мне нужна более подходящая форма помощи.

**Implements:** FR18

**Acceptance Criteria:**

**Given** сессия уже переведена в crisis-aware escalation flow
**When** бот формирует escalation message
**Then** ответ сначала признает серьезность состояния пользователя в calm and humane tone
**And** не звучит как cold refusal, legal disclaimer dump или abrupt system rejection

**Given** продукт не должен притворяться терапевтом, врачом или crisis service
**When** бот объясняет свои границы в crisis-aware path
**Then** сообщение ясно обозначает, что продукт не является достаточной формой помощи в этой ситуации
**And** делает это без diagnostic language, moral judgment или shaming tone

**Given** escalation message отправляется вместо обычного reflective continuation
**When** пользователь читает ответ в Telegram
**Then** текст остается readable, direct and emotionally supportive
**And** не превращается в длинный перегруженный блок текста, ухудшающий восприятие в стрессовом состоянии

**Given** crisis trigger активирован
**When** бот завершает основную часть escalation messaging
**Then** message направляет пользователя toward safer support path
**And** framing делает акцент на безопасности и следующем шаге, а не на том, что продукт “отказывается помогать”

**Given** сообщение пользователя содержит потенциально ложноположительный или не до конца ясный risk signal
**When** бот формирует escalation response
**Then** язык остается достаточно мягким, чтобы не усилить стыд, страх или сопротивление
**And** не фиксирует кризисную интерпретацию более жестко, чем это оправдано текущим контекстом

**Given** generation escalation copy fails or uses disallowed unsafe phrasing
**When** система проверяет готовый response before send
**Then** unsafe output не должен отправляться пользователю без контроля
**And** failure должен становиться observable как safety-critical messaging issue

### Story 3.4: Показ crisis-help resources и safer next action

As a пользователь, для которого сработала crisis-aware escalation,
I want получить понятные ресурсы помощи и ближайший безопасный следующий шаг,
So that после ответа бота у меня остается реальная опора, а не только сообщение о риске.

**Implements:** FR19

**Acceptance Criteria:**

**Given** кризисный или high-risk signal уже перевел сессию в escalation flow
**When** бот формирует support-oriented follow-up
**Then** пользователь получает crisis-help resources или support links, подходящие для escalation scenario
**And** эти ресурсы показываются как practical next help option, а не как формальная приписка в конце

**Given** escalation response должен быть actionable
**When** бот завершает crisis-aware message
**Then** сообщение включает safer next action, который пользователь может понять и выполнить immediately or soon
**And** next action сформулирован ясно, calmly and without overload

**Given** продукт использует статический curated list crisis resources в MVP
**When** соответствующие resources выводятся пользователю
**Then** система подставляет доступные support links or contact options из approved source list
**And** не генерирует произвольные или неподтвержденные crisis destinations on the fly

**Given** пользователь находится в остром эмоциональном состоянии
**When** resources и safer next action показываются в Telegram
**Then** presentation остается readable, low-burden and scannable
**And** бот не смешивает practical support resources с длинным reflective content block

**Given** suitable crisis resources недоступны, incomplete или не могут быть reliably retrieved
**When** система не может показать ожидаемый support set
**Then** failure становится observable как safety-relevant issue
**And** продукт по-прежнему выдает минимально безопасный escalation framing вместо silent omission of help resources

**Given** escalation path уже активирован, но пользовательский контекст остается partially uncertain
**When** бот предлагает resources and next action
**Then** support guidance остается серьезной и protective
**And** не смягчается до обычного reflective advice только потому, что деталь ситуации еще не полностью ясна

### Story 3.5: Operator alerting без routine exposure к содержимому

As an operator,
I want получать alerts по crisis-routed sessions без постоянного доступа к полному содержимому переписки,
So that я могу реагировать на safety-relevant events without turning the product into a surveillance system.

**Implements:** FR35, FR36

**Acceptance Criteria:**

**Given** система перевела пользовательскую сессию в crisis-aware escalation flow
**When** crisis routing подтверждено как safety-relevant event
**Then** operator alert создается и отправляется в определенный operational channel
**And** alert содержит достаточно signal-level information для реагирования

**Given** alert формируется для founder/operator
**When** он получает notification о crisis-routed session
**Then** alert не включает full raw transcript by default
**And** routine operator visibility ограничивается metadata, risk classification и минимально необходимым operational context

**Given** crisis-routed sessions могут случаться повторно или параллельно
**When** система генерирует несколько alerts
**Then** alerts остаются individually traceable and observable
**And** оператор может отличить новые события от повторных или retry-deliveries

**Given** alert delivery в operational channel завершилась ошибкой
**When** notification не была доставлена надежно
**Then** failure становится operator-visible или system-visible как отдельный incident signal
**And** событие не теряется silently

**Given** operator alerting должно сохранять privacy boundary продукта
**When** строится обычный monitoring workflow around crisis events
**Then** design поддерживает реагирование без routine reading of sensitive user content
**And** доступ к более глубокому содержимому не становится default operational behavior

**Given** alerting pipeline сработала на false positive или borderline case
**When** оператор видит notification
**Then** alert framing остается достаточно точным, чтобы не представлять каждое событие как одинаково severe
**And** alert model допускает later review and reclassification without collapsing the privacy boundary

### Story 3.6: Controlled investigation path для критических safety-инцидентов

As an operator,
I want чтобы продукт поддерживал контролируемый path для расследования критических safety-инцидентов,
So that exceptional review остается возможным без превращения transcript access в routine operator behavior.

**Implements:** FR40

**Acceptance Criteria:**

**Given** crisis-routed session требует дополнительного operational review
**When** возникает обоснованная необходимость deeper investigation
**Then** система поддерживает controlled and policy-governed access path
**And** такой path не является default mode обычной operator работы

**Given** operator использует investigation path для критического случая
**When** access к дополнительному контексту действительно предоставляется
**Then** событие остается auditable и ограниченным по назначению
**And** продукт не превращает exceptional access в routine transcript visibility

**Given** investigation path или reclassification workflow завершились ошибкой
**When** система не может надежно завершить controlled review
**Then** failure становится observable как safety/ops issue
**And** продукт не должен silently lose traceability of the incident

**Given** borderline or false-positive events встречаются в системе со временем
**When** operator later reviews alert history and classifications
**Then** workflow поддерживает последующую reclassification and learning signal
**And** это можно использовать для улучшения safety behavior без снятия privacy boundary by default

### Story 3.7: Graceful step-down after false positive escalation

As a user affected by an overly strong crisis interpretation,
I want чтобы продукт мягко снимал слишком сильную crisis framing, если она не соответствует моему реальному контексту,
So that trust не разрушается даже при false positive safety handling.

**Implements:** FR18

**Acceptance Criteria:**

**Given** crisis escalation была активирована, но дальнейший conversational context показывает, что initial interpretation была слишком сильной
**When** система или последующий flow определяет false positive or over-escalation
**Then** продукт может мягко step down from crisis framing
**And** переход обратно не звучит как обвинение пользователя или system mistake dump

**Given** пользователь остается уязвимым даже при false positive
**When** crisis framing смягчается
**Then** language сохраняет уважительный, calm and non-shaming tone
**And** дальнейший flow не делает резкого скачка обратно в обычный reflective mode без мягкого transition

**Given** step-down происходит после уже отправленного escalation message
**When** продукт продолжает разговор
**Then** normal reflective flow возвращается через gentle bridging language
**And** пользователь не получает contradictory or whiplash-like messaging

**Given** step-down handling itself fails or leaves state uncertain
**When** система не может надежно завершить false-positive recovery
**Then** failure становится observable как safety-relevant issue
**And** продукт не делает вид, что graceful recovery already happened if state is unresolved

## Epic 4: Монетизация, доступ и continuity-based premium

Пользователь получает ограниченный free experience, затем понятный premium boundary, может оплатить доступ и понимать свой текущий access state.

### Story 4.1: Ограниченный free usage и учет usage threshold

As a пользователь, который только начинает пользоваться продуктом,
I want получить ограниченный бесплатный доступ до paywall,
So that я могу сначала почувствовать ценность продукта, прежде чем принимать решение об оплате.

**Implements:** FR21

**Acceptance Criteria:**

**Given** пользователь новый или еще не исчерпал бесплатный лимит
**When** он начинает или завершает eligible reflective sessions
**Then** система учитывает использование в рамках defined free-usage model
**And** пользователь может продолжать получать free access до достижения configured threshold

**Given** продукт использует ограниченный free usage before premium boundary
**When** usage events записываются в access-control logic
**Then** учитываются только те interaction outcomes, которые действительно считаются against free allowance
**And** accidental retries, duplicate inbound events или невалидные transitions не должны ложно расходовать free quota

**Given** пользователь еще находится в free tier
**When** он входит в новую сессию до достижения threshold
**Then** основной reflective flow продолжает работать без paywall interruption
**And** пользователь не сталкивается с premature monetization blocking before felt value

**Given** пользователь достигает configured free-usage threshold
**When** система пересчитывает его access eligibility
**Then** access state обновляется так, чтобы пользователь больше не считался fully eligible for unrestricted free continuation
**And** продукт готов перейти к следующему premium-boundary step without silent inconsistency

**Given** access counting or threshold evaluation завершились ошибкой
**When** система не может надежно определить оставшийся free allowance
**Then** failure становится observable для системы
**And** пользователь не должен произвольно терять доступ из-за silent counting error

**Given** free-usage model со временем может уточняться продуктово
**When** система хранит usage and threshold state
**Then** модель остается explicit and reviewable at the access-control layer
**And** billing/accounting logic не размазывается по conversation core

### Story 4.2: Paywall после felt value с continuity-based framing

As a пользователь, который уже получил пользу от первых сессий,
I want увидеть paywall в понятный и ненавязчивый момент,
So that я понимаю, за что именно предлагается платить и не чувствую, что меня прервали слишком рано.

**Implements:** FR22, FR28

**Acceptance Criteria:**

**Given** пользователь уже достиг configured free-usage threshold
**When** он пытается продолжить доступ beyond free allowance
**Then** продукт показывает premium boundary/paywall
**And** это происходит после того, как пользователь уже успел получить реальную core value от продукта

**Given** paywall показывается пользователю в Telegram-native context
**When** бот объясняет, почему теперь предлагается premium access
**Then** premium framing строится вокруг continuity, remembered context и reduced emotional setup cost
**And** не сводится к примитивному message-limit framing без объяснения product value

**Given** пользователь достиг premium boundary после emotionally sensitive interaction
**When** paywall message отправляется
**Then** сообщение остается calm, respectful and readable
**And** не ломает trust резкой, холодной или manipulative monetization tone

**Given** пользователь столкнулся с paywall
**When** система показывает premium prompt
**Then** пользователь понимает, что именно ограничено в бесплатном режиме и какую ценность открывает paid access
**And** access limits and premium benefits communicated clearly enough to support informed choice

**Given** у пользователя есть сохраненная continuity value from prior sessions
**When** premium boundary объясняется
**Then** продукт может связывать premium с сохранением и развитием этой continuity value
**And** не создает впечатления, что already-earned context is being emotionally held hostage

**Given** paywall rendering or access-state transition сработали некорректно
**When** система не может надежно показать correct premium boundary state
**Then** failure становится observable
**And** пользователь не должен получать contradictory messages about whether access is free or paid

### Story 4.3: Запуск supported payment flow для premium access

As a пользователь, который решил оплатить premium access,
I want запустить понятный и поддерживаемый payment flow,
So that я могу быстро и безопасно разблокировать платный доступ.

**Implements:** FR23

**Acceptance Criteria:**

**Given** пользователь находится на premium boundary и решил продолжить с оплатой
**When** он выбирает действие оплаты в доступном Telegram-native flow
**Then** система запускает supported payment flow через configured provider path
**And** user journey остается понятным и не требует от пользователя разбираться во внутренних billing details

**Given** продукт поддерживает Telegram Stars и/или ЮKassa в MVP perimeter
**When** пользователь инициирует premium purchase
**Then** payment flow создается через approved payment provider integration
**And** conversation core не берет на себя provider-specific business logic beyond the billing boundary

**Given** payment initiation успешно создана
**When** пользователь переходит в payment process
**Then** система сохраняет достаточно state and reference data для последующего reconciliation of payment result
**And** не требует хранения raw payment instrument details внутри продукта

**Given** пользователь передумал, закрыл flow или payment initiation не завершилась
**When** purchase flow не доходит до успешной оплаты
**Then** access state пользователя не повышается prematurely
**And** продукт остается в согласованном pre-payment or unpaid state

**Given** payment initiation step завершилась ошибкой
**When** система не может надежно создать payment flow
**Then** failure становится observable и user-visible в спокойной понятной форме
**And** пользователь не остается в неясности, была ли оплата реально запущена

**Given** пользователь инициирует оплату несколько раз из-за retry, lag or confusion
**When** система обрабатывает repeated initiation attempts
**Then** billing layer сохраняет согласованность purchase intent state
**And** duplicate initiation не должна создавать неконтролируемые contradictory access outcomes

### Story 4.4: Обработка payment events и обновление access state

As a paying user,
I want чтобы продукт корректно распознавал результаты оплаты и обновлял мой access state,
So that мой доступ к premium работает предсказуемо и без путаницы.

**Implements:** FR24, FR41

**Acceptance Criteria:**

**Given** payment provider отправляет inbound event о purchase, renewal, failure, cancellation или related billing state
**When** система получает этот callback or provider event
**Then** billing layer валидирует подлинность события
**And** необработанные или неподтвержденные callbacks не меняют пользовательский access state

**Given** подтвержденный payment success event получен системой
**When** событие проходит reconciliation with stored purchase intent or billing reference
**Then** access state пользователя обновляется до соответствующего paid status
**And** продукт может использовать этот state в дальнейших premium access decisions

**Given** payment failure, timeout, delayed confirmation или cancellation event получен
**When** система обрабатывает billing update
**Then** access state изменяется только в соответствии с подтвержденным event outcome
**And** пользователь не получает premature premium access on ambiguous billing results

**Given** payment provider может прислать duplicate callbacks or retries
**When** система повторно получает уже обработанное событие
**Then** обработка остается idempotent
**And** duplicate event не приводит к двойному изменению access state, двойной активации или contradictory billing record

**Given** provider event не может быть корректно сопоставлен с ожидаемым payment context
**When** reconciliation fails or remains incomplete
**Then** failure становится observable для системы и operator workflow
**And** access state не меняется на основании неясного billing signal

**Given** access state был обновлен на основании confirmed payment result
**When** пользователь снова взаимодействует с продуктом
**Then** система применяет актуальный paid or unpaid status consistently
**And** conversation layer не опирается на устаревший access state cache

### Story 4.5: Просмотр текущего access/subscription status пользователем

As a user with free or paid access,
I want видеть мой текущий access or subscription status,
So that я понимаю, доступен ли мне premium и в каком состоянии находится моя подписка или покупка.

**Implements:** FR25

**Acceptance Criteria:**

**Given** у пользователя уже есть определенный access state в системе
**When** он запрашивает свой current status через supported product flow
**Then** продукт показывает актуальный access/subscription state в понятной форме
**And** сообщение не требует от пользователя интерпретировать внутренние billing codes or technical statuses

**Given** пользователь находится в free tier
**When** он смотрит свой статус
**Then** продукт ясно показывает, что доступ пока бесплатный или ограниченный
**And** состояние communicated consistently with configured free-usage model

**Given** пользователь имеет активный paid access
**When** он запрашивает статус
**Then** продукт показывает, что premium currently active
**And** status messaging не противоречит последним confirmed billing events

**Given** у пользователя есть pending, failed, canceled or otherwise non-active billing state
**When** он смотрит access status
**Then** система отражает это состояние достаточно ясно для понимания next step
**And** пользователь не остается в silent ambiguity about whether access should work

**Given** access/subscription state не может быть надежно загружен или текущий billing context inconsistent
**When** пользователь запрашивает статус
**Then** продукт сообщает о проблеме спокойно и понятно
**And** failure становится observable для system/operator workflows without inventing false status certainty

**Given** conversation layer использует access state для monetization behavior
**When** status shown to the user
**Then** displayed state соответствует тому же источнику истины, который используется для access decisions
**And** пользователь не получает один статус в интерфейсе и другой в реальном поведении продукта

### Story 4.6: Запрос cancellation или non-renewal paid access

As a paying user,
I want иметь понятный способ отменить продление или прекратить платный доступ,
So that я сохраняю контроль над подпиской и не чувствую себя запертым в оплате.

**Implements:** FR26

**Acceptance Criteria:**

**Given** у пользователя есть active or renewable paid access
**When** он инициирует cancellation or non-renewal request через supported product flow
**Then** система принимает этот запрос и связывает его с соответствующим billing context
**And** пользователь получает понятное подтверждение, что запрос на отмену или непродление зарегистрирован

**Given** billing model поддерживает non-renewal rather than immediate cutoff
**When** cancellation request обработан корректно
**Then** access state обновляется в соответствии с supported billing behavior
**And** продукт не лишает пользователя доступа раньше, чем это допускает подтвержденная billing policy

**Given** cancellation request поступила для пользователя без active paid state или с inconsistent billing context
**When** система пытается обработать запрос
**Then** продукт отвечает понятным статусом без misleading confirmation
**And** не создает ложное впечатление, что отмена сработала там, где активного paid access не было

**Given** provider-side cancellation or non-renewal требует отдельного взаимодействия или подтверждения
**When** продукт не может завершить отмену полностью только своими силами
**Then** пользователю показывается точный следующий шаг или limitation of the current flow
**And** система не утверждает, что cancellation complete, если это не подтверждено

**Given** cancellation workflow дает ошибку или остается в неопределенном состоянии
**When** система не может надежно завершить запрос
**Then** failure становится observable и user-visible в спокойной форме
**And** пользователь не остается в silent ambiguity about whether renewal is still active

**Given** пользователь после cancellation/non-renewal снова проверяет свой статус
**When** access/subscription state отображается в продукте
**Then** он согласован с последним confirmed cancellation-related outcome
**And** monetization behavior не противоречит communicated status

### Story 4.7: Continuity across free and paid states

As a user moving between free and paid access states,
I want чтобы continuity value продукта сохранялась и в free, и в paid model без нелогичных разрывов,
So that premium boundary feels like an upgrade in continuity experience, not a break in my relationship with the product.

**Implements:** FR27

**Acceptance Criteria:**

**Given** у пользователя уже есть накопленный continuity context from prior sessions
**When** он достигает premium boundary или меняет access state
**Then** продукт сохраняет already-earned continuity artifacts в согласованном виде
**And** переход между free and paid states не ломает core memory model

**Given** пользователь остается на free tier после достижения ограничений или возвращается в unpaid state
**When** система применяет соответствующие access rules
**Then** continuity and access distinctions обрабатываются по defined policy
**And** продукт не ведет себя так, будто вся ранее накопленная ценность внезапно исчезла без объяснения

**Given** пользователь активировал paid access
**When** продукт продолжает будущие сессии
**Then** premium experience может усиливать continuity-based value и снижать emotional setup cost
**And** premium differentiation ощущается как meaningful upgrade rather than arbitrary gate

**Given** access state пользователя изменился из-за confirmed billing event, cancellation or renewal outcome
**When** новый conversational session начинается
**Then** система применяет continuity behavior, согласованное с актуальным access state
**And** не использует устаревшую free/paid interpretation of the user’s entitlements

**Given** в billing/access layer возникла inconsistency around free/paid transition
**When** продукт пытается определить, как вести себя с continuity features
**Then** failure становится observable
**And** пользователь не должен видеть contradictory behavior where continuity is both promised and denied at once

**Given** monetization design не должна восприниматься как emotional hostage-taking
**When** продукт объясняет различия между free and paid continuity experience
**Then** communication остается respectful and trust-preserving
**And** не использует already-stored user context как pressure tactic for conversion

## Epic 5: Retention и повторное возвращение (Post-MVP / Phase 2)

Пользователь получает дополнительную ценность вне acute момента за счет weekly insight и continuity-driven repeat usage.
Этот эпик является отложенным слоем retention и не должен трактоваться как phase-1 blocker для запуска MVP core reflection, continuity, safety и billing flows.

### Story 5.1: Генерация periodic reflective insight на основе prior sessions

As a returning user,
I want чтобы продукт мог формировать периодический reflective insight на основе прошлых сессий и накопленного контекста,
So that я получаю дополнительную ценность даже вне острого момента и лучше вижу повторяющиеся паттерны.

**Implements:** FR29

**Acceptance Criteria:**

**Given** у пользователя есть достаточный continuity context from prior sessions
**When** система запускает periodic insight generation
**Then** продукт формирует reflective insight на основе prior summaries and retained context
**And** результат не выглядит как generic, one-size-fits-all content blast

**Given** insight строится на historical continuity data
**When** система генерирует insight content
**Then** текст отражает релевантные patterns, shifts or recurring themes from the user’s prior sessions
**And** не выдумывает глубокие выводы, если накопленного материала недостаточно

**Given** accumulated context слабый, слишком редкий или низкого качества для meaningful insight
**When** periodic generation запускается
**Then** система может не генерировать full reflective insight или выдать более conservative version
**And** не создает фальшивую персонализацию на слабой evidence base

**Given** weekly/periodic insight не должен ломать trust модели продукта
**When** insight подготавливается для пользователя
**Then** language остается calm, reflective and low-pressure
**And** не превращается в manipulative retention copy или productivity-nag messaging

**Given** periodic insight generation выполняется вне основного user conversation path
**When** background generation starts or completes
**Then** этот процесс использует scheduler/job seam and asynchronous processing model
**And** не влияет на latency active conversational sessions

**Given** insight generation завершилась ошибкой или не смогла опереться на reliable continuity data
**When** система не может получить quality result
**Then** failure становится observable
**And** продукт предпочитает не отправлять слабый или misleading insight вместо того, чтобы отправить любой ценой

### Story 5.2: Delivery weekly insight без необходимости вручную стартовать сессию

As a user who may not actively reopen the bot every time,
I want получать periodic reflective insight без ручного запуска новой сессии,
So that продукт может мягко возвращать ценность и напоминать о continuity outside acute moments.

**Implements:** FR30

**Acceptance Criteria:**

**Given** для пользователя уже подготовлен valid reflective insight
**When** наступает scheduled delivery time or delivery condition
**Then** система отправляет weekly/periodic insight пользователю без необходимости вручную стартовать новую session
**And** delivery происходит через supported Telegram delivery path

**Given** insight доставляется proactively rather than in-session
**When** пользователь получает это сообщение
**Then** message feels like low-pressure reflective support
**And** не воспринимается как spammy nudge, aggressive re-engagement tactic или generic notification blast

**Given** delivery model зависит от scheduler/job execution
**When** система запускает batch or scheduled insight delivery
**Then** delivery pipeline использует explicit async/scheduled flow
**And** не блокирует active conversational traffic or main request path

**Given** пользователь недоступен, delivery fails or Telegram delivery path returns error
**When** система не может успешно отправить insight
**Then** failure становится observable и traceable
**And** продукт не предполагает silently, что value already delivered

**Given** пользователю не следует получать irrelevant or low-quality periodic message
**When** insight delivery readiness оценивается перед отправкой
**Then** система отправляет только prepared and valid insight artifacts
**And** не шлет placeholder, empty or weak-content message ради самого факта касания

**Given** пользователь получает periodic insight и решает вернуться в продукт
**When** он отвечает на insight message или открывает новый conversation flow после него
**Then** продукт может естественно продолжить continuity-aware interaction
**And** delivery message служит мягкой точкой входа, а не отдельным disconnected content object

### Story 5.3: Repeat-use experience вне acute conflict moments

As a user who returns in calmer periods,
I want чтобы продукт оставался полезным не только в момент острого конфликта,
So that у меня появляется причина возвращаться к нему регулярно, а не только в peak pain moments.

**Implements:** FR31

**Acceptance Criteria:**

**Given** пользователь возвращается в продукт не из-за нового acute conflict, а в более спокойный период
**When** он начинает новую continuity-aware interaction
**Then** продукт может поддержать reflective use case outside acute distress
**And** новый flow не требует обязательного crisis-like trigger or peak-emotion context to feel relevant

**Given** у пользователя уже есть accumulated continuity from prior sessions
**When** продукт взаимодействует с ним в calmer-period usage
**Then** система использует prior context для более релевантного entry point, follow-up framing or insight continuity
**And** repeat-use experience feels like natural continuation rather than artificial feature forcing

**Given** пользователь приходит не с новым “событием”, а с желанием проверить состояние, паттерн или повторяющуюся динамику
**When** reflective interaction развивается
**Then** продукт поддерживает этот lower-intensity use case in a valid way
**And** не заставляет пользователя искусственно формулировать crisis-level problem to proceed

**Given** retention layer не должна превращаться в generic wellness content loop
**When** продукт формирует calmer-period repeat-use experience
**Then** value остается anchored in the user’s own continuity and patterns
**And** не уходит в broad self-help chatter unrelated to prior user context

**Given** returning use outside acute moments не всегда будет clearly meaningful
**When** система не видит достаточного continuity basis for a strong interaction
**Then** продукт остается conservative and low-pressure
**And** не симулирует глубину или personalization, которой на самом деле нет

**Given** пользователь после weekly insight или просто по собственной инициативе возвращается в продукт
**When** новая сессия стартует
**Then** repeat-use path остается coherent with earlier memory, status and reflective positioning
**And** ощущается как закономерное развитие продукта, а не как отдельный retention gimmick

## Epic 6: Privacy, operator operations и надежность сервиса

Пользователь может запросить удаление данных, а оператор может безопасно поддерживать работу продукта, отслеживать health, инциденты и проблемные платежные/операционные события.

### Story 6.1: Запрос удаления пользовательских данных

As a user,
I want запросить удаление моих сохраненных данных,
So that я сохраняю контроль над своей приватной информацией и могу прекратить хранение контекста в продукте.

**Implements:** FR32

**Acceptance Criteria:**

**Given** пользователь хочет удалить свои данные из продукта
**When** он инициирует deletion request через supported product flow
**Then** система принимает запрос на удаление данных
**And** пользователь получает понятное подтверждение, что request зарегистрирован

**Given** продукт хранит continuity artifacts and related user data
**When** deletion request принята системой
**Then** request связывается с корректным user identity and data scope
**And** workflow не требует от пользователя разбираться во внутренней структуре хранения

**Given** deletion request поступает в privacy-sensitive system
**When** продукт обрабатывает начальную стадию запроса
**Then** статус request становится traceable for later completion
**And** продукт не теряет deletion intent silently

**Given** пользователь случайно, повторно или неоднозначно инициирует deletion request
**When** система валидирует запрос
**Then** продукт избегает confusing duplicate request handling
**And** пользователь получает понятный status rather than contradictory confirmations

**Given** deletion request intake завершилась ошибкой или не может быть надежно зарегистрирована
**When** система не может принять запрос корректно
**Then** failure становится observable и user-visible в спокойной форме
**And** продукт не создает ложное ощущение, что deletion workflow уже запущен, если это не так

**Given** deletion request зарегистрирована
**When** пользователь продолжает взаимодействие с продуктом до фактического выполнения удаления
**Then** система может показывать consistent pending-deletion state where relevant
**And** дальнейшее поведение продукта не противоречит уже принятому privacy request

### Story 6.2: Выполнение deletion workflow и удаление retained memory artifacts

As a user and as an operator handling privacy requests,
I want чтобы зарегистрированный deletion request реально удалял сохраненные continuity artifacts и связанные пользовательские данные,
So that privacy request завершается фактическим data removal, а не только формальной отметкой.

**Implements:** FR33, FR38

**Acceptance Criteria:**

**Given** valid deletion request уже зарегистрирован в системе
**When** deletion workflow запускается на выполнение
**Then** система удаляет или надежно деактивирует retained summaries, profile facts и другие user-linked memory artifacts within defined data scope
**And** удаление не ограничивается только сменой статуса request

**Given** продукт хранит данные в нескольких memory and operational scopes
**When** deletion execution проходит по user-linked records
**Then** workflow охватывает все relevant retained user data according to privacy policy
**And** transient or already-expired processing data не используется как оправдание для пропуска durable artifacts

**Given** deletion workflow связан с privacy-sensitive operations
**When** выполнение удаления завершается полностью или частично
**Then** результат остается traceable and auditable for operator confirmation
**And** система может подтвердить completion or failure without routine exposure to removed content itself

**Given** operator должен иметь возможность execute or confirm deletion requests
**When** request доходит до operational stage
**Then** operator workflow поддерживает controlled execution or confirmation step
**And** это действие остается bounded by privacy and audit expectations

**Given** часть данных уже отсутствует, была ранее удалена или оказалась в inconsistent state
**When** deletion workflow выполняется повторно или частично
**Then** процесс остается safe and idempotent enough for re-run behavior
**And** не ломается только потому, что часть targeted artifacts уже недоступна

**Given** deletion execution завершилась ошибкой или не смогла удалить все required artifacts
**When** workflow не доходит до complete success
**Then** failure становится observable и traceable for follow-up
**And** пользователь не получает misleading confirmation of full deletion if required removal did not complete

### Story 6.3: Health visibility и базовый service monitoring

As an operator,
I want видеть базовый health status сервиса,
So that я могу быстро понять, работает ли система в нормальном состоянии и требует ли она немедленного внимания.

**Implements:** FR42

**Acceptance Criteria:**

**Given** продукт развернут как работающий сервис
**When** monitoring system or operator проверяет service health
**Then** система предоставляет explicit health visibility signal
**And** этот сигнал пригоден для базового uptime and readiness monitoring

**Given** service health endpoint or equivalent mechanism используется operational tooling
**When** сервис находится в нормальном состоянии
**Then** health response возвращается быстро и предсказуемо
**And** соответствует agreed operational expectations for normal-state checks

**Given** критически важные зависимости сервиса недоступны, degraded or unhealthy
**When** health visibility signal формируется
**Then** состояние отражает, что сервис больше не находится в healthy state
**And** operator monitoring может отличить healthy, degraded and failed behavior enough for response

**Given** оператору нужна observability без чтения пользовательского контента
**When** он смотрит базовый health status
**Then** health visibility не требует доступа к sensitive session data
**And** operational signal остается отделенным от transcript-level inspection

**Given** health check or monitoring path сама работает с ошибкой
**When** система не может reliably report its own health state
**Then** failure становится observable как operational issue
**And** отсутствие надежного health signal не маскируется под normal healthy state

**Given** health status используется как часть deployment and response workflows
**When** operator or automation опирается на этот signal
**Then** service health mechanism остается stable enough to be used as operational source
**And** не требует ручной интерпретации внутренних технических деталей при каждом check

### Story 6.4: Operator monitoring ключевых operational signals

As an operator,
I want отслеживать ключевые operational signals продукта,
So that я могу видеть аномалии, usage patterns, product failures и реагировать на них до того, как они разрушают trust или monetization.

**Implements:** FR37

**Acceptance Criteria:**

**Given** продукт уже генерирует core operational events and states
**When** operator использует monitoring workflow
**Then** он может видеть ключевые сигналы вроде session activity, payment events, product errors и других важных operational indicators
**And** monitoring не зависит от ручного чтения всех пользовательских диалогов

**Given** operator monitoring должен поддерживать управляемость продукта
**When** сигналы отображаются или агрегируются
**Then** система делает видимыми meaningful operational patterns and anomalies
**And** operator может отличить normal activity from conditions requiring attention

**Given** monitoring касается trust-sensitive продукта
**When** operator получает operational visibility
**Then** обычный monitoring слой опирается на metrics, statuses, counts, classifications or bounded metadata
**And** routine transcript exposure не является required path for product oversight

**Given** payment-related, summary-related, alert-delivery or other critical pipeline failures происходят в системе
**When** такие события попадают в monitoring layer
**Then** operator visibility охватывает эти categories as operational signals
**And** failure modes не теряются silently за пределами product oversight

**Given** monitoring data source partially degraded, lagging or inconsistent
**When** operator смотрит operational view
**Then** система не выдает ложное ощущение полной нормальности
**And** degradation or blind spots themselves become observable where possible

**Given** operator использует monitoring for product management and response
**When** operational signals разворачиваются со временем
**Then** monitoring workflow поддерживает repeated oversight rather than one-off inspection
**And** служит управлению реальным продуктом, а не только формальному check-the-box observability

### Story 6.5: Review payment issues and subscription-state problems

As an operator,
I want видеть и разбирать payment issues и subscription-state problems,
So that я могу понимать, где monetization flow сломался или стал противоречивым для пользователя.

**Implements:** FR39

**Acceptance Criteria:**

**Given** в системе происходят payment failures, reconciliation mismatches or subscription-state inconsistencies
**When** operator использует supported operational review path
**Then** он может увидеть эти проблемные случаи как distinct operational issues
**And** review workflow не требует routine access to sensitive conversation content

**Given** у конкретного пользователя возник конфликт между expected billing outcome и actual access state
**When** operator анализирует этот случай
**Then** система показывает достаточно bounded billing and access context для понимания проблемы
**And** operator может отличить payment initiation issue, callback issue, reconciliation problem or status-display inconsistency

**Given** billing issue связана с delayed confirmation, provider timeout или duplicate callback behavior
**When** operator reviewing workflow поднимает этот случай
**Then** система сохраняет traceability of the event chain
**And** problem review не сводится к guesswork from partial state

**Given** review payment issues должно поддерживать product operations, а не ручную импровизацию
**When** operator работает с monetization-related problems
**Then** workflow позволяет последовательно видеть state, anomalies and unresolved cases
**And** не зависит только от ad hoc database inspection as the primary path

**Given** billing-review data itself incomplete, stale or unavailable
**When** operator пытается разобраться в payment issue
**Then** система делает видимой ограниченность или деградацию available review context
**And** не выдает misleading certainty about the user’s monetization state

**Given** payment or subscription problem later resolves through confirmed event or manual follow-up
**When** operator revisits the case
**Then** updated operational view reflects latest confirmed state
**And** resolved and unresolved billing issues are not indistinguishable in the workflow

### Story 6.6: Idempotent handling duplicate or repeated service events

As a product operator and as a system relying on external callbacks,
I want чтобы повторные или дублирующиеся service events обрабатывались идемпотентно,
So that user state, billing state and operational workflows не ломались из-за retries, duplicates or replayed events.

**Implements:** FR43

**Acceptance Criteria:**

**Given** Telegram updates, payment callbacks or other service events могут приходить повторно
**When** система получает duplicate or replayed event
**Then** обработка остается idempotent
**And** повторное событие не приводит к повторному изменению user state, access state или operational state

**Given** событие уже было успешно обработано ранее
**When** его копия или retry снова поступает в систему
**Then** система может распознать, что это не новое business event
**And** не создает duplicate side effects such as double activation, repeated deletion execution or duplicated alert logic

**Given** повторные события поступают в условиях partial failures or delayed retries
**When** система повторно обрабатывает ingress
**Then** resulting state остается consistent with the first valid confirmed outcome
**And** duplicate handling не зависит от lucky timing or manual cleanup

**Given** service event частично обработался, но completion status остался ambiguous
**When** тот же event приходит снова или поднимается для reprocessing
**Then** система обрабатывает его через safe retry-aware logic
**And** не создает contradictory state transitions из-за неясного промежуточного состояния

**Given** duplicate detection or idempotency layer itself encounters an error
**When** система не может надежно определить, было ли событие уже обработано
**Then** failure становится observable как operational issue
**And** продукт не должен silently proceed in a way that risks corrupting durable state

**Given** operator later reviews event-driven incidents or anomalies
**When** duplicate-related cases попадают в monitoring or issue review workflows
**Then** system traceability помогает увидеть, что произошло с original and repeated events
**And** duplicate-handling behavior не остается opaque to operations
