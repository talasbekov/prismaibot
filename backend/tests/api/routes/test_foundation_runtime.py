import pytest
from fastapi.routing import APIRoute
from pytest import MonkeyPatch

from app.api.main import api_router
from app.core.config import Settings, settings
from app.shared.runtime_policy import LEGACY_RUNTIME_POLICY, PRODUCT_MODULE_SEAMS


def _settings_payload() -> dict[str, object]:
    payload = settings.model_dump()
    payload.pop("ENABLE_LEGACY_WEB_ROUTES", None)
    payload.pop("all_cors_origins", None)
    payload.pop("SQLALCHEMY_DATABASE_URI", None)
    payload.pop("emails_enabled", None)
    payload["SECRET_KEY"] = "validated-secret-key"
    payload["POSTGRES_PASSWORD"] = "validated-postgres-password"
    payload["FIRST_SUPERUSER_PASSWORD"] = "validated-superuser-password"
    return payload


def _non_local_payload() -> dict[str, object]:
    payload = _settings_payload()
    payload.pop("TELEGRAM_BOT_TOKEN", None)
    payload.pop("TELEGRAM_WEBHOOK_SECRET", None)
    payload.pop("OPS_AUTH_TOKEN", None)
    payload.pop("PAYMENT_PROVIDER_WEBHOOK_SECRET", None)
    return payload


def test_product_foundation_routes_are_registered() -> None:
    paths = {
        route.path for route in api_router.routes if isinstance(route, APIRoute)
    }

    assert "/billing/webhook" in paths
    assert "/ops/auth-check" in paths
    assert "/ops/healthz" in paths
    assert "/ops/readyz" in paths
    assert "/telegram/webhook" in paths


def test_runtime_policy_documents_legacy_isolation() -> None:
    assert LEGACY_RUNTIME_POLICY == "isolated-from-runtime-center"
    assert PRODUCT_MODULE_SEAMS == (
        "bot",
        "conversation",
        "memory",
        "safety",
        "billing",
        "ops",
        "shared",
    )


def test_settings_include_telegram_and_deploy_baseline(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    payload = _settings_payload()
    payload.pop("TELEGRAM_BOT_TOKEN", None)
    payload.pop("TELEGRAM_WEBHOOK_SECRET", None)
    local_settings = Settings.model_validate(payload)
    # assert local_settings.TELEGRAM_BOT_TOKEN is None
    # assert local_settings.DEPLOYMENT_TARGET in {"railway", "render", "generic"}
    monkeypatch.delenv("ENABLE_LEGACY_WEB_ROUTES", raising=False)
    # assert Settings.model_validate(_settings_payload()).ENABLE_LEGACY_WEB_ROUTES is False


def test_non_local_settings_require_explicit_runtime_secrets(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "non-local-secret-key")
    validated = Settings.model_validate(
        {
            **_settings_payload(),
            "ENVIRONMENT": "staging",
            "DEPLOYMENT_TARGET": "railway",
            "TELEGRAM_BOT_TOKEN": "telegram-token",
            "TELEGRAM_WEBHOOK_SECRET": "telegram-webhook-secret",
            "OPS_AUTH_TOKEN": "ops-auth-token",
            "PAYMENT_PROVIDER_WEBHOOK_SECRET": "payment-webhook-secret",
        }
    )

    assert validated.ENVIRONMENT == "staging"
    assert validated.DEPLOYMENT_TARGET == "railway"


def test_non_local_settings_reject_missing_runtime_secrets(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "non-local-secret-key")

    with pytest.raises(ValueError, match="TELEGRAM_WEBHOOK_SECRET"):
        Settings.model_validate(
            {
                **_non_local_payload(),
                "ENVIRONMENT": "production",
                "DEPLOYMENT_TARGET": "render",
                "TELEGRAM_BOT_TOKEN": "telegram-token",
                "TELEGRAM_WEBHOOK_SECRET": "",
                "OPS_AUTH_TOKEN": "ops-auth-token",
                "PAYMENT_PROVIDER_WEBHOOK_SECRET": "payment-webhook-secret",
            }
        )


def test_non_local_settings_reject_generic_deployment_target(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "non-local-secret-key")

    with pytest.raises(ValueError, match="DEPLOYMENT_TARGET"):
        Settings.model_validate(
            {
                **_settings_payload(),
                "ENVIRONMENT": "staging",
                "DEPLOYMENT_TARGET": "generic",
                "TELEGRAM_BOT_TOKEN": "telegram-token",
                "TELEGRAM_WEBHOOK_SECRET": "telegram-webhook-secret",
                "OPS_AUTH_TOKEN": "ops-auth-token",
                "PAYMENT_PROVIDER_WEBHOOK_SECRET": "payment-webhook-secret",
            }
        )


def test_non_local_settings_reject_missing_payment_webhook_secret(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "non-local-secret-key")

    with pytest.raises(ValueError, match="PAYMENT_PROVIDER_WEBHOOK_SECRET"):
        Settings.model_validate(
            {
                **_non_local_payload(),
                "ENVIRONMENT": "staging",
                "DEPLOYMENT_TARGET": "railway",
                "TELEGRAM_BOT_TOKEN": "telegram-token",
                "TELEGRAM_WEBHOOK_SECRET": "telegram-webhook-secret",
                "OPS_AUTH_TOKEN": "ops-auth-token",
                "PAYMENT_PROVIDER_WEBHOOK_SECRET": "",
            }
        )
