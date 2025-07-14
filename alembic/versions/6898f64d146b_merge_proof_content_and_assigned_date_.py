"""Merge proof_content and assigned_date heads

Revision ID: 6898f64d146b
Revises: add_proof_content_to_posts, d358850b5526
Create Date: 2025-07-14 11:03:10.420198

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6898f64d146b'
down_revision = ('add_proof_content_to_posts', 'd358850b5526')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass