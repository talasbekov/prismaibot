# Story 7.5: Implement automated subscription management (Recurring Payments)

Status: done

## Story

As a developer,
I want to use ApiPay's subscription feature to automate recurring billing for Kaspi users,
So that users don't have to manually pay every 30 days.

## Acceptance Criteria

1. **Given** a successful first payment from Story 7.4, **When** the first month is near its end, **Then** the system should have already created a `Subscription` record in ApiPay via `POST /subscriptions`. [Source: apipay.kz/docs.html]

2. **Given** an automated renewal event, **When** ApiPay sends a `subscription.payment_succeeded` webhook, **Then** our system must extend the user's local `Subscription` by another 30 days. [Source: apipay.kz/docs.html]

3. **Given** a failed renewal, **When** ApiPay sends a `subscription.payment_failed` webhook, **Then** our system must:
    - Update local `Subscription` status to `past_due`.
    - Notify the user via the bot about the failed payment and the 24-hour grace period. [Source: tech-spec-apipay-kaspi-integration.md]

4. **Given** a subscription cancellation request, **When** the user sends `/cancel`, **Then** the system must call `DELETE /subscriptions/{id}` in ApiPay AND update the local record to `cancel_at_period_end = True`. [Source: tech-spec-apipay-kaspi-integration.md]

## Tasks / Subtasks

- [x] Implement `create_apipay_subscription` in `billing/service.py`.
- [x] Implement `cancel_apipay_subscription` in `billing/service.py`.
- [x] Update webhook handler to support `subscription.*` events.
- [x] Add integration tests for subscription lifecycle (success, fail, cancel).

## Dev Notes

- Automated subscriptions in Kaspi via ApiPay are handled on their side, but we must stay in sync.
- Use `monthly` period as per Epic 4 requirements.
- Ensure grace period settings in ApiPay match our internal 24-hour policy if possible, or handle it locally in `check_and_update_subscription_status`.

## References

- ApiPay Subscription Docs: https://apipay.kz/docs.html#subscriptions
- Tech Spec: `_bmad-output/implementation-artifacts/tech-spec-apipay-kaspi-integration.md`
