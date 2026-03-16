"""Add brainstorm_phase and brainstorm_data to telegram_session

Revision ID: b3c4d5e6f7a8
Revises: 22a9a888f304
Create Date: 2026-03-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "22a9a888f304"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "telegram_session",
        sa.Column("brainstorm_phase", sa.String(32), nullable=True),
    )
    op.add_column(
        "telegram_session",
        sa.Column("brainstorm_data", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("telegram_session", "brainstorm_data")
    op.drop_column("telegram_session", "brainstorm_phase")
