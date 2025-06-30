from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint, Index, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from ..database import Base


class ProofType(PyEnum):
    """Proof type enumeration"""
    IMAGE = "image"
    VIDEO = "video"
    TEXT = "text"
    AUDIO = "audio"


class PostPrivacy(PyEnum):
    """Post privacy levels"""
    PRIVATE = "private"
    FRIENDS = "friends"
    CLOSE_FRIENDS = "close_friends"


class Post(Base):
    """
    Represents a user's post with proof and social features.
    """
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="SET NULL"), nullable=True)

    # Media content
    proof_urls = Column(JSON, nullable=False)  # Array of media URLs
    proof_type = Column(String, nullable=False)  # ProofType enum value
    description = Column(Text, nullable=True)

    # Privacy and visibility
    privacy = Column(String, nullable=False, default="friends")  # PostPrivacy enum value

    # Analytics
    views_count = Column(Integer, nullable=False, default=0)
    likes_count = Column(Integer, nullable=False, default=0)
    comments_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    habit = relationship("Habit", foreign_keys=[habit_id])
    comments = relationship("PostComment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")
    views = relationship("PostView", back_populates="post", cascade="all, delete-orphan")

    # Constraints and Indexes
    __table_args__ = (
        Index('idx_post_user_created', 'user_id', 'created_at'),
        Index('idx_post_privacy', 'privacy'),
        Index('idx_post_created_at', 'created_at'),
        Index('idx_post_habit_id', 'habit_id'),
    )


class PostComment(Base):
    """
    Represents a comment on a post with threading support.
    """
    __tablename__ = "post_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_comment_id = Column(Integer, ForeignKey("post_comments.id", ondelete="CASCADE"), nullable=True)

    content = Column(Text, nullable=False)
    likes_count = Column(Integer, nullable=False, default=0)
    replies_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    post = relationship("Post", back_populates="comments")
    user = relationship("User", foreign_keys=[user_id])
    parent_comment = relationship("PostComment", remote_side=[id], back_populates="replies")
    replies = relationship("PostComment", back_populates="parent_comment", cascade="all, delete-orphan")
    likes = relationship("PostLike", back_populates="comment", cascade="all, delete-orphan")

    # Constraints and Indexes
    __table_args__ = (
        Index('idx_comment_post_created', 'post_id', 'created_at'),
        Index('idx_comment_user_id', 'user_id'),
        Index('idx_comment_parent_id', 'parent_comment_id'),
    )


class PostLike(Base):
    """
    Represents a like on a post or comment.
    """
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    comment_id = Column(Integer, ForeignKey("post_comments.id", ondelete="CASCADE"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    post = relationship("Post", back_populates="likes")
    comment = relationship("PostComment", back_populates="likes")

    # Constraints and Indexes
    __table_args__ = (
        # User can only like a post once
        UniqueConstraint('user_id', 'post_id', name='unique_post_like'),
        # User can only like a comment once
        UniqueConstraint('user_id', 'comment_id', name='unique_comment_like'),
        Index('idx_like_user_id', 'user_id'),
        Index('idx_like_post_id', 'post_id'),
        Index('idx_like_comment_id', 'comment_id'),
        Index('idx_like_created_at', 'created_at'),
    )


class PostView(Base):
    """
    Represents a view/impression on a post for analytics.
    """
    __tablename__ = "post_views"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    # Analytics data
    view_duration = Column(Integer, nullable=True)  # Seconds spent viewing
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    post = relationship("Post", back_populates="views")
    user = relationship("User", foreign_keys=[user_id])

    # Constraints and Indexes
    __table_args__ = (
        # One view per user per post (can be updated)
        UniqueConstraint('user_id', 'post_id', name='unique_post_view'),
        Index('idx_view_post_id', 'post_id'),
        Index('idx_view_user_id', 'user_id'),
        Index('idx_view_viewed_at', 'viewed_at'),
    )


class PostReport(Base):
    """
    Represents a report on a post for content moderation.
    """
    __tablename__ = "post_reports"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    reason = Column(String, nullable=False)  # spam, inappropriate, etc.
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, reviewed, dismissed

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    post = relationship("Post", foreign_keys=[post_id])
    reporter = relationship("User", foreign_keys=[reporter_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    # Constraints and Indexes
    __table_args__ = (
        # User can only report a post once
        UniqueConstraint('reporter_id', 'post_id', name='unique_post_report'),
        Index('idx_report_post_id', 'post_id'),
        Index('idx_report_status', 'status'),
        Index('idx_report_created_at', 'created_at'),
    )