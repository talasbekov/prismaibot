"""Add telegram session table

Revision ID: 3f0d7f6b9a11
Revises: fe56fa70289e
Create Date: 2026-03-11 22:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f0d7f6b9a11"
down_revision: str | None = "fe56fa70289e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "telegram_session",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
        ),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column(
            "last_user_message",
            sqlmodel.sql.sqltypes.AutoString(length=2000),
            nullable=True,
        ),
        sa.Column(
            "last_bot_prompt",
            sqlmodel.sql.sqltypes.AutoString(length=2000),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "telegram_user_id", "chat_id", name="uq_telegram_session_user_chat"
        ),
    )
    op.create_index(
        op.f("ix_telegram_session_chat_id"),
        "telegram_session",
        ["chat_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_telegram_session_telegram_user_id"),
        "telegram_session",
        ["telegram_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_telegram_session_telegram_user_id"), table_name="telegram_session")
    op.drop_index(op.f("ix_telegram_session_chat_id"), table_name="telegram_session")
    op.drop_table("telegram_session")
