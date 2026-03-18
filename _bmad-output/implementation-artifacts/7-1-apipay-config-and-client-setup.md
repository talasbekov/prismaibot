# Story 7.1: Setup ApiPay configuration and client

Status: done

## Story

As a developer,
I want to set up the necessary configuration and API client for ApiPay.kz,
So that I can securely communicate with the Kaspi payment gateway.

## Acceptance Criteria

1. **Given** settings initialization, **When** the application starts, **Then** it must load `APIPAY_API_KEY`, `APIPAY_WEBHOOK_SECRET`, and `APIPAY_BASE_URL` from environment variables. [Source: tech-spec-apipay-kaspi-integration.md]

2. **Given** an API call to ApiPay, **When** the request is sent, **Then** it must include the `X-API-Key` header with the correct key. [Source: apipay.kz/docs.html]

3. **Given** an incoming webhook, **When** the payload is received, **Then** the system must provide a utility to verify the `X-Webhook-Signature` using the `APIPAY_WEBHOOK_SECRET`. [Source: apipay.kz/docs.html]

4. **Given** the sandbox requirement, **When** `APIPAY_SANDBOX` is True, **Then** all created invoices should have the `is_sandbox=true` property (if supported by the endpoint) or use the sandbox environment. [Source: apipay.kz/docs.html]

## Tasks / Subtasks

- [x] Update `backend/app/core/config.py` with new settings.
- [x] Create `backend/app/billing/apipay_client.py` with basic request methods (POST /invoices, POST /subscriptions).
- [x] Implement signature verification logic in `backend/app/billing/utils.py`.
- [x] Add unit tests for signature verification.

## Dev Notes

- Use `httpx` for the API client (as per project patterns).
- Ensure `APIPAY_BASE_URL` defaults to `https://bpapi.bazarbay.site/api/v1`.
- Signature verification must be timing-attack resilient using `hmac.compare_digest`.

## References

- ApiPay Documentation: https://apipay.kz/docs.html
- Tech Spec: `_bmad-output/implementation-artifacts/tech-spec-apipay-kaspi-integration.md`
