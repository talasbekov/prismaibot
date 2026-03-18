# Sprint Change Proposal: Transition to Monthly Subscription Model

**Date:** 2026-03-18
**Project:** goals
**Status:** Approved (Incremental Review)

## 1. Issue Summary
Проект переходит от модели разовой оплаты доступа к модели **ежемесячной рекуррентной подписки**. Это изменение необходимо для обеспечения стабильного дохода и лучшего соответствия ожиданиям пользователей от AI-сервиса с долгосрочной памятью (continuity).

## 2. Impact Analysis
- **PRD Impact:** Изменение FR21-FR23, добавление FR44-FR45 (логика продления и grace period).
- **Epic Impact:** Полная переработка Epic 4 (Монетизация).
- **Architecture Impact:** Требуется расширение модели данных (таблица `subscriptions`) и реализация фоновой задачи для обработки просроченных платежей.
- **UX Impact:** Изменение формулировок пейволла (акцент на безлимит и сохранение памяти за 3000 ₸/мес).

## 3. Recommended Approach
Реализовать логику подписки как базовую функциональность (Epic 4), подготовив систему к технической интеграции с ApiPay.kz (Epic 7).

## 4. Detailed Change Proposals

### Artifact: PRD (prd.md)
- **FR21:** Предоставление одного полного цикла (рефлексия/брейншторм) бесплатно.
- **FR22:** Пейволл срабатывает при попытке начать вторую сессию.
- **FR23:** Стоимость подписки — 3000 ₸ в месяц с автопродлением.
- **FR45:** Льготный период (Grace Period) — 1 день (24 часа) на исправление ошибки оплаты.

### Artifact: Epics (epics.md)
- **Story 4.1 (Limits):** Переход на отслеживание флага `first_session_completed`.
- **Story 4.2 (Value):** Рефрейминг ценности Premium вокруг безлимита и памяти.
- **Story 4.4 (Payments):** Внедрение State Machine подписки: `active` -> `past_due` -> `suspended`.
- **Story 4.6 (Cancellation):** Реализация логики `cancel_at_period_end`.

## 5. Implementation Handoff
- **Scope:** Moderate (Требуется реорганизация бэклога и обновление архитектурных схем данных).
- **Handoff:** Scrum Master (для обновления `sprint-status.yaml`) и Developer (для реализации новой логики доступа).

---
**Handoff complete.**
