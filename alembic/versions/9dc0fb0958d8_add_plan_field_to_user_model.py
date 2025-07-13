"""add plan field to user model

Revision ID: 9dc0fb0958d8
Revises: 13cc710e186e
Create Date: 2025-07-11 00:59:31.389278

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9dc0fb0958d8'
down_revision = '13cc710e186e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('plan', sa.String(), nullable=False, server_default='free'))

def downgrade() -> None:
    op.drop_column('users', 'plan')