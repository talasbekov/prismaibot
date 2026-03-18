# Story 7.3: Implement payment initiation flow (ApiPay Invoice)

Status: done

## Story

As a developer,
I want to implement the flow that creates an invoice in ApiPay when a user provides their phone number,
So that the user receives a payment push notification in their Kaspi app.

## Acceptance Criteria

1. **Given** a verified phone number from Story 7.2, **When** the bot processes the contact, **Then** it must call `POST /invoices` on the ApiPay API with the correct amount (3000 Stars equivalent in Tenge, e.g., 3000 KZT for MVP simplicity or as configured). [Source: apipay.kz/docs.html]

2. **Given** a successful API response from ApiPay, **When** the invoice is created, **Then** the system must create a `PurchaseIntent` in our DB with `status="pending"`, `provider_type="apipay"`, and `provider_invoice_id`. [Source: tech-spec-apipay-kaspi-integration.md]

3. **Given** the invoice creation, **When** the bot informs the user, **Then** the message must say: "Счет на 3000 ₸ отправлен в ваше приложение Kaspi.kz. Пожалуйста, подтвердите его." [Source: tech-spec-apipay-kaspi-integration.md]

4. **Given** an API failure (e.g., Kaspi session expired), **When** the request fails, **Then** the bot should send a polite error message and alert the operator if necessary. [Source: apipay.kz/docs.html]

## Tasks / Subtasks

- [x] Update `PurchaseIntent` model in `billing/models.py` to include ApiPay fields.
- [x] Implement `create_apipay_invoice` in `billing/service.py`.
- [x] Connect contact handling to invoice creation.
- [x] Add integration tests for invoice initiation (mocking ApiPay API).

## Dev Notes

- Price should be configurable. If we keep 3000 Stars as the base, we need a way to define the KZT equivalent (e.g., 1 Star = 1 KZT for simplicity, or 3000 KZT flat).
- Ensure idempotency: if a user sends their contact twice, don't create two invoices if one is already pending.

## References

- Tech Spec: `_bmad-output/implementation-artifacts/tech-spec-apipay-kaspi-integration.md`
