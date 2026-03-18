# Story 4.6: Отмена подписки и сохранение доступа до конца периода

Status: done

## Story

As a пользователь, который решил не продлевать подписку,
I want чтобы мой текущий оплаченный доступ сохранялся до конца 30-дневного периода,
So that я мог использовать то, за что уже заплатил.

## Acceptance Criteria

1. **Given** запрос `/cancel`, **When** у пользователя есть активная подписка, **Then** система устанавливает флаг `cancel_at_period_end = True` в таблице `Subscription`. [Source: epics.md#story-4.6-AC1]

2. **Given** отмену подписки, **When** процесс завершен, **Then** `access_tier` пользователя в `UserAccessState` остается `premium` до фактического истечения даты `current_period_end`. [Source: epics.md#story-4.6-AC2]

3. **Given** сообщение об успехе, **When** подписка отменена, **Then** бот сообщает, что автопродление отключено, но доступ активен до конца периода. [Source: ux-design-specification.md#feedback-patterns]

4. **Given** отсутствие активной подписки, **When** пользователь отправляет `/cancel`, **Then** бот сообщает, что активной подписки нет. [Source: prd.md#error-handling]

## Tasks / Subtasks

- [x] Обновить `process_cancellation_request` в `service.py` для работы с `cancel_at_period_end` (AC: 1, 2)
- [x] Обновить текст сообщения об отмене в `prompts.py` (AC: 3)
- [x] Написать тесты для проверки сохранения доступа после отмены в `test_cancel_command.py` (AC: все)

## Dev Notes

- В текущей реализации Telegram Stars автоматических продлений со стороны бота нет, но модель готова к переходу на Stripe/ApiPay, где этот флаг критичен.
- Логика "мягкой" отмены (soft cancel) более лояльна к пользователю.

## Testing Requirements

- `uv run pytest tests/billing/test_cancel_command.py`
