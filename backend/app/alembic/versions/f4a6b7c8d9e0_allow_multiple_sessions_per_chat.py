"""Allow multiple sessions per Telegram user/chat pair

Revision ID: f4a6b7c8d9e0
Revises: c1d2e3f4a5b6
Create Date: 2026-03-13 20:50:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f4a6b7c8d9e0"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_telegram_session_user_chat",
        "telegram_session",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_telegram_session_user_chat",
        "telegram_session",
        ["telegram_user_id", "chat_id"],
    )
