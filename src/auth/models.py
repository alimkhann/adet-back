from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    clerk_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=False, index=True)
    username = Column(String, nullable=True, unique=True, index=True)  # Made nullable since we'll get it from Clerk
    name = Column(String, nullable=True)  # User's display name
    bio = Column(String, nullable=True)  # User's bio
    profile_image_url = Column(String, nullable=True)  # User's profile image URL
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship with onboarding answers
    onboarding_answer = relationship(
        "OnboardingAnswer",
        back_populates="user",
        uselist=False,
        passive_deletes=True
    )

    # Relationship with habits
    habits = relationship("Habit", back_populates="user", cascade="all, delete-orphan")

    # Relationship with task entries
    task_entries = relationship("TaskEntry", back_populates="user", cascade="all, delete-orphan")

    # Relationship with friendships (as user)
    friendships = relationship("Friendship", foreign_keys="Friendship.user_id", back_populates="user", cascade="all, delete-orphan")

    # Relationship with sent friend requests
    sent_friend_requests = relationship("FriendRequest", foreign_keys="FriendRequest.sender_id", back_populates="sender", cascade="all, delete-orphan")

    # Relationship with received friend requests
    received_friend_requests = relationship("FriendRequest", foreign_keys="FriendRequest.receiver_id", back_populates="receiver", cascade="all, delete-orphan")

    # Relationship with close friends (as user)
    close_friends = relationship("CloseFriend", foreign_keys="CloseFriend.user_id", back_populates="user", cascade="all, delete-orphan")
