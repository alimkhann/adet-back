from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date
from .models import MotivationLevel, AbilityLevel

class HabitBase(BaseModel):
    name: str
    description: Optional[str] = None
    frequency: str
    validation_time: str
    difficulty: str
    proof_style: str

class HabitCreate(HabitBase):
    pass

class HabitUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[str] = None
    validation_time: Optional[str] = None
    difficulty: Optional[str] = None
    proof_style: Optional[str] = None

class Habit(HabitBase):
    id: int
    user_id: int
    streak: int

    class Config:
        from_attributes = True

# --- AI Task Generation Schemas ---

class AITaskRequest(BaseModel):
    """Request schema for AI task generation"""
    base_difficulty: Literal["easy", "medium", "hard"] = Field(..., description="User's preferred difficulty level")
    motivation_level: Literal["low", "medium", "high"] = Field(..., description="Current motivation level")
    ability_level: Literal["hard", "medium", "easy"] = Field(..., description="Current ability level")
    proof_style: Literal["photo", "video", "audio", "text"] = Field(..., description="Preferred proof style")
    user_language: Optional[str] = Field("en", description="User's preferred language")
    user_timezone: Optional[str] = Field("UTC", description="User's timezone")

class QuickTaskRequest(BaseModel):
    """Request schema for quick task generation (fallback)"""
    base_difficulty: Literal["easy", "medium", "hard"] = Field(..., description="User's preferred difficulty level")
    proof_style: Literal["photo", "video", "audio", "text"] = Field(..., description="Preferred proof style")
    user_language: Optional[str] = Field("en", description="User's preferred language")

class GeneratedTaskResponse(BaseModel):
    """Response schema for generated task"""
    task_description: str = Field(..., description="The generated task description")
    difficulty_level: float = Field(..., description="Final difficulty level (0.5-3.0)")
    estimated_duration: int = Field(..., description="Estimated time in minutes")
    success_criteria: str = Field(..., description="How to know the task is complete")
    celebration_message: str = Field(..., description="Message to celebrate completion")
    easier_alternative: Optional[str] = Field(None, description="Alternative if task feels too hard")
    harder_alternative: Optional[str] = Field(None, description="Alternative if task feels too easy")
    anchor_suggestion: Optional[str] = Field(None, description="Suggested anchor habit")
    proof_requirements: str = Field(..., description="What proof is required")
    calibration_metadata: Optional[dict] = Field(None, description="Difficulty calibration metadata")

class PerformanceAnalysisResponse(BaseModel):
    """Response schema for performance analysis"""
    total_tasks: int = Field(..., description="Total number of tasks")
    completed_tasks: int = Field(..., description="Number of completed tasks")
    success_rate: float = Field(..., description="Success rate as percentage")
    current_streak: int = Field(..., description="Current streak count")
    difficulty_insights: list = Field(default_factory=list, description="AI-generated difficulty insights")

class ImprovementSuggestionsResponse(BaseModel):
    """Response schema for improvement suggestions"""
    performance_summary: dict = Field(..., description="Performance analysis summary")
    improvement_suggestions: str = Field(..., description="AI-generated improvement suggestions")

# --- Motivation/Ability Schemas ---

class MotivationEntryBase(BaseModel):
    habit_id: int
    date: date
    level: MotivationLevel

class MotivationEntryCreate(MotivationEntryBase):
    pass

class MotivationEntryRead(MotivationEntryBase):
    id: int
    user_id: str
    class Config:
        from_attributes = True

class AbilityEntryBase(BaseModel):
    habit_id: int
    date: date
    level: AbilityLevel

class AbilityEntryCreate(AbilityEntryBase):
    pass

class AbilityEntryRead(AbilityEntryBase):
    id: int
    user_id: str
    class Config:
        from_attributes = True
