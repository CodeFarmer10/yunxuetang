"""add db_type column to databaseconnections

Revision ID: 002
Revises: 001
Create Date: 2026-07-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add db_type column to databaseconnections."""
    op.add_column(
        'databaseconnections',
        sa.Column('db_type', sa.String(length=20), nullable=False, server_default='postgresql'),
    )


def downgrade() -> None:
    """Remove db_type column from databaseconnections."""
    with op.batch_alter_table('databaseconnections') as batch_op:
        batch_op.drop_column('db_type')