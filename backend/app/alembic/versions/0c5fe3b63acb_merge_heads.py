"""merge_heads

Revision ID: 0c5fe3b63acb
Revises: a4b228f82484, cd34ef45ab67, f4a6b7c8d9e0
Create Date: 2026-03-15 10:40:32.380879

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '0c5fe3b63acb'
down_revision = ('a4b228f82484', 'cd34ef45ab67', 'f4a6b7c8d9e0')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
