"""add country and status to waitlist_emails

Revision ID: 68f129bc93a0
Revises: 4b54aafabbc8
Create Date: 2025-07-06 21:53:15.686367

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '68f129bc93a0'
down_revision = '4b54aafabbc8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'country' and 'status' columns to waitlist_emails
    op.add_column('waitlist_emails', sa.Column('country', sa.String(length=64), nullable=True))
    op.add_column('waitlist_emails', sa.Column('status', sa.String(length=32), nullable=False, server_default='success'))


def downgrade() -> None:
    # Remove 'country' and 'status' columns from waitlist_emails
    op.drop_column('waitlist_emails', 'country')
    op.drop_column('waitlist_emails', 'status')