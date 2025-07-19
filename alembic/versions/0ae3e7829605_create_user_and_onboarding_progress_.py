"""Create user and onboarding_progress tables

Revision ID: 0ae3e7829605
Revises:
Create Date: 2025-06-13 04:58:59.563785

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0ae3e7829605'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('clerk_id', sa.String(length=64), nullable=False, unique=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('username', sa.String(length=64), nullable=False, unique=True),
        sa.Column('first_name', sa.String(length=64), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('profile_image_url', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('role', sa.Integer(), nullable=False, server_default=sa.text('2')),
        sa.Column('plan', sa.String(length=32), nullable=False, server_default=sa.text("'free'")),
    )
    op.create_table(
        'onboarding_progress',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('step', sa.String(length=64), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('onboarding_progress')
    op.drop_table('users')