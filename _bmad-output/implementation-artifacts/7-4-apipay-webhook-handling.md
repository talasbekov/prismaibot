# Story 7.4: Implement Webhook endpoint for ApiPay status updates

Status: done

## Story

As a developer,
I want to implement a secure webhook endpoint to receive payment updates from ApiPay,
So that I can automatically activate user subscriptions once they pay via Kaspi.

## Acceptance Criteria

1. **Given** an incoming request to `/api/v1/billing/apipay/webhook`, **When** the `X-Webhook-Signature` is valid, **Then** the system must process the payload. [Source: apipay.kz/docs.html]

2. **Given** an `invoice.status_changed` event with `status="paid"`, **When** the corresponding `PurchaseIntent` is found, **Then** the system must:
    - Update `PurchaseIntent` to `completed`.
    - Update/Create `Subscription` for the user (active, +30 days).
    - Send a "Payment Successful" message to the user via the Telegram bot. [Source: tech-spec-apipay-kaspi-integration.md]

3. **Given** an invalid signature, **When** a request is received, **Then** the system must return `401 Unauthorized` and log the incident. [Source: apipay.kz/docs.html]

4. **Given** a valid webhook, **When** processing is complete, **Then** the endpoint must return `200 OK` within 10 seconds to avoid retries. [Source: apipay.kz/docs.html]

## Tasks / Subtasks

- [x] Create `backend/app/api/v1/billing/apipay.py` with the webhook endpoint.
- [x] Implement signature verification middleware or dependency.
- [x] Implement `process_apipay_webhook` in `billing/service.py`.
- [x] Implement bot notification logic for successful payments.
- [x] Add integration tests for the webhook (with valid/invalid signatures).

## Dev Notes

- Use `BackgroundTasks` for bot notifications to keep the response time low.
- Ensure idempotency: if the same "paid" event is received twice, don't extend the subscription twice.

## References

- Tech Spec: `_bmad-output/implementation-artifacts/tech-spec-apipay-kaspi-integration.md`
