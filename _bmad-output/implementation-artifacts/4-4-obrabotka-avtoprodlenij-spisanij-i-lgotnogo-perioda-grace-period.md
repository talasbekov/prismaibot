# Story 4.4: Обработка автопродлений, списаний и льготного периода (Grace Period)

Status: done

## Story

As a пользователь с активной подпиской,
I want чтобы система корректно обрабатывала продления и давала мне время исправить ошибку оплаты,
So that мой доступ не закрывался мгновенно при неудачном списании.

## Acceptance Criteria

1. **Given** успешную оплату (из Story 4.3/4.4-old), **When** система подтверждает платеж, **Then** она должна создать или обновить запись в новой таблице `Subscription` со статусом `active` и установить `expires_at` на +30 дней. [Source: epics.md#story-4.4-AC1]

2. **Given** активную подписку, **When** наступает дата продления и платеж не проходит (имитируется или получается от провайдера), **Then** статус подписки переходит в `past_due` (льготный период). [Source: epics.md#story-4.4-AC2]

3. **Given** статус `past_due`, **When** пользователь отправляет сообщение боту, **Then** система **продолжает предоставлять Premium-доступ** в течение 24 часов (Grace Period), но может отправить уведомление о проблеме с оплатой. [Source: prd.md#FR45]

4. **Given** статус `past_due` более 24 часов, **When** время истекло, **Then** статус подписки переходит в `suspended`, и Premium-функции блокируются (показывается пейволл). [Source: epics.md#story-4.4-AC4]

5. **Given** переход в `suspended`, **When** пользователь заблокирован, **Then** он должен увидеть сообщение о том, что подписка приостановлена из-за ошибки оплаты, с предложением обновить платежные данные. [Source: ux-design-specification.md#feedback-patterns]

## Tasks / Subtasks

- [x] Создать модель `Subscription` в `backend/app/billing/models.py` (AC: 1, 2)
  - [x] Поля: `id`, `telegram_user_id`, `status` (active, past_due, suspended, cancelled), `current_period_end`, `cancel_at_period_end: bool`.
  - [x] Создать Alembic миграцию.

- [x] Реализовать логику управления состоянием в `billing/service.py` (AC: 1, 2, 4)
  - [x] Обновить `confirm_payment_and_upgrade`, чтобы он создавал/продлевал `Subscription`.
  - [x] Создать функцию `check_and_update_subscription_status(session, user_id)`, которая проверяет даты и переводит в `past_due` или `suspended`.

- [x] Обновить `is_free_eligible` или создать `has_premium_access` (AC: 3, 4)
  - [x] Учитывать не только `access_tier`, но и статус `Subscription` (включая Grace Period).

- [x] Проверить Gate в `session_bootstrap.py` (AC: 4, 5)
  - [x] При вызове `get_user_access_state` также проверять статус подписки.
  - [x] Если `suspended` — показывать специальный пейволл для просроченной оплаты.

- [x] Написать и запустить тесты (AC: все)
  - [x] Test: создание подписки при оплате.
  - [x] Test: доступ разрешен в `past_due` (в течение 24ч).
  - [x] Test: доступ запрещен в `suspended`.
  - [x] Test: идемпотентность продления.

## Dev Notes

- **Grace Period**: Важно реализовать именно 24-часовой зазор. Мы доверяем пользователю и даем шанс исправить проблему с картой/звездами.
- **Интеграция**: На текущем этапе (Telegram Stars) автопродление технически обрабатывается самим Telegram, но наше состояние должно уметь реагировать на его события или отсутствие подтверждения в срок.
- **Модель**: `UserAccessState` остается для общих флагов, `Subscription` — для управления временными периодами.

## Project Structure Notes

- Models: `backend/app/billing/models.py`
- Service: `backend/app/billing/service.py`
- Tests: `backend/tests/billing/test_subscriptions.py`

## Technical Requirements

- SQLModel
- Python `datetime` с timezone (UTC).

## Architecture Compliance

- State Machine: четкие переходы состояний.
- Async Jobs: в будущем потребуется периодическая задача (celery/arq) для проверки просрочек, но пока можно делать проверку "just-in-time" при входе пользователя.

## Testing Requirements

- `uv run pytest tests/billing/`
- Mocking `datetime.now` для проверки переходов состояний.

## References

- Epics Story 4.4: [Source: planning-artifacts/epics.md#story-4.4]
- Sprint Change Proposal 2026-03-18: [Source: planning-artifacts/sprint-change-proposal-2026-03-18.md]
