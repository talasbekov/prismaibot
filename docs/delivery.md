# Delivery Guide

This project uses one backend service plus PostgreSQL. Delivery must preserve the order `db -> migrations/prestart -> backend traffic`.

## Environment Files

- `/.env.example`: local template with insecure placeholders for development only
- `/.env.staging.example`: staging shape for managed-platform rollout
- `/.env.production.example`: production shape for managed-platform rollout

Required non-local secrets:

- `SECRET_KEY`
- `FIRST_SUPERUSER`
- `FIRST_SUPERUSER_PASSWORD`
- `POSTGRES_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`
- `OPS_AUTH_TOKEN`
- `PAYMENT_PROVIDER_WEBHOOK_SECRET`

Required non-local runtime settings:

- `ENVIRONMENT=staging|production`
- `DEPLOYMENT_TARGET=railway|render`
- `POSTGRES_SERVER`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `BACKEND_BASE_URL`

Optional legacy-web runtime setting:

- `FRONTEND_HOST` only if password-reset email flows remain enabled for the target environment

## Local Verification

From the repo root:

```bash
docker compose up -d db mailcatcher
cd backend
uv sync --frozen --group dev
uv run bash scripts/ci-verify.sh
cd ..
docker compose build prestart backend
docker compose up -d backend
curl --fail http://localhost:8000/api/v1/ops/healthz
curl --fail http://localhost:8000/api/v1/ops/readyz
curl --fail http://localhost:8000/api/v1/ops/auth-check \
  -H 'X-Ops-Auth-Token: local-ops-auth-token'
curl --fail -X POST http://localhost:8000/api/v1/telegram/webhook \
  -H 'Content-Type: application/json' \
  -d '{"update_id": 999}'
curl --fail -X POST http://localhost:8000/api/v1/billing/webhook \
  -H 'Content-Type: application/json' \
  -H 'X-Payment-Webhook-Secret: local-payment-webhook-secret' \
  -d '{"type": "payment.failed"}'
docker compose down -v --remove-orphans
```

Expected webhook seam result for the smoke payload: `{"status":"ignored", ...}`.

## CI Baseline

GitHub Actions workflow `test-backend.yml` is the required backend gate. It now enforces:

- `ruff check app tests`
- `mypy app tests`
- `alembic upgrade head` through `backend/scripts/prestart.sh`
- full pytest suite with coverage
- runtime smoke checks for `healthz`, `readyz`, `ops/auth-check`, Telegram ingress, and the payment callback seam

Do not treat a change as delivery-ready if only the tests pass but migration or readiness validation fails.

## Staging and Production Verification

GitHub Actions workflows:

- `.github/workflows/deploy-staging.yml`
- `.github/workflows/deploy-production.yml`

These workflows use GitHub Environments (`staging`, `production`) and now perform the managed-platform deployment after verification.

Each workflow:

1. loads environment-specific secrets
2. runs the same migration-aware quality gates as CI
3. boots the backend in the target environment mode
4. verifies `healthz`, `readyz`, `ops/auth-check`, Telegram ingress, and the payment callback seam locally
5. deploys to Railway or Render based on `DEPLOYMENT_TARGET`
6. waits for remote readiness and re-runs operator/payment verification against `BACKEND_BASE_URL`

## Managed Platform Rollout

Preferred targets:

- `railway`
- `render`

Rollout sequence:

1. sync the target environment secrets from the matching example file
2. configure the matching GitHub Environment vars/secrets, including `BACKEND_BASE_URL`
3. ensure the target platform already has its migration/predeploy command configured to preserve `prestart -> backend` ordering
4. run the corresponding GitHub deployment workflow
5. let the workflow deploy to Railway or Render and wait for remote readiness
6. verify `/api/v1/ops/readyz`, `/api/v1/ops/auth-check`, and `/api/v1/billing/webhook` on the deployed service
7. send a Telegram webhook smoke payload only in staging, not production

If migrations fail, readiness is red, operator auth fails, or callback verification fails, stop the rollout and fix the issue before retrying.
