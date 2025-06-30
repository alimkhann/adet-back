"""add_close_friends_table_only

Revision ID: 363101ac576a
Revises: 6d52704a9b2f
Create Date: 2025-07-01 02:43:08.026468

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '363101ac576a'
down_revision = '6d52704a9b2f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create close_friends table
    op.create_table('close_friends',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('close_friend_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'close_friend_id', name='unique_close_friend'),
    )

    # Create indexes
    op.create_index('idx_close_friend_user_id', 'close_friends', ['user_id'])
    op.create_index('idx_close_friend_close_friend_id', 'close_friends', ['close_friend_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_close_friend_close_friend_id', table_name='close_friends')
    op.drop_index('idx_close_friend_user_id', table_name='close_friends')

    # Drop table
    op.drop_table('close_friends')