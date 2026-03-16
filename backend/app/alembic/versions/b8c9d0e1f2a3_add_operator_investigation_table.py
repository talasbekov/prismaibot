"""add operator investigation table

Revision ID: b8c9d0e1f2a3
Revises: a7f9c3d2b4e1
Create Date: 2026-03-14 21:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7f9c3d2b4e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operator_investigation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("operator_alert_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "reason_code",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=False,
        ),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
            server_default="requested",
        ),
        sa.Column(
            "requested_by",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=False,
        ),
        sa.Column(
            "approved_by",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
        sa.Column(
            "reviewed_by",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
        sa.Column(
            "source_classification",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="safe",
        ),
        sa.Column(
            "source_trigger_category",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
            server_default="none",
        ),
        sa.Column(
            "source_confidence",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="low",
        ),
        sa.Column(
            "reviewed_classification",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=True,
        ),
        sa.Column(
            "outcome",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=True,
        ),
        sa.Column(
            "audit_notes",
            sqlmodel.sql.sqltypes.AutoString(length=1000),
            nullable=True,
        ),
        sa.Column("context_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["operator_alert_id"], ["operator_alert.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["telegram_session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_operator_investigation_operator_alert_id"),
        "operator_investigation",
        ["operator_alert_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_operator_investigation_session_id"),
        "operator_investigation",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_operator_investigation_telegram_user_id"),
        "operator_investigation",
        ["telegram_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_operator_investigation_telegram_user_id"),
        table_name="operator_investigation",
    )
    op.drop_index(
        op.f("ix_operator_investigation_session_id"),
        table_name="operator_investigation",
    )
    op.drop_index(
        op.f("ix_operator_investigation_operator_alert_id"),
        table_name="operator_investigation",
    )
    op.drop_table("operator_investigation")
