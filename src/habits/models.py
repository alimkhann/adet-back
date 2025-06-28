from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from src.database import Base

class MotivationLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class AbilityLevel(str, Enum):
    hard = "hard"
    medium = "medium"
    easy = "easy"

class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    frequency = Column(String, nullable=False)
    validation_time = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    proof_style = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    streak = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships with cascade delete
    user = relationship("User", back_populates="habits")
    motivation_entries = relationship("MotivationEntry", back_populates="habit", cascade="all, delete-orphan")
    ability_entries = relationship("AbilityEntry", back_populates="habit", cascade="all, delete-orphan")
    task_entries = relationship("TaskEntry", back_populates="habit", cascade="all, delete-orphan")

class MotivationEntry(Base):
    __tablename__ = "motivation_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)  # clerk_id
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    level = Column(String, nullable=False)  # MotivationLevel enum
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    habit = relationship("Habit", back_populates="motivation_entries")

class AbilityEntry(Base):
    __tablename__ = "ability_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)  # clerk_id
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    level = Column(String, nullable=False)  # AbilityLevel enum
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    habit = relationship("Habit", back_populates="ability_entries")

# --- Task Completion Models ---

class TaskStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    missed = "missed"

class ProofType(str, Enum):
    photo = "photo"
    video = "video"
    audio = "audio"
    text = "text"

class TaskEntry(Base):
    """AI-generated task entries"""
    __tablename__ = "task_entries"

    id = Column(Integer, primary_key=True, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Task details
    task_description = Column(Text, nullable=False)
    difficulty_level = Column(Float, nullable=False)  # 0.5-3.0 scale
    estimated_duration = Column(Integer, nullable=False)  # minutes
    success_criteria = Column(Text, nullable=False)
    celebration_message = Column(Text, nullable=False)
    easier_alternative = Column(Text)
    harder_alternative = Column(Text)
    proof_requirements = Column(Text, nullable=False)

    # Task state
    status = Column(String, default=TaskStatus.pending)  # TaskStatus enum
    assigned_date = Column(Date, nullable=False)
    due_date = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)

    # Proof submission
    proof_type = Column(String)  # ProofType enum
    proof_content = Column(Text)  # URL or text content
    proof_validation_result = Column(Boolean)  # AI validation result
    proof_validation_confidence = Column(Float)  # AI confidence score
    proof_feedback = Column(Text)  # AI feedback on proof

    # AI metadata
    ai_generation_metadata = Column(Text)  # JSON string of AI generation details
    calibration_metadata = Column(Text)  # JSON string of difficulty calibration

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    habit = relationship("Habit", back_populates="task_entries")
    user = relationship("User", back_populates="task_entries")

class TaskValidation(Base):
    """AI validation results for task proofs"""
    __tablename__ = "task_validations"

    id = Column(Integer, primary_key=True, index=True)
    task_entry_id = Column(Integer, ForeignKey("task_entries.id"), nullable=False)

    # Validation details
    is_valid = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0-1.0
    feedback = Column(Text, nullable=False)
    suggestions = Column(Text)  # JSON array of suggestions

    # AI metadata
    validation_model = Column(String, nullable=False)  # "vertex_ai_gemini_1_5_pro"
    validation_prompt = Column(Text)  # Prompt used for validation
    validation_response = Column(Text)  # Raw AI response

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    task_entry = relationship("TaskEntry")
