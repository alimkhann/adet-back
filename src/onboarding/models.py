from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..database import Base

class OnboardingProgress(Base):
    __tablename__ = "onboarding_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    current_step = Column(String, default="start")
    is_completed = Column(Boolean, default=False)
    data = Column(String, nullable=True) # To store JSON string of answers/preferences
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="onboarding_progress")