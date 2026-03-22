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

| ApiPay событие | Новое поведение |
|---|---|
| `subscription.payment_failed` | → лог + `PAYMENT_RETRY_MESSAGE` пользователю. Мутация статуса (`session.add/commit`) **удаляется полностью**. |
| `subscription.grace_period_started` | → `past_due`, `current_period_end = expires_at`, уведомление |
| `subscription.expired` | без изменений |
| `subscription.payment_succeeded` | без изменений |
| `invoice.refunded` | → только лог |

**UX intent:** пользователь не получает уведомление при каждом неудачном платеже. Первое уведомление приходит только когда ApiPay объявляет grace period (`grace_period_started`). Это намеренно — меньше паники при ретраях.

**`grace_period_started` handler (новый):**
```python
if event == "subscription.grace_period_started":
    provider_sub_id = str(subscription_data.get("id"))
    sub = repository.get_subscription_by_provider_id(session, provider_sub_id)
    if not sub:
        logger.warning("Subscription not found for provider_sub_id=%s", provider_sub_id)
        return {"status": "error", "message": "subscription_not_found"}

    expires_at_str = payload.get("expires_at")
    if expires_at_str:
        sub.current_period_end = datetime.fromisoformat(expires_at_str)
    sub.status = "past_due"
    sub.updated_at = datetime.now(timezone.utc)
    session.add(sub)
    session.commit()

    remaining_hours = max(0, int((sub.current_period_end - datetime.now(timezone.utc)).total_seconds() // 3600))
    await send_telegram_message(sub.telegram_user_id, STATUS_SUBSCRIPTION_PAST_DUE_MESSAGE.format(hours=remaining_hours))
    return {"status": "ok", "message": "grace_period_started"}
```

Новый промпт в `prompts.py`:
```python
PAYMENT_RETRY_MESSAGE = "Оплата не прошла. ApiPay сделает повторную попытку автоматически."
```

**`build_status_response` — исправление:** заменить:
```python
grace_end = subscription.current_period_end + timedelta(hours=24)
```
на:
```python
grace_end = subscription.current_period_end
```
После этого деплоя `current_period_end` для `past_due` записей = конец grace period (из `expires_at`). Существующие `past_due` записи (если есть) будут показывать неточное количество часов, но их мало и они разрешатся через вебхуки `subscription.expired`.

### 2. Убираем локальный стейт-машин (`service.py`)

`check_and_update_subscription_status` становится read-only: убрать все `session.add`, `session.flush` внутри функции. Просто возвращает `Subscription | None`.

**Принятые риски (явно):**

1. **Потеря вебхука → вечный `past_due`:** если `subscription.expired` от ApiPay не дойдёт, пользователь с `past_due` статусом сохраняет доступ (`has_premium_access` возвращает `True` для `past_due`). Это намеренный trade-off Варианта Б. ApiPay ретраит subscription webhooks до 3 раз (1/5/15 мин). При необходимости можно добавить periodic reconciliation job позже (Вариант В).

2. **Callers не делают commit самостоятельно:** `build_status_response` и `has_premium_access` вызывают функцию и не вызывают `session.commit()` сами — удаление мутаций безопасно.

**Legacy users:** пользователи с `access_tier="premium"` без subscription record не затронуты — `has_premium_access` fallback остаётся.

### 3. `external_subscriber_id` при создании подписки

- `ApiPayClient.create_subscription` получает параметр `external_subscriber_id: str | None = None`, включается в payload если передан
- `create_apipay_subscription` передаёт `external_subscriber_id=str(telegram_user_id)`
- `ApiPaySubscriptionResponse` не меняется — Pydantic v2 игнорирует лишние поля в ответе по умолчанию

### 4. Валидация `APIPAY_WEBHOOK_SECRET` в конфиге (`config.py`)

Добавить в `_enforce_non_default_secrets`:
```python
self._require_non_local_setting("APIPAY_WEBHOOK_SECRET", self.APIPAY_WEBHOOK_SECRET)
```

`PAYMENT_PROVIDER_WEBHOOK_SECRET` и `/billing/webhook` — без изменений (другой эндпоинт).
`billing/api.py`, `billing/utils.py` — без изменений.

---

## Затронутые файлы

| Файл | Тип изменения |
|---|---|
| `backend/app/billing/service.py` | Вебхуки + стейт-машин + fix `build_status_response` |
| `backend/app/billing/apipay_client.py` | Добавить `external_subscriber_id` |
| `backend/app/core/config.py` | Валидация секрета |
| `backend/app/billing/prompts.py` | Добавить `PAYMENT_RETRY_MESSAGE` |
| `backend/tests/billing/test_payment_confirmation.py` | Обновить |
| `backend/tests/billing/test_payment_initiation.py` | Обновить |
| `backend/tests/billing/test_subscriptions.py` | Добавить тесты для новых событий |
| `backend/tests/billing/test_status_command.py` | Обновить под read-only статус |
| `backend/tests/billing/test_paywall_ui.py` | Обновить если нужно |

---

## Что НЕ меняется

- Флоу создания инвойса и подписки
- `has_premium_access` (проверяет `status in ("active", "past_due")`)
- Отмена подписки, paywall, free tier
- `billing/api.py`, `billing/utils.py`, `repository.py`
- `PAYMENT_PROVIDER_WEBHOOK_SECRET`, `/billing/webhook`
