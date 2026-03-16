"""Add safety signal storage and session safety state

Revision ID: ab12cd34ef56
Revises: c1d2e3f4a5b6
Create Date: 2026-03-13 12:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision: str = "ab12cd34ef56"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "telegram_session",
        sa.Column(
            "safety_classification",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="safe",
        ),
    )
    op.add_column(
        "telegram_session",
        sa.Column(
            "safety_trigger_category",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "telegram_session",
        sa.Column(
            "safety_confidence",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="low",
        ),
    )
    op.add_column(
        "telegram_session",
        sa.Column("safety_last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "safety_signal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False, server_default="1"),
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["telegram_session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_safety_signal_session_id"),
        "safety_signal",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_safety_signal_telegram_user_id"),
        "safety_signal",
        ["telegram_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_safety_signal_telegram_user_id"), table_name="safety_signal")
    op.drop_index(op.f("ix_safety_signal_session_id"), table_name="safety_signal")
    op.drop_table("safety_signal")
    op.drop_column("telegram_session", "safety_last_evaluated_at")
    op.drop_column("telegram_session", "safety_confidence")
    op.drop_column("telegram_session", "safety_trigger_category")
    op.drop_column("telegram_session", "safety_classification")
