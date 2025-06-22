from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UserSchema(BaseModel):
    id: int
    clerk_id: str
    email: str
    username: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UsernameUpdateSchema(BaseModel):
    username: str