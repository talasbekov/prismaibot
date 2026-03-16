import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import EmailStr
from sqlalchemy import JSON, BigInteger, Column, DateTime, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


class TelegramSession(SQLModel, table=True):
    __tablename__ = "telegram_session"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())
    chat_id: int = Field(index=True, sa_type=BigInteger())
    status: str = Field(default="active", max_length=32)
    reflective_mode: str = Field(default="deep", max_length=16)
    mode_source: str = Field(default="default", max_length=16)
    turn_count: int = Field(default=0)
    working_context: str | None = Field(default=None, max_length=2000)
    last_user_message: str | None = Field(default=None, max_length=2000)
    last_bot_prompt: str | None = Field(default=None, max_length=2000)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    transcript_purged_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    safety_classification: str = Field(default="safe", max_length=16)
    safety_trigger_category: str = Field(default="none", max_length=32)
    safety_confidence: str = Field(default="low", max_length=16)
    safety_last_evaluated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    crisis_state: str = Field(
        default="normal",
        max_length=32,
    )  # values: "normal" | "crisis_active" | "step_down_pending"
    crisis_activated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    crisis_last_routed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    crisis_step_down_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    brainstorm_phase: str | None = Field(default=None, max_length=32)
    brainstorm_data: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )


class SessionSummary(SQLModel, table=True):
    __tablename__ = "session_summary"
    __table_args__ = (UniqueConstraint("session_id", name="uq_session_summary_session"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="telegram_session.id", nullable=False, index=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())
    reflective_mode: str = Field(default="deep", max_length=16)
    source_turn_count: int = Field(default=0)
    takeaway: str = Field(max_length=1000)
    key_facts: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    emotional_tensions: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    uncertainty_notes: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    next_step_context: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    retention_scope: str = Field(default="durable_summary", max_length=32)
    deletion_eligible: bool = True


class ProfileFact(SQLModel, table=True):
    __tablename__ = "profile_fact"
    __table_args__ = (
        UniqueConstraint("telegram_user_id", "fact_key", name="uq_profile_fact_user_key"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())
    source_session_id: uuid.UUID = Field(
        foreign_key="telegram_session.id", nullable=False, index=True
    )
    fact_key: str = Field(max_length=64)
    fact_value: str = Field(max_length=500)
    confidence: str = Field(default="medium", max_length=16)
    retention_scope: str = Field(default="durable_profile", max_length=32)
    deletion_eligible: bool = True
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    superseded_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class SummaryGenerationSignal(SQLModel, table=True):
    __tablename__ = "summary_generation_signal"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_summary_generation_signal_session"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="telegram_session.id", nullable=False, index=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())
    signal_type: str = Field(default="session_summary_failed", max_length=64)
    status: str = Field(default="open", max_length=16)
    retryable: bool = Field(default=True)
    details: dict[str, str] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    attempt_count: int = Field(default=1)
    retry_payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    retry_available_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class PeriodicInsight(SQLModel, table=True):
    __tablename__ = "periodic_insight"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())
    insight_text: str = Field(max_length=1500)
    basis_summary_count: int = Field(default=0)
    status: str = Field(default="pending_delivery", max_length=32)
    generation_error: str | None = Field(default=None, max_length=500)
    delivery_error: str | None = Field(default=None, max_length=500)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class SafetySignal(SQLModel, table=True):
    __tablename__ = "safety_signal"
    __table_args__ = (
        UniqueConstraint("session_id", "turn_index", name="uq_safety_signal_session_turn"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="telegram_session.id", nullable=False, index=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())
    turn_index: int = Field(default=1)
    classification: str = Field(default="safe", max_length=16)
    trigger_category: str = Field(default="none", max_length=32)
    confidence: str = Field(default="low", max_length=16)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class OperatorAlert(SQLModel, table=True):
    __tablename__ = "operator_alert"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_operator_alert_session"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="telegram_session.id", nullable=False, index=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())  # type: ignore[call-overload]
    classification: str = Field(default="safe", max_length=16)
    trigger_category: str = Field(default="none", max_length=32)
    confidence: str = Field(default="low", max_length=16)
    delivery_channel: str = Field(default="ops_inbox", max_length=32)
    status: str = Field(default="created", max_length=32)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    delivery_attempt_count: int = Field(default=0)
    dedupe_key: str = Field(default="", max_length=128)
    last_delivery_error: str | None = Field(default=None, max_length=500)
    first_routed_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    last_delivery_attempt_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    delivered_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class OperatorInvestigation(SQLModel, table=True):
    __tablename__ = "operator_investigation"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    operator_alert_id: uuid.UUID = Field(
        foreign_key="operator_alert.id", nullable=False, index=True
    )
    session_id: uuid.UUID = Field(foreign_key="telegram_session.id", nullable=False, index=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())  # type: ignore[call-overload]
    reason_code: str = Field(max_length=64)
    status: str = Field(default="requested", max_length=32)
    requested_by: str = Field(max_length=64)
    approved_by: str | None = Field(default=None, max_length=64)
    reviewed_by: str | None = Field(default=None, max_length=64)
    source_classification: str = Field(default="safe", max_length=16)
    source_trigger_category: str = Field(default="none", max_length=32)
    source_confidence: str = Field(default="low", max_length=16)
    reviewed_classification: str | None = Field(default=None, max_length=16)
    outcome: str | None = Field(default=None, max_length=64)
    audit_notes: str | None = Field(default=None, max_length=1000)
    context_payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    requested_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    approved_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    opened_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    closed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class DeletionRequest(SQLModel, table=True):
    __tablename__ = "deletion_request"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    telegram_user_id: int = Field(index=True, sa_type=BigInteger())  # type: ignore[call-overload]
    status: str = Field(default="pending", max_length=32)
    requested_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    audit_notes: str | None = Field(default=None, max_length=1000)


class ProcessedTelegramUpdate(SQLModel, table=True):
    __tablename__ = "processed_telegram_update"

    update_id: int = Field(primary_key=True, sa_type=BigInteger())
    processed_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
