"""Add unique constraint on (session_id, turn_index) to safety_signal

Revision ID: bc23de45fg67
Revises: ab12cd34ef56
Create Date: 2026-03-13 14:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "bc23de45fg67"
down_revision: str | None = "ab12cd34ef56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_safety_signal_session_turn",
        "safety_signal",
        ["session_id", "turn_index"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_safety_signal_session_turn",
        "safety_signal",
        type_="unique",
    )
