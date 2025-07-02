"""update_message_deleted_format

Revision ID: f56aca9968ac
Revises: 9d009ee003f2
Create Date: 2024-12-19 16:57:37.772425

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f56aca9968ac'
down_revision = '9d009ee003f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update existing messages to use new format without brackets
    op.execute("""
        UPDATE messages
        SET content = 'Message deleted'
        WHERE content = '[Message deleted]'
    """)


def downgrade() -> None:
    # Revert back to old format with brackets
    op.execute("""
        UPDATE messages
        SET content = '[Message deleted]'
        WHERE content = 'Message deleted'
    """)