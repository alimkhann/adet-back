from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    clerk_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=False, index=True)
    username = Column(String, nullable=True)  # Made nullable since we'll get it from Clerk
    profile_image_url = Column(String, nullable=True)  # URL to profile image
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
    habits = relationship("Habit", back_populates="owner", cascade="all, delete-orphan")
