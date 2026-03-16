"""Add crisis step-down tracking to telegram_session

Revision ID: e7b9c1d2f3a4
Revises: b8c9d0e1f2a3
Create Date: 2026-03-14 22:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7b9c1d2f3a4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "telegram_session",
        sa.Column("crisis_step_down_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("telegram_session", "crisis_step_down_at")
