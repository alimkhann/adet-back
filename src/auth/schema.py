from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UserSchema(BaseModel):
    id: int
    clerk_id: str
    email: str
    username: Optional[str] = None
    name: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    plan: str
    streak_freezers: int

    class Config:
        from_attributes = True


class UsernameUpdateSchema(BaseModel):
    username: str
class ProfileImageUpdateSchema(BaseModel):
    profile_image_url: str


class ProfileUpdateSchema(BaseModel):
    """Schema for updating user profile fields (name, username, bio)."""
    name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None


