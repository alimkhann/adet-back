from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# Base schemas for users in friends context
class UserBasic(BaseModel):
    """Basic user information for friends lists"""
    id: int
    username: Optional[str] = None
    name: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True


# Friendship schemas
class FriendshipBase(BaseModel):
    """Base friendship schema"""
    status: str = "active"


class FriendshipCreate(FriendshipBase):
    """Schema for creating friendships"""
    pass


class FriendshipRead(FriendshipBase):
    """Schema for reading friendships"""
    id: int
    user_id: int
    friend_id: int
    friend: UserBasic
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Friend Request schemas
class FriendRequestBase(BaseModel):
    """Base friend request schema"""
    message: Optional[str] = None


class FriendRequestCreate(FriendRequestBase):
    """Schema for creating friend requests"""
    receiver_id: int


class FriendRequestUpdate(BaseModel):
    """Schema for updating friend request status"""
    status: str  # accepted, declined, cancelled


class FriendRequestRead(FriendRequestBase):
    """Schema for reading friend requests"""
    id: int
    sender_id: int
    receiver_id: int
    sender: UserBasic
    receiver: UserBasic
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Response schemas
class FriendsListResponse(BaseModel):
    """Response schema for friends list"""
    friends: List[FriendshipRead]
    count: int


class FriendRequestsResponse(BaseModel):
    """Response schema for friend requests"""
    incoming_requests: List[FriendRequestRead]
    outgoing_requests: List[FriendRequestRead]
    incoming_count: int
    outgoing_count: int


class UserSearchResponse(BaseModel):
    """Response schema for user search"""
    users: List[UserBasic]
    count: int
    query: str


# Action response schemas
class FriendActionResponse(BaseModel):
    """Response schema for friend actions"""
    success: bool
    message: str
    friendship: Optional[FriendshipRead] = None


class FriendRequestActionResponse(BaseModel):
    """Response schema for friend request actions"""
    success: bool
    message: str
    request: Optional[FriendRequestRead] = None