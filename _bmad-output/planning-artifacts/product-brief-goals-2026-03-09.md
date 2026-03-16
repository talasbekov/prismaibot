---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - /home/erda/Музыка/goals/_bmad-output/brainstorming/brainstorming-session-2026-03-08-231431.md
date: 2026-03-09
author: Bratan
---

# Product Brief: goals

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

goals is a Telegram-first AI companion designed to help people untangle emotionally charged situations in real time. The MVP focuses specifically on acute interpersonal conflicts, when users need immediate clarity, emotional decompression, and a structured next step before they escalate the situation further.

Unlike friends, general-purpose AI chats, psychologists, or journaling, the product is built for live conflict reflection in the exact moment of need. It combines a low-friction Telegram interface, structured conversational guidance, and lightweight accumulated memory across sessions to help users move from emotional overload to a clearer, calmer state.

The product's wedge is not generic self-help. It is helping users avoid making situations worse in moments of emotional overload. Over time, that acute use case expands into retention behaviors such as mental hygiene, recurring conflict reflection, and pattern awareness through memory and weekly insights.

---

## Core Vision

### Problem Statement

People regularly find themselves in emotionally charged conflicts or mentally tangled situations and have no immediate, trusted, structured way to process them. In those moments, they need to be heard, helped to unpack what happened, and guided toward clarity before they escalate the conflict, spiral internally, or make impulsive decisions they later regret.

### Problem Impact

When this problem goes unsolved, users often intensify conflicts, lose sleep, ruminate for hours, act from emotion instead of judgment, and accumulate unresolved resentment. Over time, this damages relationships, self-respect, emotional stability, and, in work contexts, even reputation and position.

### Why Existing Solutions Fall Short

Current solutions each solve only part of the problem:

- Friends are available but biased, inconsistent, and often project their own views.
- ChatGPT is accessible but feels generic, overly verbose, lacks situational memory, and is not designed for emotional conflict structuring.
- Psychologists may be highly valuable but are expensive, delayed, and unavailable in the exact moment of need.
- Journaling and notes provide release but no feedback, structure, or clear next step.
- Content and meditation may calm users generally, but they do not help unpack the user's specific situation.

What remains missing is an always-available, nonjudgmental, structured conversational layer that helps users work through a real situation right now while remembering relevant personal context over time.

### Proposed Solution

A Telegram-based AI conversational product that helps users process acute conflicts, relationship tension, and internal emotional chaos in real time. The product listens first, asks clarifying questions, structures the situation, identifies likely patterns and emotional distortions, offers several grounded interpretations, and helps the user leave with a clearer head and a reasonable next step.

The MVP will launch only in Telegram to minimize friction, leverage native messaging behavior, use built-in payment paths, and support recurring touchpoints such as weekly insights. Memory in the MVP will be implemented through structured per-session summaries and an accumulated user profile containing key topics, recurring patterns, relevant people, and emotional triggers. This avoids overengineering while preserving continuity between sessions.

### Key Differentiators

- **Telegram-first UX:** zero-install, familiar interface, native notifications, easy re-engagement, and built-in payment options.
- **Acute conflict wedge:** optimized for the exact moment users are most emotionally overloaded and most motivated to seek help.
- **Structured emotional sense-making:** not just empathetic chat, but guided unpacking of a messy real-life situation.
- **Lightweight contextual memory:** summary-based continuity across sessions without complex memory infrastructure in the MVP.
- **Clarity plus damage reduction:** designed not only to soothe, but to help users avoid making the situation worse in the heat of the moment.

## Target Users

### Primary Users

#### Persona 1: Маша, 31 — конфликт в отношениях

Маша работает менеджером и живет с партнером уже 3 года. После очередной ссоры формально все утихло, но внутри у нее остались обида, неясность и чувство, что разговор так и не состоялся. Она не хочет снова грузить подругу той же историей и не считает ситуацию "достаточно серьезной", чтобы идти к психологу.

Ее внутренний вопрос звучит так: "Я слишком остро реагирую или он правда ведет себя так, что мне больно?" Она ищет не абстрактную поддержку, а нейтральный и бережный разбор ситуации, который поможет понять свои чувства, увидеть картину яснее и подготовиться к следующему разговору с партнером.

Для Маши успех — это выйти из состояния эмоциональной мути с более ясной головой, без чувства стыда и без ощущения, что ее осудили или отмахнулись от проблемы.

#### Persona 2: Антон, 34 — конфликт на работе

Антон — тимлид, который недавно столкнулся с напряженным конфликтом с руководителем по поводу задачи. Ему кажется, что его подставили, но он не уверен, не ошибся ли сам. Он злится, но сдерживается, потому что не хочет выглядеть эмоциональным или непрофессиональным.

Его внутренний вопрос: "Я неадекватно реагирую или меня реально используют?" Он не хочет снова переносить рабочий конфликт в разговоры дома и ищет структурированный, спокойный взгляд со стороны, который поможет понять, что произошло, и как вести себя на следующей встрече.

Для Антона успех — это получить четкую картину ситуации, увидеть вероятные ошибки сторон и выйти с более хладнокровным следующим шагом.

### Secondary Users

#### Persona 3: Лена, 29 — регулярная эмоциональная разгрузка

Лена склонна к тревожности и руминации. Даже когда у нее нет острого кризиса, в фоне постоянно присутствует внутреннее напряжение и повторяющиеся мысли. Она впервые пришла в продукт после конфликта, почувствовала облегчение и теперь использует его регулярно.

Для нее продукт становится не только экстренной помощью, но и инструментом еженедельной разгрузки и самонаблюдения. Она возвращается, чтобы увидеть weekly summary, заметить повторяющиеся паттерны и почувствовать, что ее эмоциональная динамика не теряется между сессиями.

Для Лены успех — это ощущение, что кто-то помогает ей замечать изменения, повторения и внутренние сдвиги, а не просто слушает каждый раз с нуля.

### Secondary Users / Exclusions

В рамках MVP продукт не ориентирован на:

- пользователей в тяжелом клиническом состоянии;
- подростков;
- корпоративный wellbeing и B2B-сценарии.

Эти сегменты требуют отдельной продуктовой, регуляторной и этической проработки и не входят в стартовый фокус.

### User Journey

#### Journey: Маша

**Discovery:** Маша видит рилс или пост в Instagram либо Telegram-канале с обещанием не "поговорить", а "разобраться в конфликте". Эта формулировка попадает в ее состояние точнее обычной self-help подачи.

**Onboarding:** Она открывает Telegram-бота и получает простой старт без длинных опросников. Вместо сложного onboarding бот сразу задает простой вопрос: "Что случилось?" Маша пишет несколько предложений о ситуации. Бот отвечает коротко, тепло и без ранних советов, сначала уточняя контекст.

**Core Usage:** Бот помогает ей проговорить ситуацию, отделяет факты от эмоций, показывает возможные интерпретации и помогает увидеть, что именно ее задело. Разговор ощущается не как поток утешений, а как спокойный разбор.

**Aha Moment:** Бот формулирует ее ситуацию яснее, чем она могла сама. В этот момент Маша чувствует, что ее действительно поняли, не осудили и не нагрузили шаблонным текстом. Облегчение приходит через ясность.

**Return Trigger / Monetization Moment:** Через несколько дней происходит новый эпизод. Бот помнит контекст прошлого разговора, и Маше не нужно объяснять все заново. Именно continuity and memory становятся причиной повторного использования и перехода в платное поведение.

**Long-term:** Со временем продукт становится для нее не только помощником в конфликтах, но и личным пространством для эмоционального дебрифа и наблюдения за повторяющимися паттернами в отношениях.

## Success Metrics

Успех goals измеряется не только ощущением полезности, но и тем, приводит ли продукт пользователя к ясности в моменте и формирует ли повторяемую ценность со временем.

### User Success

**После одной сессии:**
Пользователь выходит с более ясной картиной, чем заходил. Ему не обязательно получить окончательное решение, но важно, чтобы мысли перестали ходить по кругу и появилась более понятная структура ситуации.

**Поведенческий сигнал первой ценности:**
Пользователь доходит до конца первой сессии и не бросает диалог на середине. Это означает, что разговор удержал внимание и был воспринят как полезный.

**После нескольких недель использования:**
Пользователь чувствует, что продукт помнит его контекст и ему больше не нужно каждый раз объяснять все с нуля. Возникает ощущение непрерывности и наблюдения за динамикой: пользователь начинает замечать повторяющиеся паттерны, эмоциональные триггеры и изменения в своем поведении.

### Business Objectives

**Горизонт 3 месяца:**
- Достичь 200–500 платящих пользователей.
- Понять, какой acquisition channel приводит пользователей эффективнее и дешевле всего.
- Достичь retention на 2-й неделе выше 40% для ключевого пользовательского сегмента.

**Горизонт 12 месяцев:**
- Довести MRR до уровня, покрывающего операционные расходы.
- Получить устойчивый органический рост за счет рекомендаций и сарафана.
- Понять unit-экономику одного подписчика, включая стоимость привлечения, удержание и lifetime value.

### Key Performance Indicators

- **Activation Rate:** доля новых пользователей, дошедших до конца первой сессии.
- **Session Completion Rate:** доля сессий, в которых пользователь доходит до итогового ответа, а не прекращает диалог раньше.
- **D7 Return Rate:** доля пользователей, вернувшихся в течение 7 дней после первой сессии.
- **Conversion to Paid:** доля пользователей, перешедших в платную подписку после 2–3 сессий.
- **Weekly Retention:** доля платящих пользователей, остающихся активными на 2-й и 4-й неделе подписки.
- **Sessions per User per Month:** среднее число сессий на пользователя в месяц как вспомогательный индикатор привычки и регулярной ценности.
- **Churn Rate:** доля отмен подписки как главный сигнал, что ценность не закрепилась.
- **Memory Continuity Signal:** доля повторных сессий, в которых пользователю не требуется пересказывать контекст заново, либо доля пользователей, взаимодействующих с memory-based value, such as weekly summaries.
- **Post-Session Clarity Score:** простой вопрос после сессии, стало ли пользователю яснее после разговора.
- **NPS / Qualitative Referral Signal:** регулярный вопрос пользователю, порекомендовал бы он продукт другу и почему.

### Strategic Interpretation

Эти метрики связывают пользовательскую ценность с бизнес-результатом. Activation и completion показывают, срабатывает ли первая сессия. D7 return, memory continuity и post-session clarity показывают, есть ли у продукта реальный perceived value. Conversion to paid и weekly retention отражают, превращается ли эта ценность в подписочную модель. Churn и qualitative feedback помогают понять, где продукт теряет доверие, глубину или ощущение незаменимости.

## MVP Scope

### Core Features

- **Low-friction onboarding:** Telegram-first старт без опросников, с одним входным вопросом: "Что случилось?"
- **Core conversational loop:** сессия строится по схеме: выслушать -> уточнить -> разложить ситуацию -> предложить следующий шаг -> дать итог.
- **Two session modes:** быстрый режим для короткого разбора в 5–7 сообщений и глубокий режим для полноценного разбора.
- **Session memory:** после каждой сессии сохраняется структурированный summary, который используется для continuity в следующих разговорах.
- **Safety escalation:** мягкая обработка red-flag сценариев без резкого обрыва диалога, с направлением к профильной помощи, когда это необходимо.
- **Paywall model:** бесплатный слой дает 2–3 полноценные сессии, платный открывает память между сессиями и глубокий режим.
- **Weekly insight:** краткий понедельничный weekly summary с повторяющимися паттернами и наблюдениями по динамике пользователя, если scope позволяет включить retention-loop уже в MVP.

### Out of Scope for MVP

В MVP сознательно не входят:

- голосовые сообщения;
- веб-версия и мобильное приложение вне Telegram;
- групповые сессии и парный режим с партнером;
- упражнения, медитации и домашние задания;
- визуальный дашборд с графиками состояний;
- внешние интеграции с Apple Health, календарями и подобными сервисами;
- мультиязычность;
- B2B и корпоративный wellbeing-модуль;
- vector memory / semantic retrieval и сложная memory-инфраструктура.

Эти направления либо не обязательны для доказательства core value, либо создают лишнюю сложность на раннем этапе.

### MVP Success Criteria

MVP считается подтвержденным, если:

- не менее 40% пользователей возвращаются на 7-й день;
- не менее 15% пользователей переходят в платную подписку после 2–3 сессий;
- session completion rate стабильно превышает 60%;
- появляются органические рекомендации без оплаченного продвижения как ранний validation signal.

Эти сигналы покажут, что продукт не только вызывает интерес, но и создает повторяемую пользовательскую ценность, за которую готовы платить и которую готовы рекомендовать другим.

### Future Vision

Через 2–3 года продукт может превратиться в персонального AI-партнера для ментальной ясности с долгосрочной памятью о человеке, его паттернах, отношениях, триггерах и динамике изменений. Это не замена психологу, а инструмент, который помогает человеку разбираться в себе и принимать решения с более ясной головой.

Возможное расширение после подтверждения consumer-модели — white-label или companion-инструмент для психологов, который используется между сессиями с клиентами.

## Growth Notes

### Referral Mechanic

Для раннего роста продукт может использовать безопасную одноуровневую referral-механику, завязанную на реальную активацию, а не на массовое приглашение.

**Recommended model:**

- пользователь получает персональную referral-ссылку;
- бонус выдается только если приглашенный пользователь действительно активируется, например проходит первую полноценную сессию;
- бонус получают оба участника.

**Recommended rewards:**

- 7 дней premium-доступа;
- или 1 глубокая сессия;
- или временный доступ к premium-функции.

**Important boundaries:**

- никакой многоуровневой пирамидальной механики;
- никакой денежной награды за приглашения;
- никакого агрессивного pressure-based invite loop;
- позиционирование должно оставаться как рекомендация полезного инструмента, а не growth hack на уязвимой аудитории.

**Product rationale:**

Эта механика может усиливать органический рост и сарафан, не разрушая доверие к бренду, если встроена мягко и активируется только после момента ценности, когда пользователь уже почувствовал реальную пользу от разбора.
