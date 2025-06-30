from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base


class Friendship(Base):
    """
    Represents a friendship relationship between two users.
    Each friendship creates two records (bidirectional).
    """
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="active")  # active, blocked
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="friendships")
    friend = relationship("User", foreign_keys=[friend_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),
        Index('idx_friendship_user_id', 'user_id'),
        Index('idx_friendship_friend_id', 'friend_id'),
        Index('idx_friendship_status', 'status'),
    )


class FriendRequest(Base):
    """
    Represents a friend request between two users.
    Only one record exists per request.
    """
    __tablename__ = "friend_requests"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending, accepted, declined, cancelled
    message = Column(String, nullable=True)  # Optional message with request
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Auto-expire old requests

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_friend_requests")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_friend_requests")

    # Constraints
    __table_args__ = (
        UniqueConstraint('sender_id', 'receiver_id', name='unique_friend_request'),
        Index('idx_friend_request_sender_id', 'sender_id'),
        Index('idx_friend_request_receiver_id', 'receiver_id'),
        Index('idx_friend_request_status', 'status'),
        Index('idx_friend_request_created_at', 'created_at'),
    )


class CloseFriend(Base):
    """
    Represents a one-way close friend relationship.
    User A can add User B as a close friend without B's consent.
    """
    __tablename__ = "close_friends"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    close_friend_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="close_friends")
    close_friend = relationship("User", foreign_keys=[close_friend_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'close_friend_id', name='unique_close_friend'),
        Index('idx_close_friend_user_id', 'user_id'),
        Index('idx_close_friend_close_friend_id', 'close_friend_id'),
    )