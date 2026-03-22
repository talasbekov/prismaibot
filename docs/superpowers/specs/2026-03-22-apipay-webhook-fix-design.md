# ApiPay Webhook Fix — Design Spec

**Date:** 2026-03-22
**Approach:** Вариант Б — полный рефактор grace period, доверяем ApiPay

---

## Контекст

После аудита интеграции с ApiPay/Kaspi выявлено 4 проблемы:

1. Не обрабатываются 2 вебхук-события: `subscription.grace_period_started`, `invoice.refunded`
2. Двойная логика grace period — локальный стейт-машин в `check_and_update_subscription_status` конфликтует с ApiPay
3. `external_subscriber_id` не передаётся при создании подписки
4. `APIPAY_WEBHOOK_SECRET` не валидируется в non-local окружении

---

## Изменения

### 1. Переработка вебхук-событий (`service.py`)

Переназначаем события на правильные переходы состояний:

| ApiPay событие | Старое поведение | Новое поведение |
|---|---|---|
| `subscription.payment_failed` | → `past_due` + уведомление | → лог + уведомление "оплата не прошла, повторим попытку" |
| `subscription.grace_period_started` | не обрабатывалось | → `past_due` + уведомление о grace period |
| `subscription.expired` | → `suspended` + downgrade | без изменений |
| `subscription.payment_succeeded` | → `active` + продление | без изменений |
| `invoice.refunded` | не обрабатывалось | → лог (возвраты не поддерживаются) |

**Логика:** `past_due` теперь означает именно "ApiPay начал grace period" — все попытки оплаты исчерпаны. `payment_failed` — промежуточное событие, пока ApiPay ещё делает ретраи.

### 2. Убираем локальный стейт-машин (`service.py`, `repository.py`)

`check_and_update_subscription_status` сейчас самостоятельно переводит статусы:
- `active → past_due` если `now > current_period_end`
- `past_due → suspended` если `now > current_period_end + 24h`

**После:** функция становится read-only — только читает текущий статус из БД, не меняет его. Все переходы состояний происходят исключительно через вебхуки ApiPay.

`build_status_response` и `has_premium_access` продолжают использовать ту же функцию, но теперь она просто возвращает подписку без side effects.

**Компромисс:** если вебхук от ApiPay потеряется, статус в БД не обновится. Принимаем этот риск — ApiPay ретраит вебхуки (до 3 раз с интервалами 1/5/15 минут).

### 3. `external_subscriber_id` при создании подписки (`apipay_client.py`, `service.py`)

- `ApiPayClient.create_subscription` принимает новый параметр `external_subscriber_id: str | None = None`
- `create_apipay_subscription` передаёт `external_subscriber_id=str(telegram_user_id)`

Позволяет найти подписку в дашборде ApiPay по telegram_user_id и упрощает reconciliation.

### 4. Валидация `APIPAY_WEBHOOK_SECRET` в конфиге (`config.py`)

Добавляем в `_enforce_non_default_secrets`:
```python
self._require_non_local_setting("APIPAY_WEBHOOK_SECRET", self.APIPAY_WEBHOOK_SECRET)
```

Запуск без `APIPAY_WEBHOOK_SECRET` в production становится невозможным.

---

## Затронутые файлы

| Файл | Тип изменения |
|---|---|
| `backend/app/billing/service.py` | Основные изменения — вебхуки + убрать стейт-машин |
| `backend/app/billing/apipay_client.py` | Добавить `external_subscriber_id` |
| `backend/app/core/config.py` | Добавить валидацию секрета |
| `backend/app/billing/prompts.py` | Добавить сообщение для `payment_failed` (retry) |
| `backend/tests/billing/test_payment_confirmation.py` | Обновить под новую логику |
| `backend/tests/billing/test_payment_initiation.py` | Обновить под новую логику |
| `backend/tests/billing/test_subscriptions.py` | Добавить тесты `grace_period_started`, `invoice.refunded` |
| `backend/tests/billing/test_status_command.py` | Обновить под read-only статус |
| `backend/tests/billing/test_paywall_ui.py` | Обновить если нужно |

---

## Что НЕ меняется

- Флоу создания инвойса и подписки
- Логика `has_premium_access` (проверяет `status in ("active", "past_due")`)
- Отмена подписки
- Paywall и free tier логика
