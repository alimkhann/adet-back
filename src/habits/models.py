from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    frequency = Column(String, nullable=False)
    validation_time = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    proof_style = Column(String, nullable=False)
    streak = Column(Integer, default=0)

    owner = relationship("User", back_populates="habits")