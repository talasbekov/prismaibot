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
FR21: One full reflection/brainstorm cycle is provided for free to allow the user to experience the full value of the product.
FR22: Paywall is enforced upon attempting to start the second session after the first full cycle completion.
FR23: User can unlock monthly subscription (3000 ₸) with auto-renewal through a supported payment flow.
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
FR44: System handles subscription renewal (recurring payments) automatically via payment provider adapter.
FR45: System provides a 1-day grace period for failed renewals before suspending premium access.

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

### Epic 4: Монетизация, доступ и подписка (Subscription Model)
Пользователь получает один полный бесплатный цикл, затем понятный Premium-барьер (3000 тг/мес) с автопродлением, льготным периодом и сохранением памяти.
**FRs covered:** FR21, FR22, FR23, FR24, FR25, FR26, FR27, FR28, FR41, FR44, FR45

### Epic 5: Retention и повторное возвращение (Post-MVP / Phase 2)
Пользователь получает дополнительную ценность вне acute момента за счет weekly insight и continuity-driven repeat usage.
**FRs covered:** FR29, FR30, FR31

### Epic 6: Privacy, operator operations и надежность сервиса
Пользователь может запросить удаление данных, а оператор может безопасно поддерживать работу продукта, отслеживать health, инциденты и проблемные платежные/операционные события.
**FRs covered:** FR32, FR33, FR37, FR38, FR39, FR42, FR43

## Epic 1: Первая полезная reflective-сессия в Telegram

Пользователь может зайти в бот, быстро описать ситуацию, пройти базовый reflective flow и получить ясный итог со следующим шагом без регистрации и тяжелого onboarding.

### Story 1.1: Инициализация проекта из starter template для Telegram-first backend
... (содержимое сохраняется) ...

## Epic 4: Монетизация, доступ и подписка (Subscription Model)

Пользователь получает один полный бесплатный цикл (рефлексия/брейншторм), затем понятный Premium-барьер для подписки (3000 тг/мес) с автопродлением и 1 днем льготного периода.

### Story 4.1: Лимит на один бесплатный цикл и учет сессий

As a пользователь, который только начинает пользоваться продуктом,
I want получить один полный бесплатный сеанс до пейволла,
So that я могу сначала почувствовать ценность продукта, прежде чем принимать решение о подписке.

**Acceptance Criteria:**

- Система отслеживает флаг завершения первого полного цикла (`first_session_completed`).
- Пользователь может завершить одну полную сессию (от старта до получения итогового takeaway).
- Пейволл срабатывает при попытке отправить сообщение для начала **второй сессии**.

### Story 4.2: Пейволл с акцентом на безлимит и непрерывность (Continuity)

As a пользователь, который уже получил пользу от первой сессии,
I want увидеть предложение подписки в понятный момент,
So that я понимаю, что Premium дает безлимитный доступ и сохранение моей памяти.

**Acceptance Criteria:**

- Пейволл появляется сразу после завершения первого takeaway/summary.
- Premium позиционируется как "Безлимитная ясность и работа с памятью за 3000 тг/месяц".
- Пользователь понимает, что без подписки вторая сессия не будет учитывать контекст первой.

### Story 4.3: Запуск и выбор ежемесячной подписки (3000 тг)

As a пользователь, который решил оформить Premium,
I want запустить процесс оплаты ежемесячной подписки,
So that я могу разблокировать безлимитный доступ.

**Acceptance Criteria:**

- Бот предлагает кнопку оплаты ежемесячной подписки (3000 тг).
- Система инициализирует процесс подписки (Subscription) через платежный адаптер.

### Story 4.4: Обработка автопродлений, списаний и льготного периода (Grace Period)

As a пользователь с активной подпиской,
I want чтобы система корректно обрабатывала продления и давала мне время исправить ошибку оплаты,
So that мой доступ не закрывался мгновенно при неудачном списании.

**Acceptance Criteria:**

- Система обрабатывает рекуррентные списания (автопродление).
- Внедрен State Machine подписки: `active` -> `past_due` (неудачная оплата) -> `suspended` (через 24 часа).
- **Grace Period (1 день):** При неудачном продлении бот уведомляет пользователя, сохраняя Premium-доступ на 24 часа.
- После 24 часов без оплаты доступ переходит в `suspended` (Premium-функции заблокированы).

### Story 4.5: Просмотр статуса подписки и даты продления

As a пользователь,
I want видеть мой текущий статус подписки,
So that я знаю, активен ли Premium и когда будет следующее списание.

**Acceptance Criteria:**

- Бот показывает статус: "Подписка активна", "Льготный период" или "Подписка приостановлена".
- Отображается дата следующего списания.

### Story 4.6: Отмена подписки и сохранение доступа до конца периода

As a пользователь,
I want иметь возможность отменить подписку, сохранив доступ до конца оплаченного месяца,
So that я сохраняю контроль над своими финансами.

**Acceptance Criteria:**

- Пользователь может отменить подписку через команду.
- **Доступ остается активным до конца оплаченного 30-дневного периода.**
- Система помечает подписку как `cancel_at_period_end`.

... (остальные эпики 2, 3, 5, 6 сохраняются) ...

## Epic 7: Scaling and Management

Расширение платежных возможностей для региональных рынков и создание инструментов управления для операторов.

### Story 7.1 - 7.5: Интеграция Kaspi.kz (ApiPay)
Позволяет пользователям из Казахстана оплачивать подписку через Kaspi.kz с поддержкой рекуррентных платежей и льготного периода. (Реализовано)

### Story 7.6: Базовый Telegram Admin Interface и авторизация
As an operator,
I want иметь доступ к скрытым командам управления в Telegram,
So that я могу взаимодействовать с системой без использования веб-панели.

**Acceptance Criteria:**
- Доступ к админ-командам (например, `/admin`) ограничен списком `ADMIN_IDS` в конфиге.
- Бот распознает админа и показывает приветственное меню управления.

### Story 7.7: Просмотр операционных сигналов и статистики (Admin)
As an operator,
I want видеть ключевые метрики (количество сессий, активные подписки, ошибки) через Telegram,
So that я могу быстро оценивать состояние системы.

**Acceptance Criteria:**
- Админ может вызвать сводную статистику за последние 24 часа / 7 дней.
- Статистика включает количество новых пользователей, завершенных сессий и успешных оплат.

### Story 7.8: Управление подписками и разбор проблемных платежей
As an operator,
I want иметь возможность проверить статус оплаты конкретного пользователя и вручную корректировать доступ,
So that я могу решать тикеты поддержки пользователей.

**Acceptance Criteria:**
- Админ может запросить статус пользователя по `telegram_id`.
- Админ может вручную активировать Premium-доступ для пользователя в случае сбоя платежа.

### Story 7.9: Управляемый путь расследования safety-инцидентов
As an operator,
I want безопасно просматривать детали кризисных сессий при получении алерта,
So that я могу принять решение о дальнейшей помощи.

**Acceptance Criteria:**
- При получении алерта админ может запросить "детали" сессии.
- Доступ к деталям логгируется.
- Детали включают краткий контекст, по которому сработал триггер, без полной выгрузки всей истории, если это не требуется политикой.
