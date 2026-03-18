import os
import secrets
import warnings
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


def parse_admin_ids(v: Any) -> list[int]:
    if isinstance(v, list):
        valid = []
        for i in v:
            try:
                valid.append(int(i))
            except (ValueError, TypeError):
                pass
        return valid
    if isinstance(v, str) and v:
        valid = []
        for i in v.split(","):
            if i.strip():
                try:
                    valid.append(int(i.strip()))
                except ValueError:
                    pass
        return valid
    if isinstance(v, int):
        return [v]
    return []


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Resolve the top-level .env relative to the repository root, not the cwd.
        env_file=PROJECT_ROOT / ".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "https://example.invalid"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    DEPLOYMENT_TARGET: Literal["railway", "render", "generic"] = "railway"
    ENABLE_LEGACY_WEB_ROUTES: bool = False
    SAFETY_ENABLED: bool = True
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_WEBHOOK_SECRET: str | None = None
    OPS_AUTH_TOKEN: str | None = None
    PAYMENT_PROVIDER_WEBHOOK_SECRET: str | None = None
    OPENAI_API_KEY: str | None = None
    CONVERSATION_MIN_CLEAR_MESSAGE_LENGTH: int = 10
    CONVERSATION_CLOSURE_MIN_TURN_COUNT: int = 2
    CONVERSATION_DEFAULT_REFLECTIVE_MODE: str = "deep"
    MEMORY_MAX_RETRY_ATTEMPTS: int = 3
    # Number of completed reflective sessions a user may have before the premium boundary is considered.
    FREE_SESSION_THRESHOLD: int = 1
    # Price in Telegram Stars for premium access.
    PREMIUM_STARS_PRICE: int = 1
    # Price in KZT for Kaspi payments
    PREMIUM_KZT_PRICE: int = 3000
    # Interval in days for periodic reflective insight generation.
    INSIGHT_GENERATION_INTERVAL_DAYS: int = 7
    # Interval in hours for periodic reflective insight delivery.
    INSIGHT_DELIVERY_INTERVAL_HOURS: int = 24

    # ApiPay (Kaspi.kz) configuration
    APIPAY_API_KEY: str | None = None
    APIPAY_WEBHOOK_SECRET: str | None = None
    APIPAY_BASE_URL: str = "https://bpapi.bazarbay.site/api/v1"
    APIPAY_SANDBOX: bool = False

    # List of Telegram user IDs with administrative access
    ADMIN_IDS: Annotated[list[int], BeforeValidator(parse_admin_ids)] = []

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    def _require_non_local_setting(self, var_name: str, value: str | None) -> None:
        if self.ENVIRONMENT != "local" and not value:
            raise ValueError(
                f"{var_name} must be set in non-local environments to keep deploy validation reproducible."
            )

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )
        if self.ENVIRONMENT != "local" and "SECRET_KEY" not in os.environ:
            raise ValueError(
                "SECRET_KEY must be set via environment variable in non-local environments. "
                "The auto-generated default invalidates all JWT tokens on every restart."
            )
        if self.ENVIRONMENT != "local" and self.DEPLOYMENT_TARGET == "generic":
            raise ValueError(
                "DEPLOYMENT_TARGET must be explicitly set to 'railway' or 'render' in non-local environments."
            )
        self._require_non_local_setting("TELEGRAM_BOT_TOKEN", self.TELEGRAM_BOT_TOKEN)
        self._require_non_local_setting(
            "TELEGRAM_WEBHOOK_SECRET", self.TELEGRAM_WEBHOOK_SECRET
        )
        self._require_non_local_setting("OPS_AUTH_TOKEN", self.OPS_AUTH_TOKEN)
        self._require_non_local_setting(
            "PAYMENT_PROVIDER_WEBHOOK_SECRET",
            self.PAYMENT_PROVIDER_WEBHOOK_SECRET,
        )
        return self


settings = Settings()  # type: ignore
