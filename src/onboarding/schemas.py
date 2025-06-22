from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class OnboardingProgressCreate(BaseModel):
    user_id: int
    current_step: str = "start"
    is_completed: bool = False
    data: Optional[Dict[str, Any]] = None

class OnboardingProgressUpdate(BaseModel):
    current_step: Optional[str] = None
    is_completed: Optional[bool] = None
    data: Optional[Dict[str, Any]] = None

class OnboardingProgressResponse(BaseModel):
    id: int
    user_id: int
    current_step: str
    is_completed: bool
    data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}