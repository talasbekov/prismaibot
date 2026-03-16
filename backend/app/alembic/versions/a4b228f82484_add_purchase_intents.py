"""add_purchase_intents

Revision ID: a4b228f82484
Revises: f1a2b3c4d5e6
Create Date: 2026-03-14 20:54:04.374667

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'a4b228f82484'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "purchase_intents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("invoice_payload", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("provider_payment_charge_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_payload", name="uq_purchase_intents_invoice_payload"),
    )
    op.create_index(
        op.f("ix_purchase_intents_telegram_user_id"),
        "purchase_intents",
        ["telegram_user_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_purchase_intents_telegram_user_id"), table_name="purchase_intents")
    op.drop_table("purchase_intents")
