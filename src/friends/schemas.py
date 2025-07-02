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


# Close Friends schemas
class CloseFriendBase(BaseModel):
    """Base close friend schema"""
    pass


class CloseFriendCreate(BaseModel):
    """Schema for creating close friend relationship"""
    friend_id: int
    is_close_friend: bool


class CloseFriendRead(CloseFriendBase):
    """Schema for reading close friends"""
    id: int
    user_id: int
    close_friend_id: int
    close_friend: UserBasic
    created_at: datetime

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


class CloseFriendsResponse(BaseModel):
    """Response schema for close friends list"""
    close_friends: List[UserBasic]
    count: int


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


class CloseFriendActionResponse(BaseModel):
    """Response schema for close friend actions"""
    success: bool
    message: str
    close_friend: Optional[CloseFriendRead] = None
    incoming_count: int
    outgoing_count: int


# Blocked Users schemas
class BlockedUserBase(BaseModel):
    """Base blocked user schema"""
    reason: Optional[str] = None


class BlockedUserCreate(BlockedUserBase):
    """Schema for blocking a user"""
    pass


class BlockedUserRead(BlockedUserBase):
    """Schema for reading blocked users"""
    id: int
    blocker_id: int
    blocked_id: int
    blocked: UserBasic
    created_at: datetime

    class Config:
        from_attributes = True


# User Report schemas
class UserReportBase(BaseModel):
    """Base user report schema"""
    category: str  # harassment, spam, inappropriate_content, fake_account, other
    description: Optional[str] = None


class UserReportCreate(UserReportBase):
    """Schema for creating a user report"""
    pass


class UserReportRead(UserReportBase):
    """Schema for reading user reports"""
    id: int
    reporter_id: int
    reported_id: int
    reporter: UserBasic
    reported: UserBasic
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None

    class Config:
        from_attributes = True


class UserReportUpdate(BaseModel):
    """Schema for updating report status"""
    status: str  # reviewed, resolved, dismissed


# Response schemas for blocking and reporting
class BlockedUsersResponse(BaseModel):
    """Response schema for blocked users list"""
    blocked_users: List[BlockedUserRead]
    count: int


class BlockActionResponse(BaseModel):
    """Response schema for block actions"""
    success: bool
    message: str
    blocked_user: Optional[BlockedUserRead] = None


class ReportActionResponse(BaseModel):
    """Response schema for report actions"""
    success: bool
    message: str
    report: Optional[UserReportRead] = None


class ReportsResponse(BaseModel):
    """Response schema for reports list (admin)"""
    reports: List[UserReportRead]
    count: int
    status: str