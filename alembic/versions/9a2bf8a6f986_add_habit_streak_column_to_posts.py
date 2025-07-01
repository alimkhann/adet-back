"""Add habit_streak column to posts

Revision ID: 9a2bf8a6f986
Revises: 62495114e156
Create Date: 2025-07-01 03:40:31.656079

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a2bf8a6f986'
down_revision = '62495114e156'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add habit_streak column to posts table
    op.add_column('posts', sa.Column('habit_streak', sa.Integer(), nullable=True))

    # Add index for habit_streak column for better performance
    op.create_index('idx_post_habit_streak', 'posts', ['habit_streak'])


def downgrade() -> None:
    # Drop index first
    op.drop_index('idx_post_habit_streak', table_name='posts')

    # Drop the habit_streak column
    op.drop_column('posts', 'habit_streak')