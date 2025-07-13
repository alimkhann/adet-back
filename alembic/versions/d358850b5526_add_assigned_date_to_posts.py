"""add assigned_date to posts

Revision ID: d358850b5526
Revises: 9dc0fb0958d8
Create Date: 2025-07-13 03:08:15.547543

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd358850b5526'
down_revision = '9dc0fb0958d8'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Add the column as nullable
    op.add_column('posts', sa.Column('assigned_date', sa.Date(), nullable=True))
    # 2. Populate for existing rows (fallback to created_at date)
    op.execute("UPDATE posts SET assigned_date = DATE(created_at) WHERE assigned_date IS NULL")
    # 3. Make the column non-nullable
    op.alter_column('posts', 'assigned_date', nullable=False)
    # 4. Add the unique constraint
    op.create_unique_constraint('unique_user_habit_day_post', 'posts', ['user_id', 'habit_id', 'assigned_date'])

def downgrade() -> None:
    op.drop_constraint('unique_user_habit_day_post', 'posts', type_='unique')
    op.drop_column('posts', 'assigned_date')