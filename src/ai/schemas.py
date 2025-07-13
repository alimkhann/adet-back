from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class DifficultyResponse(BaseModel):
    """Response from Difficulty Calibrator Agent"""
    difficulty: float = Field(..., ge=0.5, le=3.0, description="Difficulty level from 0.5 to 3.0")
    reasoning: str = Field(..., description="Explanation of why this difficulty level was chosen")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the difficulty assessment")

class GeneratedTask(BaseModel):
    """Generated task structure"""
    task_description: str = Field(..., description="The generated task description")
    difficulty_level: float = Field(..., description="Final difficulty level (0.5-3.0)")
    estimated_duration: int = Field(..., description="Estimated time in minutes")
    success_criteria: str = Field(..., description="How to know the task is complete")
    celebration_message: str = Field(..., description="Message to celebrate completion")
    easier_alternative: Optional[str] = Field(None, description="Alternative if task feels too hard")
    harder_alternative: Optional[str] = Field(None, description="Alternative if task feels too easy")
    proof_requirements: str = Field(..., description="What proof is required")

class MotivationalResponse(BaseModel):
    """Response from Motivational Coach Agent"""
    message: str = Field(..., description="Motivational message")
    tone: Literal["celebratory", "encouraging", "supportive", "curious"] = Field(..., description="Tone of the message")
    action_suggestion: Optional[str] = Field(None, description="Suggested next action")
    identity_reinforcement: Optional[str] = Field(None, description="Identity-based encouragement")

class ContextAnalysis(BaseModel):
    """Response from Context Analyzer Agent"""
    time_context: str = Field(..., description="Analysis of time-based factors")
    environmental_factors: List[str] = Field(default_factory=list, description="Environmental considerations")
    energy_level_suggestion: Optional[str] = Field(None, description="Suggested energy level for task")
    optimal_timing: Optional[str] = Field(None, description="Optimal time to perform task")

class TaskGenerationContext(BaseModel):
    """Input context for task generation"""
    habit_name: str
    habit_description: str
    base_difficulty: Literal["easy", "medium", "hard"]
    motivation_level: Literal["low", "medium", "high"]
    ability_level: Literal["hard", "medium", "easy"]
    proof_style: Literal["photo", "video", "audio", "text"]
    user_language: str = "en"
    recent_performance: List[dict] = Field(default_factory=list)
    current_time: datetime
    day_of_week: str
    weather: Optional[str] = None
    user_timezone: str = "UTC"

class TaskValidationResult(BaseModel):
    """Result of task proof validation"""
    is_valid: bool = Field(..., description="Whether the proof validates the task")
    is_nsfw: bool = Field(default=False, description="Whether the proof is NSFW/inappropriate")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in validation")
    feedback: str = Field(..., description="Feedback on the proof")
    reasoning: Optional[str] = Field(None, description="Short explanation for the validation result")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")

class AIAgentResponse(BaseModel):
    """Generic response wrapper for AI agents"""
    success: bool = Field(..., description="Whether the operation was successful")
    data: Optional[dict] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

