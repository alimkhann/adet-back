from pydantic import BaseModel
from typing import Optional
from .user import UserResponse

class UserDataBatch(BaseModel):
    """Batch response containing user data and related counts"""
    user: UserResponse
    postCount: int
    friendCount: int
    pendingFriendRequests: int

    class Config:
        from_attributes = True