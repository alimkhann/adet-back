from pydantic import BaseModel, Field
from typing import Optional
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
