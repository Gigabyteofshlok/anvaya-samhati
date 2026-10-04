"""add controlled clinical clearance to structured discharge

Revision ID: 3b7d9b9c68ee
Revises: e15ec6a400f1
"""
from alembic import op
import sqlalchemy as sa

revision = "3b7d9b9c68ee"
down_revision = "e15ec6a400f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("discharges", sa.Column("clinical_cleared", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("discharges", "clinical_cleared", server_default=None)


def downgrade() -> None:
    op.drop_column("discharges", "clinical_cleared")
