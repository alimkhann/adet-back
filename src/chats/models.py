from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base


class Conversation(Base):
    """
    Represents a conversation between friends.
    Each conversation contains multiple messages.
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    participant_1_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    participant_2_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Track last activity for sorting conversations
    last_message_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    participant_1 = relationship("User", foreign_keys=[participant_1_id])
    participant_2 = relationship("User", foreign_keys=[participant_2_id])
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    # Constraints and indexes
    __table_args__ = (
        Index('idx_conversation_participants', 'participant_1_id', 'participant_2_id'),
        Index('idx_conversation_last_message', 'last_message_at'),
    )


class Message(Base):
    """
    Represents an individual message within a conversation.
    Supports real-time status tracking.
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String, nullable=False, default="text")  # text, system

    # Message status for real-time features
    status = Column(String, nullable=False, default="sent")  # sent, delivered, read

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])

    # Constraints and indexes
    __table_args__ = (
        Index('idx_message_conversation_created', 'conversation_id', 'created_at'),
        Index('idx_message_sender', 'sender_id'),
        Index('idx_message_status', 'status'),
    )


class ConversationParticipant(Base):
    """
    Tracks conversation participants and their real-time status.
    Used for presence tracking and unread counts.
    """
    __tablename__ = "conversation_participants"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Real-time status tracking
    is_online = Column(Boolean, default=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    last_read_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)

    # Unread count for this participant
    unread_count = Column(Integer, default=0)

    # Timestamps
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    conversation = relationship("Conversation")
    user = relationship("User")
    last_read_message = relationship("Message", foreign_keys=[last_read_message_id])

    # Constraints and indexes
    __table_args__ = (
        Index('idx_participant_conversation_user', 'conversation_id', 'user_id'),
        Index('idx_participant_online', 'is_online'),
        Index('idx_participant_unread', 'unread_count'),
    )