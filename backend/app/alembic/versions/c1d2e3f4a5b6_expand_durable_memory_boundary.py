"""Expand durable memory boundary for summaries and profile facts

Revision ID: c1d2e3f4a5b6
Revises: 6f7c4d21a8b9
Create Date: 2026-03-12 20:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "6f7c4d21a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "telegram_session",
        sa.Column("transcript_purged_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "session_summary",
        sa.Column(
            "retention_scope",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
            server_default="durable_summary",
        ),
    )
    op.add_column(
        "session_summary",
        sa.Column(
            "deletion_eligible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.create_table(
        "profile_fact",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("source_session_id", sa.Uuid(), nullable=False),
        sa.Column(
            "fact_key",
            sqlmodel.sql.sqltypes.AutoString(length=64),
            nullable=False,
        ),
        sa.Column(
            "fact_value",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "retention_scope",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
            server_default="durable_profile",
        ),
        sa.Column(
            "deletion_eligible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_session_id"], ["telegram_session.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_user_id", "fact_key", name="uq_profile_fact_user_key"),
    )
    op.create_index(
        op.f("ix_profile_fact_telegram_user_id"),
        "profile_fact",
        ["telegram_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_profile_fact_source_session_id"),
        "profile_fact",
        ["source_session_id"],
        unique=False,
    )

    op.add_column(
        "summary_generation_signal",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "summary_generation_signal",
        sa.Column("retry_payload", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "summary_generation_signal",
        sa.Column("retry_available_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_summary_generation_signal_session",
        "summary_generation_signal",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_summary_generation_signal_session",
        "summary_generation_signal",
        type_="unique",
    )
    op.drop_column("summary_generation_signal", "retry_available_at")
    op.drop_column("summary_generation_signal", "retry_payload")
    op.drop_column("summary_generation_signal", "attempt_count")

    op.drop_index(op.f("ix_profile_fact_source_session_id"), table_name="profile_fact")
    op.drop_index(op.f("ix_profile_fact_telegram_user_id"), table_name="profile_fact")
    op.drop_table("profile_fact")

    op.drop_column("session_summary", "deletion_eligible")
    op.drop_column("session_summary", "retention_scope")
    op.drop_column("telegram_session", "transcript_purged_at")
