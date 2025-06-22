"""Reset users table to empty state

Revision ID: e95569ac6b84
Revises: a3c21557cf1d
Create Date: 2025-06-21 20:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e95569ac6b84'
down_revision = 'a3c21557cf1d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration documents the state where the users table has been cleared
    # No schema changes are made - this is just for version tracking
    # The users table was manually truncated to remove all data
    # This ensures a clean slate for future development
    pass


def downgrade() -> None:
    # No downgrade action needed since this is just a state marker
    pass