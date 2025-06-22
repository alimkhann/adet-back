from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class OnboardingAnswer(Base):
    __tablename__ = "onboarding_answers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    habit_name = Column(String, nullable=False)
    habit_description = Column(String, nullable=True)
    frequency = Column(String, nullable=False)
    validation_time = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    proof_style = Column(String, nullable=False)

    user = relationship("User", back_populates="onboarding_answer", passive_deletes=True)