"""Add operator alert table

Revision ID: a7f9c3d2b4e1
Revises: c1d2e3f4a5b6
Create Date: 2026-03-14 19:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision: str = "a7f9c3d2b4e1"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operator_alert",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "classification",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="safe",
        ),
        sa.Column(
            "trigger_category",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
            server_default="none",
        ),
        sa.Column(
            "confidence",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="low",
        ),
        sa.Column(
            "delivery_channel",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
            server_default="ops_inbox",
        ),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
            server_default="created",
        ),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("delivery_attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "dedupe_key",
            sqlmodel.sql.sqltypes.AutoString(length=128),
            nullable=False,
        ),
        sa.Column(
            "last_delivery_error",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.Column("first_routed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_delivery_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["telegram_session.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_operator_alert_session"),
    )
    op.create_index(
        op.f("ix_operator_alert_session_id"),
        "operator_alert",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_operator_alert_telegram_user_id"),
        "operator_alert",
        ["telegram_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_operator_alert_telegram_user_id"), table_name="operator_alert")
    op.drop_index(op.f("ix_operator_alert_session_id"), table_name="operator_alert")
    op.drop_table("operator_alert")
