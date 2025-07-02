"""Merge multiple heads

Revision ID: 46d2fa07c648
Revises: 9a2bf8a6f986, f56aca9968ac
Create Date: 2025-07-02 17:50:26.888131

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '46d2fa07c648'
down_revision = ('9a2bf8a6f986', 'f56aca9968ac')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass