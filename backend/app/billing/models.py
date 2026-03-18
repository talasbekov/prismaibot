import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


def _get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class UserAccessState(SQLModel, table=True):
    __tablename__ = "user_access_states"
    __table_args__ = (
        UniqueConstraint("telegram_user_id", name="uq_user_access_states_telegram_user"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())  # type: ignore[call-overload]
    access_tier: str = Field(default="free", max_length=32)
    free_sessions_used: int = Field(default=0)
    first_session_completed: bool = Field(default=False)
    threshold_reached_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    created_at: datetime | None = Field(
        default_factory=_get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=_get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class FreeSessionEvent(SQLModel, table=True):
    __tablename__ = "free_session_events"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_free_session_events_session"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())  # type: ignore[call-overload]
    session_id: uuid.UUID = Field(index=True)
    recorded_at: datetime | None = Field(
        default_factory=_get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class PurchaseIntent(SQLModel, table=True):
    __tablename__ = "purchase_intents"
    __table_args__ = (
        UniqueConstraint("invoice_payload", name="uq_purchase_intents_invoice_payload"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())  # type: ignore[call-overload]
    provider_type: str = Field(default="telegram_stars", max_length=32)
    provider_invoice_id: str | None = Field(default=None, index=True)
    phone_number: str | None = Field(default=None, max_length=32)
    invoice_payload: str = Field()
    amount: int
    currency: str = Field(default="XTR", max_length=16)
    status: str = Field(default="pending", max_length=32)
    provider_payment_charge_id: str | None = Field(default=None)
    created_at: datetime | None = Field(
        default_factory=_get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=_get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("provider_subscription_id", name="uq_subscriptions_provider_subscription_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())  # type: ignore[call-overload]
    provider_type: str = Field(default="telegram_stars", max_length=32)
    provider_subscription_id: str | None = Field(default=None, index=True)
    status: str = Field(default="active", max_length=32)  # active, past_due, suspended, cancelled
    current_period_end: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    cancel_at_period_end: bool = Field(default=False)
    created_at: datetime | None = Field(
        default_factory=_get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=_get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
