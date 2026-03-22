# ApiPay Webhook Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix ApiPay webhook integration — remove local grace period state machine, add missing webhook event handlers, pass `external_subscriber_id`, and enforce `APIPAY_WEBHOOK_SECRET` in prod.

**Architecture:** All subscription status transitions move to webhook-driven only (`grace_period_started`, `expired`, `payment_succeeded`). `check_and_update_subscription_status` becomes read-only. `payment_failed` stops mutating state. New `grace_period_started` handler sets `past_due` using ApiPay's `expires_at`.

**Tech Stack:** Python, FastAPI, SQLModel, pytest/anyio, uv

**Spec:** `docs/superpowers/specs/2026-03-22-apipay-webhook-fix-design.md`

---

## File Map

| File | Change |
|---|---|
| `backend/app/billing/prompts.py` | Add `PAYMENT_RETRY_MESSAGE` |
| `backend/app/core/config.py` | Add `APIPAY_WEBHOOK_SECRET` non-local validation |
| `backend/app/billing/service.py` | Fix `payment_failed`, add `grace_period_started`, add `invoice.refunded`, remove state machine mutations, fix `build_status_response` |
| `backend/app/billing/apipay_client.py` | Add `external_subscriber_id` to `create_subscription` |
| `backend/tests/billing/test_apipay_webhook.py` | Add tests for new events, update `payment_failed` test |
| `backend/tests/billing/test_subscriptions.py` | Replace auto-transition tests with webhook-driven equivalents |
| `backend/tests/billing/test_status_command.py` | Update `past_due`/`suspended` tests to set status directly |

---

## Task 1: Add `PAYMENT_RETRY_MESSAGE` prompt and config validation

**Files:**
- Modify: `backend/app/billing/prompts.py`
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Add `PAYMENT_RETRY_MESSAGE` to prompts**

In `backend/app/billing/prompts.py`, add after the existing message constants:

```python
PAYMENT_RETRY_MESSAGE = "Оплата не прошла. ApiPay сделает повторную попытку автоматически."
```

- [ ] **Step 2: Add `APIPAY_WEBHOOK_SECRET` validation to config**

In `backend/app/core/config.py`, inside `_enforce_non_default_secrets` method, after the existing `_require_non_local_setting("PAYMENT_PROVIDER_WEBHOOK_SECRET", ...)` call, add:

```python
self._require_non_local_setting("APIPAY_WEBHOOK_SECRET", self.APIPAY_WEBHOOK_SECRET)
```

- [ ] **Step 3: Verify config loads in local env**

```bash
cd backend && uv run python -c "from app.core.config import settings; print('OK')"
```
Expected: `OK` (no error — local env doesn't enforce the secret)

- [ ] **Step 4: Commit**

```bash
git add backend/app/billing/prompts.py backend/app/core/config.py
git commit -m "feat(billing): add PAYMENT_RETRY_MESSAGE and enforce APIPAY_WEBHOOK_SECRET in prod"
```

---

## Task 2: Fix `payment_failed` webhook handler

**Files:**
- Modify: `backend/app/billing/service.py`
- Modify: `backend/tests/billing/test_apipay_webhook.py`

- [ ] **Step 1: Write failing test for new `payment_failed` behavior**

In `backend/tests/billing/test_apipay_webhook.py`, add:

```python
@pytest.mark.anyio
async def test_apipay_webhook_subscription_payment_failed_no_status_change(db: Session):
    """payment_failed should NOT set past_due — just log and notify with retry message."""
    from app.billing.repository import create_or_update_subscription
    from datetime import datetime, timedelta, timezone

    user_id = 80010
    provider_sub_id = "sub_999"
    end = datetime.now(timezone.utc) + timedelta(days=10)
    create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=end,
        provider_type="apipay",
        provider_subscription_id=provider_sub_id,
    )
    db.commit()

    payload = {
        "event": "subscription.payment_failed",
        "subscription": {"id": int(provider_sub_id.replace("sub_", ""))},
    }
    body = json.dumps(payload).encode()

    with (
        patch("app.billing.api.verify_apipay_signature", return_value=True),
        patch("app.billing.service.send_telegram_message", new_callable=AsyncMock) as mock_send,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/billing/apipay/webhook",
            content=body,
            headers={"X-Webhook-Signature": "sha256=dummy"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Status must remain "active" — no state mutation
    db.expire_all()
    from sqlmodel import select
    from app.billing.models import Subscription
    sub = db.exec(select(Subscription).where(Subscription.telegram_user_id == user_id)).one()
    assert sub.status == "active"

    # User must be notified with retry message
    from app.billing.prompts import PAYMENT_RETRY_MESSAGE
    mock_send.assert_called_once_with(user_id, PAYMENT_RETRY_MESSAGE)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/billing/test_apipay_webhook.py::test_apipay_webhook_subscription_payment_failed_no_status_change -v
```
Expected: FAIL — current code sets `past_due`

- [ ] **Step 3: Fix `payment_failed` handler in `service.py`**

Find the `if event == "subscription.payment_failed":` block (around line 104). Replace the entire block with:

```python
if event == "subscription.payment_failed":
    provider_sub_id = str(subscription_data.get("id"))
    sub = repository.get_subscription_by_provider_id(session, provider_sub_id)
    if not sub:
        logger.warning("Subscription not found for provider_sub_id=%s", provider_sub_id)
        return {"status": "error", "message": "subscription_not_found"}

    logger.info("Payment failed for subscription provider_sub_id=%s, ApiPay will retry", provider_sub_id)
    await send_telegram_message(sub.telegram_user_id, PAYMENT_RETRY_MESSAGE)
    return {"status": "ok", "message": "payment_failed_notified"}
```

Also add `PAYMENT_RETRY_MESSAGE` to the imports at the top of `service.py`:
```python
from app.billing.prompts import (
    ...
    PAYMENT_RETRY_MESSAGE,
    ...
)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/billing/test_apipay_webhook.py::test_apipay_webhook_subscription_payment_failed_no_status_change -v
```
Expected: PASS

- [ ] **Step 5: Run full billing test suite**

```bash
cd backend && uv run pytest tests/billing/ -v
```
Expected: All tests pass (existing `subscription.payment_failed` tests should be updated or pass with new behavior)

- [ ] **Step 6: Commit**

```bash
git add backend/app/billing/service.py backend/tests/billing/test_apipay_webhook.py
git commit -m "fix(billing): payment_failed no longer mutates subscription status"
```

---

## Task 3: Add `grace_period_started` handler and fix `build_status_response`

**Files:**
- Modify: `backend/app/billing/service.py`
- Modify: `backend/tests/billing/test_apipay_webhook.py`

- [ ] **Step 1: Write failing test for `grace_period_started`**

In `backend/tests/billing/test_apipay_webhook.py`, add:

```python
@pytest.mark.anyio
async def test_apipay_webhook_grace_period_started(db: Session):
    """grace_period_started should set status=past_due and current_period_end=expires_at."""
    from app.billing.repository import create_or_update_subscription
    from app.billing.models import Subscription
    from datetime import datetime, timedelta, timezone

    user_id = 80020
    provider_sub_id = "501"
    expires_at = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

    create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        provider_type="apipay",
        provider_subscription_id=provider_sub_id,
    )
    db.commit()

    payload = {
        "event": "subscription.grace_period_started",
        "subscription": {"id": int(provider_sub_id)},
        "expires_at": expires_at,
    }
    body = json.dumps(payload).encode()

    with (
        patch("app.billing.api.verify_apipay_signature", return_value=True),
        patch("app.billing.service.send_telegram_message", new_callable=AsyncMock) as mock_send,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/billing/apipay/webhook",
            content=body,
            headers={"X-Webhook-Signature": "sha256=dummy"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "grace_period_started"}

    db.expire_all()
    sub = db.exec(select(Subscription).where(Subscription.telegram_user_id == user_id)).one()
    assert sub.status == "past_due"
    # current_period_end should be the grace period end (expires_at), not the original billing period end
    assert abs((sub.current_period_end - datetime.fromisoformat(expires_at)).total_seconds()) < 2

    # User must be notified about grace period
    mock_send.assert_called_once()
    call_args = mock_send.call_args[0]
    assert call_args[0] == user_id
    assert "Льготный период" in call_args[1] or "ч." in call_args[1]


@pytest.mark.anyio
async def test_apipay_webhook_grace_period_started_sub_not_found():
    """grace_period_started with unknown subscription returns error."""
    payload = {
        "event": "subscription.grace_period_started",
        "subscription": {"id": 99999},
        "expires_at": "2026-04-01T00:00:00+00:00",
    }
    body = json.dumps(payload).encode()

    with patch("app.billing.api.verify_apipay_signature", return_value=True):
        response = client.post(
            f"{settings.API_V1_STR}/billing/apipay/webhook",
            content=body,
            headers={"X-Webhook-Signature": "sha256=dummy"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "error", "message": "subscription_not_found"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/billing/test_apipay_webhook.py::test_apipay_webhook_grace_period_started -v
```
Expected: FAIL — handler doesn't exist yet

- [ ] **Step 3: Add `grace_period_started` handler in `service.py`**

In `process_apipay_webhook`, after the `subscription.payment_failed` block and before the final `return {"status": "ignored", ...}`, add:

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

- [ ] **Step 4: Fix `build_status_response` grace period calculation**

In `service.py`, in `build_status_response`, find the `past_due` branch:
```python
grace_end = subscription.current_period_end + timedelta(hours=24)
```
Replace with:
```python
grace_end = subscription.current_period_end
```
(Now `current_period_end` for `past_due` subscriptions IS the grace period end, set by `grace_period_started` webhook.)

- [ ] **Step 5: Run tests**

```bash
cd backend && uv run pytest tests/billing/test_apipay_webhook.py::test_apipay_webhook_grace_period_started tests/billing/test_apipay_webhook.py::test_apipay_webhook_grace_period_started_sub_not_found -v
```
Expected: PASS

- [ ] **Step 6: Run full billing suite**

```bash
cd backend && uv run pytest tests/billing/ -v
```
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/billing/service.py backend/tests/billing/test_apipay_webhook.py
git commit -m "feat(billing): add grace_period_started webhook handler, fix build_status_response"
```

---

## Task 4: Add `invoice.refunded` handler

**Files:**
- Modify: `backend/app/billing/service.py`
- Modify: `backend/tests/billing/test_apipay_webhook.py`

- [ ] **Step 1: Write failing test**

In `backend/tests/billing/test_apipay_webhook.py`, add:

```python
def test_apipay_webhook_invoice_refunded_ignored():
    """invoice.refunded should be logged and return ok without DB changes."""
    payload = {
        "event": "invoice.refunded",
        "refund": {"id": 5, "amount": "2000.00", "status": "completed"},
        "invoice": {"id": 42, "external_order_id": "order_123"},
    }
    body = json.dumps(payload).encode()

    with patch("app.billing.api.verify_apipay_signature", return_value=True):
        response = client.post(
            f"{settings.API_V1_STR}/billing/apipay/webhook",
            content=body,
            headers={"X-Webhook-Signature": "sha256=dummy"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["message"] == "refund_logged"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/billing/test_apipay_webhook.py::test_apipay_webhook_invoice_refunded_ignored -v
```
Expected: FAIL — returns `ignored` currently

- [ ] **Step 3: Add `invoice.refunded` handler in `service.py`**

In `process_apipay_webhook`, after the `invoice.status_changed` block, add:

```python
if event == "invoice.refunded":
    refund_data = payload.get("refund", {})
    invoice_data_refund = payload.get("invoice", {})
    logger.info(
        "invoice.refunded received: refund_id=%s invoice_id=%s amount=%s — no action taken",
        refund_data.get("id"),
        invoice_data_refund.get("id"),
        refund_data.get("amount"),
    )
    return {"status": "ok", "message": "refund_logged"}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/billing/test_apipay_webhook.py::test_apipay_webhook_invoice_refunded_ignored -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/billing/service.py backend/tests/billing/test_apipay_webhook.py
git commit -m "feat(billing): handle invoice.refunded webhook (log only)"
```

---

## Task 5: Remove local state machine from `check_and_update_subscription_status`

**Files:**
- Modify: `backend/app/billing/service.py`
- Modify: `backend/tests/billing/test_subscriptions.py`

- [ ] **Step 1: Update `test_subscriptions.py` — replace auto-transition tests**

The old tests (`test_grace_period_access`, `test_suspended_access_after_grace_period`) test the local state machine we're removing. Replace them with tests that verify the new behavior — status is only set by webhooks:

```python
def test_check_subscription_status_read_only(db: Session):
    """check_and_update_subscription_status must NOT mutate status, even if period has expired."""
    user_id = 55555
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="active",
        current_period_end=expired_time,
    )
    db.commit()

    sub = service.check_and_update_subscription_status(db, user_id)
    # Status must remain "active" — no automatic transition
    assert sub.status == "active"
    # No flush/commit should have happened
    db.expire_all()
    sub_reloaded = repository.get_subscription(db, user_id)
    assert sub_reloaded.status == "active"


def test_has_premium_access_past_due_subscription(db: Session):
    """past_due subscription (set by webhook) still grants premium access."""
    user_id = 55556
    # Simulate what grace_period_started webhook would set
    expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="past_due",
        current_period_end=expires_at,
    )
    db.commit()

    assert service.has_premium_access(db, user_id) is True


def test_has_premium_access_suspended_subscription(db: Session):
    """suspended subscription (set by subscription.expired webhook) revokes access."""
    user_id = 66666
    repository.create_or_update_subscription(
        db,
        telegram_user_id=user_id,
        status="suspended",
        current_period_end=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.commit()

    assert service.has_premium_access(db, user_id) is False
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
cd backend && uv run pytest tests/billing/test_subscriptions.py::test_check_subscription_status_read_only -v
```
Expected: FAIL — function still mutates status

- [ ] **Step 3: Remove mutations from `check_and_update_subscription_status` in `service.py`**

Find `check_and_update_subscription_status` (around line 393). Replace the entire function body with:

```python
def check_and_update_subscription_status(
    session: Session, telegram_user_id: int
) -> Subscription | None:
    """Return current subscription. Read-only — status transitions happen via ApiPay webhooks."""
    return repository.get_subscription(session, telegram_user_id)
```

- [ ] **Step 4: Run new tests to verify they pass**

```bash
cd backend && uv run pytest tests/billing/test_subscriptions.py -v
```
Expected: All pass

- [ ] **Step 5: Run full billing suite**

```bash
cd backend && uv run pytest tests/billing/ -v
```
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/billing/service.py backend/tests/billing/test_subscriptions.py
git commit -m "refactor(billing): check_and_update_subscription_status is now read-only"
```

---

## Task 6: Update `test_status_command.py` for webhook-driven status

**Files:**
- Modify: `backend/tests/billing/test_status_command.py`

The `test_status_command_subscription_past_due` and `test_status_command_subscription_suspended` tests currently create subscriptions with `status="active"` and expired `current_period_end`, relying on the old state machine to auto-transition them. After Task 5, this won't work. Update them to set status directly.

- [ ] **Step 1: Update `test_status_command_subscription_past_due`**

Find the test and change the subscription setup from:
```python
end_date = datetime.now(timezone.utc) - timedelta(hours=1)
create_or_update_subscription(db, telegram_user_id=user_id, status="active", current_period_end=end_date)
```
To:
```python
# Simulate what grace_period_started webhook would set:
# current_period_end = grace period end (23 hours from now)
grace_end = datetime.now(timezone.utc) + timedelta(hours=23)
create_or_update_subscription(db, telegram_user_id=user_id, status="past_due", current_period_end=grace_end)
```
And update the assertion accordingly (now ~23h remaining):
```python
assert "Льготный период" in resp.messages[0].text
assert re.search(r"\d+ ч\.", resp.messages[0].text)
assert resp.inline_keyboard[0][0].callback_data == "pay:kaspi"
```

- [ ] **Step 2: Update `test_status_command_subscription_suspended`**

Change:
```python
end_date = datetime.now(timezone.utc) - timedelta(hours=25)
create_or_update_subscription(db, telegram_user_id=user_id, status="active", current_period_end=end_date)
```
To:
```python
create_or_update_subscription(db, telegram_user_id=user_id, status="suspended",
    current_period_end=datetime.now(timezone.utc) - timedelta(days=1))
```

- [ ] **Step 3: Run the updated tests**

```bash
cd backend && uv run pytest tests/billing/test_status_command.py -v
```
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add backend/tests/billing/test_status_command.py
git commit -m "test(billing): update status command tests for webhook-driven subscription state"
```

---

## Task 7: Add `external_subscriber_id` to `ApiPayClient` and `create_apipay_subscription`

**Files:**
- Modify: `backend/app/billing/apipay_client.py`
- Modify: `backend/app/billing/service.py`
- Modify: `backend/tests/billing/test_apipay_subscriptions.py`

- [ ] **Step 1: Write failing test**

In `backend/tests/billing/test_apipay_subscriptions.py`, add:

```python
@pytest.mark.anyio
async def test_create_apipay_subscription_passes_external_subscriber_id(db):
    """create_apipay_subscription should pass telegram_user_id as external_subscriber_id."""
    from unittest.mock import AsyncMock, patch, MagicMock
    from app.billing.service import create_apipay_subscription
    from app.billing.apipay_client import ApiPaySubscriptionResponse

    mock_response = ApiPaySubscriptionResponse(id=1, status="active", amount=3000.0, billing_period="monthly")

    with patch("app.billing.service.ApiPayClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.create_subscription = AsyncMock(return_value=mock_response)

        await create_apipay_subscription(db, telegram_user_id=12345, phone_number="87001234567")

        call_kwargs = mock_instance.create_subscription.call_args.kwargs
        assert call_kwargs["external_subscriber_id"] == "12345"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/billing/test_apipay_subscriptions.py::test_create_apipay_subscription_passes_external_subscriber_id -v
```
Expected: FAIL — `external_subscriber_id` not passed yet

- [ ] **Step 3: Add `external_subscriber_id` to `ApiPayClient.create_subscription`**

In `backend/app/billing/apipay_client.py`, update `create_subscription` signature and payload:

```python
async def create_subscription(
    self,
    *,
    amount: float,
    phone_number: str,
    period: str = "monthly",
    description: str | None = None,
    external_subscriber_id: str | None = None,
) -> ApiPaySubscriptionResponse:
    """Create a recurring subscription in ApiPay."""
    payload: dict[str, Any] = {
        "amount": amount,
        "phone_number": phone_number,
        "billing_period": period,
    }
    if description:
        payload["description"] = description
    if external_subscriber_id:
        payload["external_subscriber_id"] = external_subscriber_id
    # ... rest unchanged
```

- [ ] **Step 4: Pass `external_subscriber_id` in `create_apipay_subscription`**

In `backend/app/billing/service.py`, update the `client.create_subscription(...)` call inside `create_apipay_subscription`:

```python
response = await client.create_subscription(
    amount=float(amount_kzt),
    phone_number=normalized_phone,
    description=f"Premium monthly subscription for {telegram_user_id}",
    external_subscriber_id=str(telegram_user_id),
)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/billing/test_apipay_subscriptions.py::test_create_apipay_subscription_passes_external_subscriber_id -v
```
Expected: PASS

- [ ] **Step 6: Run full billing suite**

```bash
cd backend && uv run pytest tests/billing/ -v
```
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/billing/apipay_client.py backend/app/billing/service.py backend/tests/billing/test_apipay_subscriptions.py
git commit -m "feat(billing): pass external_subscriber_id when creating ApiPay subscription"
```

---

## Final Check

- [ ] **Run full test suite**

```bash
cd backend && uv run pytest tests/ -v --tb=short
```
Expected: All pass, no regressions
