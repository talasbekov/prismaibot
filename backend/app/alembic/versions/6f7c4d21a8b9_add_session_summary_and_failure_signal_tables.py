"""Add session summary and failure signal tables

Revision ID: 6f7c4d21a8b9
Revises: b5f1f1729d3f
Create Date: 2026-03-12 18:35:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision: str = "6f7c4d21a8b9"
down_revision: str | None = "b5f1f1729d3f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "session_summary",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column(
            "telegram_user_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "reflective_mode",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="deep",
        ),
        sa.Column("source_turn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "takeaway",
            sqlmodel.sql.sqltypes.AutoString(length=1000),
            nullable=False,
        ),
        sa.Column("key_facts", sa.JSON(), nullable=False),
        sa.Column("emotional_tensions", sa.JSON(), nullable=False),
        sa.Column("uncertainty_notes", sa.JSON(), nullable=False),
        sa.Column("next_step_context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["telegram_session.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_session_summary_session"),
    )
    op.create_index(
        op.f("ix_session_summary_session_id"),
        "session_summary",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_summary_telegram_user_id"),
        "session_summary",
        ["telegram_user_id"],
        unique=False,
    )

    op.create_table(
        "summary_generation_signal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "signal_type",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=False,
            server_default="session_summary_failed",
        ),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="open",
        ),
        sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["telegram_session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_summary_generation_signal_session_id"),
        "summary_generation_signal",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_summary_generation_signal_telegram_user_id"),
        "summary_generation_signal",
        ["telegram_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_summary_generation_signal_telegram_user_id"),
        table_name="summary_generation_signal",
    )
    op.drop_index(
        op.f("ix_summary_generation_signal_session_id"),
        table_name="summary_generation_signal",
    )
    op.drop_table("summary_generation_signal")

    op.drop_index(op.f("ix_session_summary_telegram_user_id"), table_name="session_summary")
    op.drop_index(op.f("ix_session_summary_session_id"), table_name="session_summary")
    op.drop_table("session_summary")
