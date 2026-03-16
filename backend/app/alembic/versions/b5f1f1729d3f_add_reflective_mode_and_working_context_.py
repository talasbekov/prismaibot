"""Add reflective mode and working context to telegram session

Revision ID: b5f1f1729d3f
Revises: 3f0d7f6b9a11
Create Date: 2026-03-11 23:35:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision: str = "b5f1f1729d3f"
down_revision: str | None = "3f0d7f6b9a11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "telegram_session",
        sa.Column(
            "reflective_mode",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="deep",
        ),
    )
    op.add_column(
        "telegram_session",
        sa.Column(
            "working_context",
            sqlmodel.sql.sqltypes.AutoString(length=2000),
            nullable=True,
        ),
    )
    op.add_column(
        "telegram_session",
        sa.Column(
            "mode_source",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="default",
        ),
    )


def downgrade() -> None:
    op.drop_column("telegram_session", "mode_source")
    op.drop_column("telegram_session", "working_context")
    op.drop_column("telegram_session", "reflective_mode")
