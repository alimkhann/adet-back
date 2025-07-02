"""Add blocking and reporting models only

Revision ID: 533fdc0917d3
Revises: 5400f34e1c5d
Create Date: 2025-07-02 17:52:12.969329

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '533fdc0917d3'
down_revision = '5400f34e1c5d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create blocked_users table
    op.create_table('blocked_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('blocker_id', sa.Integer(), nullable=False),
        sa.Column('blocked_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['blocked_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['blocker_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('blocker_id', 'blocked_id', name='unique_blocked_user')
    )
    op.create_index('idx_blocked_user_blocker_id', 'blocked_users', ['blocker_id'], unique=False)
    op.create_index('idx_blocked_user_blocked_id', 'blocked_users', ['blocked_id'], unique=False)

    # Create user_reports table
    op.create_table('user_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reporter_id', sa.Integer(), nullable=False),
        sa.Column('reported_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['reported_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_report_reporter_id', 'user_reports', ['reporter_id'], unique=False)
    op.create_index('idx_user_report_reported_id', 'user_reports', ['reported_id'], unique=False)
    op.create_index('idx_user_report_status', 'user_reports', ['status'], unique=False)
    op.create_index('idx_user_report_category', 'user_reports', ['category'], unique=False)
    op.create_index('idx_user_report_created_at', 'user_reports', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop user_reports table
    op.drop_index('idx_user_report_created_at', table_name='user_reports')
    op.drop_index('idx_user_report_category', table_name='user_reports')
    op.drop_index('idx_user_report_status', table_name='user_reports')
    op.drop_index('idx_user_report_reported_id', table_name='user_reports')
    op.drop_index('idx_user_report_reporter_id', table_name='user_reports')
    op.drop_table('user_reports')

    # Drop blocked_users table
    op.drop_index('idx_blocked_user_blocked_id', table_name='blocked_users')
    op.drop_index('idx_blocked_user_blocker_id', table_name='blocked_users')
    op.drop_table('blocked_users')