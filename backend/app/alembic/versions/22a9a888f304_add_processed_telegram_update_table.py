"""add_processed_telegram_update_table

Revision ID: 22a9a888f304
Revises: ebf7a6e55215
Create Date: 2026-03-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '22a9a888f304'
down_revision = 'ebf7a6e55215'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_telegram_update",
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("update_id"),
    )


def downgrade() -> None:
    op.drop_table("processed_telegram_update")
