"""Add crisis routing state to telegram_session

Revision ID: cd34ef45ab67
Revises: bc23de45fg67
Create Date: 2026-03-13 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision: str = "cd34ef45ab67"
down_revision: str | None = "bc23de45fg67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "telegram_session",
        sa.Column(
            "crisis_state",
            sqlmodel.sql.sqltypes.AutoString(length=32),
            nullable=False,
            server_default="normal",
        ),
    )
    op.add_column(
        "telegram_session",
        sa.Column("crisis_activated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "telegram_session",
        sa.Column("crisis_last_routed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("telegram_session", "crisis_last_routed_at")
    op.drop_column("telegram_session", "crisis_activated_at")
    op.drop_column("telegram_session", "crisis_state")
