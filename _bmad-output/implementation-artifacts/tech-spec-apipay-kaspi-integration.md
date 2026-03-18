# Tech Spec: Kaspi.kz Integration via ApiPay.kz

**Status:** Draft
**Epic:** 7 - Scaling and Management
**Domain:** Billing / Payments

## 1. Goal
Provide users in Kazakhstan with a familiar and preferred way to pay for Premium access using Kaspi.kz (via the ApiPay.kz gateway). This includes one-time payments and automated recurring subscriptions.

## 2. Technical Architecture

### 2.1 Provider Boundary
We will implement an `ApiPayProvider` that adheres to our internal billing provider interface.
- **Base URL:** `https://bpapi.bazarbay.site/api/v1`
- **Auth:** `X-API-Key` header.
- **Verification:** HMAC SHA256 signature on webhooks.

### 2.2 Data Model Changes
- **`PurchaseIntent`**: Add `provider_invoice_id` (ApiPay ID) and `phone_number`.
- **`Subscription`**: Add `provider_subscription_id` and `provider_type` (telegram_stars vs apipay).

### 2.3 Conversational Flow (Telegram)
1. User clicks "Оформить Premium ✦" (or a new "Оплатить через Kaspi" button).
2. Bot requests phone number using `KeyboardButton(text="Отправить номер телефона", request_contact=True)`.
3. Upon receiving contact, bot calls `POST /invoices` (ApiPay).
4. Bot informs user: "Счет на оплату отправлен в ваше приложение Kaspi.kz. Пожалуйста, подтвердите его."
5. Bot waits for Webhook from ApiPay.

## 3. Implementation Details

### 3.1 Configuration (`core/config.py`)
- `APIPAY_API_KEY`: string
- `APIPAY_WEBHOOK_SECRET`: string
- `APIPAY_SANDBOX`: bool (default: True)

### 3.2 Service Layer (`billing/apipay_service.py`)
- `create_invoice(telegram_user_id, phone, amount)`: Calls ApiPay and returns invoice ID.
- `handle_webhook(payload, signature)`: Verifies signature and updates database.
- `initiate_subscription(telegram_user_id, phone, amount)`: Sets up recurring billing.

### 3.3 Webhook Endpoint (`api/v1/billing/apipay.py`)
- Endpoint: `POST /api/v1/billing/apipay/webhook`
- Handles `invoice.status_changed` and `subscription.*` events.

## 4. Security
- Strict signature verification using `APIPAY_WEBHOOK_SECRET`.
- Phone numbers are stored only in `PurchaseIntent` for tracking, not used for marketing.
- Secret keys managed via environment variables.

## 5. Success Criteria
- User can pay via Kaspi and get Premium access within 30 seconds of confirmation.
- Subscriptions correctly renew or enter `past_due` state on failure.
- Webhook handling is idempotent.
