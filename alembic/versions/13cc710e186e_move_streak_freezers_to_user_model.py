"""move streak_freezers to user model

Revision ID: 13cc710e186e
Revises: b58fce38fb9c
Create Date: 2025-07-08 22:39:51.528395

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '13cc710e186e'
down_revision = 'b58fce38fb9c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add streak_freezers to users (default 0, not null)
    op.add_column('users', sa.Column('streak_freezers', sa.Integer(), nullable=False, server_default='0'))
    # Optionally, remove from habits if it exists:
    # with op.batch_alter_table('habits') as batch_op:
    #     batch_op.drop_column('streak_freezers')


def downgrade() -> None:
    # Remove streak_freezers from users
    op.drop_column('users', 'streak_freezers')
    # Optionally, add back to habits if you dropped it above:
    # with op.batch_alter_table('habits') as batch_op:
    #     batch_op.add_column(sa.Column('streak_freezers', sa.Integer(), nullable=True, server_default='0'))