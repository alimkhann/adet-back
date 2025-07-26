"""Add device_tokens table

Revision ID: cf3d5b0ff921
Revises: a1b2c3d4e5f6
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'cf3d5b0ff921'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if device_tokens table already exists
    inspector = inspect(op.get_bind())
    if 'device_tokens' in inspector.get_table_names():
        print("device_tokens table already exists, skipping creation")
        return

    # Create device_tokens table
    op.create_table('device_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('device_token', sa.String(length=256), nullable=False),
        sa.Column('platform', sa.String(length=16), nullable=False),
        sa.Column('app_version', sa.String(length=32), nullable=True),
        sa.Column('system_version', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_device_tokens_id'), 'device_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_device_tokens_device_token'), 'device_tokens', ['device_token'], unique=True)

    # Create unique constraint for user_id and device_token combination
    op.create_unique_constraint('uq_user_device_token', 'device_tokens', ['user_id', 'device_token'])


def downgrade() -> None:
    # Check if device_tokens table exists before dropping
    inspector = inspect(op.get_bind())
    if 'device_tokens' not in inspector.get_table_names():
        print("device_tokens table does not exist, skipping drop")
        return

    # Drop indexes and constraints
    op.drop_constraint('uq_user_device_token', 'device_tokens', type_='unique')
    op.drop_index(op.f('ix_device_tokens_device_token'), table_name='device_tokens')
    op.drop_index(op.f('ix_device_tokens_id'), table_name='device_tokens')

    # Drop table
    op.drop_table('device_tokens')