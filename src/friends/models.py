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


class BlockedUser(Base):
    """
    Represents a blocking relationship between two users.
    When User A blocks User B, only one record is created.
    """
    __tablename__ = "blocked_users"

    id = Column(Integer, primary_key=True, index=True)
    blocker_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    blocked_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = Column(String, nullable=True)  # Optional reason for blocking
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    blocker = relationship("User", foreign_keys=[blocker_id], back_populates="blocked_users")
    blocked = relationship("User", foreign_keys=[blocked_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint('blocker_id', 'blocked_id', name='unique_blocked_user'),
        Index('idx_blocked_user_blocker_id', 'blocker_id'),
        Index('idx_blocked_user_blocked_id', 'blocked_id'),
    )


class UserReport(Base):
    """
    Represents a report against a user for inappropriate behavior.
    Multiple reports can exist for the same user.
    """
    __tablename__ = "user_reports"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reported_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=False)  # harassment, spam, inappropriate_content, fake_account, other
    description = Column(String, nullable=True)  # Additional details
    status = Column(String, nullable=False, default="pending")  # pending, reviewed, resolved, dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="submitted_reports")
    reported = relationship("User", foreign_keys=[reported_id], back_populates="received_reports")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    # Constraints
    __table_args__ = (
        Index('idx_user_report_reporter_id', 'reporter_id'),
        Index('idx_user_report_reported_id', 'reported_id'),
        Index('idx_user_report_status', 'status'),
        Index('idx_user_report_category', 'category'),
        Index('idx_user_report_created_at', 'created_at'),
    )
