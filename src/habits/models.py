from sqlalchemy import Column, Integer, String, ForeignKey, Enum as PgEnum, Date, UUID
from sqlalchemy.orm import relationship
from src.database import Base
import enum

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

# --- Motivation/Ability Models ---
class MotivationLevel(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class AbilityLevel(enum.Enum):
    hard = "hard"
    medium = "medium"
    easy = "easy"

class MotivationEntry(Base):
    __tablename__ = "motivation_entries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.clerk_id"), nullable=False)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=False)
    date = Column(Date, nullable=False)
    level = Column(PgEnum(MotivationLevel), nullable=False)

class AbilityEntry(Base):
    __tablename__ = "ability_entries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.clerk_id"), nullable=False)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=False)
    date = Column(Date, nullable=False)
    level = Column(PgEnum(AbilityLevel), nullable=False)
