"""add support system tables

Revision ID: support_system_001
Revises: 533fdc0917d3
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'support_system_001'
down_revision = '533fdc0917d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create support_requests table
    op.create_table('support_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('priority', sa.String(length=20), nullable=True),
        sa.Column('system_info', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assigned_to', sa.String(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.clerk_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.clerk_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_support_requests_id'), 'support_requests', ['id'], unique=False)

    # Create bug_reports table
    op.create_table('bug_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('steps_to_reproduce', sa.Text(), nullable=True),
        sa.Column('expected_behavior', sa.Text(), nullable=True),
        sa.Column('actual_behavior', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('system_info', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('include_screenshots', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assigned_to', sa.String(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('github_issue_url', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.clerk_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.clerk_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bug_reports_id'), 'bug_reports', ['id'], unique=False)

    # Create support_responses table
    op.create_table('support_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('support_request_id', sa.Integer(), nullable=True),
        sa.Column('bug_report_id', sa.Integer(), nullable=True),
        sa.Column('responder_id', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['bug_report_id'], ['bug_reports.id'], ),
        sa.ForeignKeyConstraint(['responder_id'], ['users.clerk_id'], ),
        sa.ForeignKeyConstraint(['support_request_id'], ['support_requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_support_responses_id'), 'support_responses', ['id'], unique=False)


def downgrade() -> None:
    # Drop support_responses table
    op.drop_index(op.f('ix_support_responses_id'), table_name='support_responses')
    op.drop_table('support_responses')

    # Drop bug_reports table
    op.drop_index(op.f('ix_bug_reports_id'), table_name='bug_reports')
    op.drop_table('bug_reports')

    # Drop support_requests table
    op.drop_index(op.f('ix_support_requests_id'), table_name='support_requests')
    op.drop_table('support_requests')

