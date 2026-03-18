# Story 4.3: Запуск и выбор ежемесячной подписки (3000 TG Stars)

Status: done

## Story

As a пользователь, который хочет поддержать проект и получить безлимитный доступ,
I want иметь возможность запустить процесс оплаты подписки через Telegram Stars,
So that я могу активировать Premium-статус на 30 дней.

## Acceptance Criteria

1. **Given** пользователь нажал кнопку "Оформить Premium ✦" в пейволле, **When** бот получает коллбэк `pay:stars`, **Then** система формирует инвойс на **3000 Telegram Stars**. [Source: epics.md#story-4.3-AC1]

2. **Given** формирование инвойса, **When** пользователь видит описание, **Then** оно должно четко указывать, что это подписка на **30-дневный безлимитный доступ** с сохранением памяти. [Source: epics.md#story-4.3-AC2]

3. **Given** запрос на оплату, **When** процесс инициирован, **Then** система должна создать запись `PurchaseIntent` в базе данных со статусом `pending` до отправки инвойса. [Source: architecture.md#payment-integrity]

4. **Given** ошибку при создании интента, **When** база данных недоступна или произошел сбой, **Then** бот должен отправить вежливое сообщение об ошибке ("Сейчас не получилось запустить оплату...") вместо молчаливого падения. [Source: prd.md#error-handling]

5. **Given** инвойс, **When** он отправлен, **Then** поле `invoice_payload` должно содержать уникальный идентификатор интента для последующей сверки при подтверждении. [Source: architecture.md#idempotency-requirements]

## Tasks / Subtasks

- [x] Обновить `PREMIUM_STARS_PRICE` в `backend/app/core/config.py` (AC: 1)
  - [x] Установить значение `3000`.

- [x] Обновить тексты инвойса в `backend/app/billing/prompts.py` (AC: 2)
  - [x] Обновить `INVOICE_TITLE` и `INVOICE_DESCRIPTION`.
  - [x] Отразить 30-дневный период и безлимит.

- [x] Проверить логику `get_or_create_purchase_intent` в `billing/service.py` (AC: 3, 5)
  - [x] Убедиться, что `amount` берется из `settings`.
  - [x] Убедиться, что `invoice_payload` содержит `intent.id` или другой надежный ключ для Story 4.4.

- [x] Проверить обработку коллбэка в `conversation/session_bootstrap.py` (AC: 1, 4)
  - [x] Убедиться, что `handle_session_entry` корректно вызывает создание интента и возвращает экшен `payment_invoice`.

- [x] Написать и запустить тесты (AC: все)
  - [x] Обновить `backend/tests/billing/test_payment_initiation.py`.
  - [x] Test: цена в инвойсе = 3000.
  - [x] Test: описание инвойса содержит упоминание 30 дней.
  - [x] Test: интент создается в БД.
  - [x] Запустить `uv run pytest tests/billing/ -q`.

## Dev Notes

- **Цена**: 3000 Stars — это актуальная цена согласно новому бизнес-плану.
- **Payload**: Важно передавать ID интента в `invoice_payload`, так как Telegram вернет его в `successful_payment` (Story 4.4).
- **Срок**: Хотя технически Telegram Stars — это разовый платеж, мы позиционируем это как подписку на 30 дней. Логика истечения будет реализована в следующих стори.

## Project Structure Notes

- Billing module: `backend/app/billing/`
- Config: `backend/app/core/config.py`
- Tests: `backend/tests/billing/test_payment_initiation.py`

## Technical Requirements

- Telegram Bot API (sendInvoice).
- SQLModel for PurchaseIntent.

## Architecture Compliance

- Payment flow integrity: запись интента до отправки инвойса.
- Fail-open for UX: вежливые ошибки.

## Testing Requirements

- `uv run pytest tests/billing/test_payment_initiation.py`
- `uv run ruff check app tests`

## References

- Epics Story 4.3: [Source: planning-artifacts/epics.md#story-4.3]
- Sprint Change Proposal 2026-03-18: [Source: planning-artifacts/sprint-change-proposal-2026-03-18.md]
