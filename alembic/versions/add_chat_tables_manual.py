"""add_chat_tables_manual

Revision ID: add_chat_tables_manual
Revises: faa4f448839c
Create Date: 2025-06-30 22:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_chat_tables_manual'
down_revision = 'faa4f448839c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('participant_1_id', sa.Integer(), nullable=False),
        sa.Column('participant_2_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['participant_1_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['participant_2_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_conversation_participants', 'conversations', ['participant_1_id', 'participant_2_id'])
    op.create_index('idx_conversation_last_message', 'conversations', ['last_message_at'])
    op.create_index('ix_conversations_id', 'conversations', ['id'])

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(), nullable=False, server_default='text'),
        sa.Column('status', sa.String(), nullable=False, server_default='sent'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_message_conversation_created', 'messages', ['conversation_id', 'created_at'])
    op.create_index('idx_message_sender', 'messages', ['sender_id'])
    op.create_index('idx_message_status', 'messages', ['status'])
    op.create_index('ix_messages_id', 'messages', ['id'])

    # Create conversation_participants table
    op.create_table(
        'conversation_participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_online', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_read_message_id', sa.Integer(), nullable=True),
        sa.Column('unread_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['last_read_message_id'], ['messages.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_participant_conversation_user', 'conversation_participants', ['conversation_id', 'user_id'])
    op.create_index('idx_participant_online', 'conversation_participants', ['is_online'])
    op.create_index('idx_participant_unread', 'conversation_participants', ['unread_count'])
    op.create_index('ix_conversation_participants_id', 'conversation_participants', ['id'])


def downgrade() -> None:
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('conversation_participants')
    op.drop_table('messages')
    op.drop_table('conversations')