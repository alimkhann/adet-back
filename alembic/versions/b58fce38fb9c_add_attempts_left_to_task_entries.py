"""add attempts_left to task_entries

Revision ID: b58fce38fb9c
Revises: 68f129bc93a0
Create Date: 2025-07-08 22:12:27.792632

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b58fce38fb9c'
down_revision = '68f129bc93a0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Add as nullable with server default
    op.add_column('task_entries', sa.Column('attempts_left', sa.Integer(), server_default='3', nullable=True))
    # Step 2: Set NOT NULL and remove server default
    op.alter_column('task_entries', 'attempts_left', nullable=False, server_default=None)


def downgrade() -> None:
    op.drop_column('task_entries', 'attempts_left')