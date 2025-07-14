"""Add proof_content column to posts

Revision ID: add_proof_content_to_posts
Revises: <previous_revision_id>
Create Date: 2024-07-14 05:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_proof_content_to_posts'
down_revision = '9dc0fb0958d8'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('posts', sa.Column('proof_content', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('posts', 'proof_content')