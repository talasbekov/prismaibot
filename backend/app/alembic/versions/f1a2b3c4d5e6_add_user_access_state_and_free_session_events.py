"""Add user_access_states and free_session_events tables

Revision ID: f1a2b3c4d5e6
Revises: e7b9c1d2f3a4
Create Date: 2026-03-14 22:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e7b9c1d2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_access_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("access_tier", sa.String(length=32), nullable=False),
        sa.Column("free_sessions_used", sa.Integer(), nullable=False),
        sa.Column("threshold_reached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "telegram_user_id", name="uq_user_access_states_telegram_user"
        ),
    )
    op.create_index(
        op.f("ix_user_access_states_telegram_user_id"),
        "user_access_states",
        ["telegram_user_id"],
        unique=False,
    )
    op.create_table(
        "free_session_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_free_session_events_session"),
    )
    op.create_index(
        op.f("ix_free_session_events_telegram_user_id"),
        "free_session_events",
        ["telegram_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_free_session_events_session_id"),
        "free_session_events",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_free_session_events_session_id"),
        table_name="free_session_events",
    )
    op.drop_index(
        op.f("ix_free_session_events_telegram_user_id"),
        table_name="free_session_events",
    )
    op.drop_table("free_session_events")
    op.drop_index(
        op.f("ix_user_access_states_telegram_user_id"),
        table_name="user_access_states",
    )
    op.drop_table("user_access_states")
