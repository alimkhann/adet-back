"""add_reply_support

Revision ID: add_reply_support
Revises: add_chat_tables_manual
Create Date: 2025-06-30 20:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_reply_support'
down_revision = 'add_chat_tables_manual'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add replied_to_message_id column to messages table
    op.add_column('messages', sa.Column('replied_to_message_id', sa.Integer(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_messages_replied_to_message_id',
        'messages',
        'messages',
        ['replied_to_message_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add index for better performance
    op.create_index('idx_message_replied_to', 'messages', ['replied_to_message_id'])


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_message_replied_to', table_name='messages')

    # Remove foreign key constraint
    op.drop_constraint('fk_messages_replied_to_message_id', 'messages', type_='foreignkey')

    # Remove column
    op.drop_column('messages', 'replied_to_message_id')