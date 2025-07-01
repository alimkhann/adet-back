from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

# Import User schema from friends module
from ..friends.schemas import UserBasic


# Enums
class ProofTypeEnum(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    TEXT = "text"
    AUDIO = "audio"


class PostPrivacyEnum(str, Enum):
    PRIVATE = "private"
    FRIENDS = "friends"
    CLOSE_FRIENDS = "close_friends"


# Base schemas
class PostBase(BaseModel):
    """Base post schema"""
    habit_id: Optional[int] = None
    proof_urls: List[str] = Field(..., min_items=1, max_items=5)
    proof_type: ProofTypeEnum
    description: Optional[str] = Field(None, max_length=280)
    privacy: PostPrivacyEnum = PostPrivacyEnum.FRIENDS

    @validator('description')
    def validate_description(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v


class PostCreate(PostBase):
    """Schema for creating posts"""
    pass


class PostUpdate(BaseModel):
    """Schema for updating posts (privacy and description only)"""
    description: Optional[str] = Field(None, max_length=280)
    privacy: PostPrivacyEnum

    @validator('description')
    def validate_description(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v


class PostRead(PostBase):
    """Schema for reading posts"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Habit streak at time of post creation
    habit_streak: Optional[int] = None

    # Analytics
    views_count: int = 0
    likes_count: int = 0
    comments_count: int = 0

    # User info
    user: UserBasic

    # Current user interaction state
    is_liked_by_current_user: bool = False
    is_viewed_by_current_user: bool = False

    class Config:
        from_attributes = True


# Comment schemas
class PostCommentBase(BaseModel):
    """Base comment schema"""
    content: str = Field(..., min_length=1, max_length=150)

    @validator('content')
    def validate_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Comment content cannot be empty')
        return v.strip()


class PostCommentCreate(PostCommentBase):
    """Schema for creating comments"""
    post_id: int
    parent_comment_id: Optional[int] = None


class PostCommentRead(PostCommentBase):
    """Schema for reading comments"""
    id: int
    post_id: int
    user_id: int
    parent_comment_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Analytics
    likes_count: int = 0
    replies_count: int = 0

    # User info
    user: UserBasic

    # Current user interaction state
    is_liked_by_current_user: bool = False

    class Config:
        from_attributes = True


# Like schemas
class PostLikeRead(BaseModel):
    """Schema for reading likes"""
    id: int
    post_id: Optional[int] = None
    comment_id: Optional[int] = None
    user_id: int
    created_at: datetime
    user: UserBasic

    class Config:
        from_attributes = True


# View schemas
class PostViewCreate(BaseModel):
    """Schema for creating post views"""
    post_id: int
    view_duration: Optional[int] = None


# Analytics schemas
class PostAnalytics(BaseModel):
    """Schema for post analytics"""
    post_id: int
    views_count: int
    likes_count: int
    comments_count: int
    shares_count: int = 0
    engagement_rate: float
    top_likers: List[UserBasic] = []


# Response schemas
class PostsResponse(BaseModel):
    """Response schema for posts list"""
    posts: List[PostRead]
    count: int
    has_more: bool = False
    next_cursor: Optional[str] = None


class PostCommentsResponse(BaseModel):
    """Response schema for comments list"""
    comments: List[PostCommentRead]
    count: int
    has_more: bool = False
    next_cursor: Optional[str] = None


class PostActionResponse(BaseModel):
    """Response schema for post actions"""
    success: bool
    message: str
    post: Optional[PostRead] = None


class CommentActionResponse(BaseModel):
    """Response schema for comment actions"""
    success: bool
    message: str
    comment: Optional[PostCommentRead] = None


class LikeActionResponse(BaseModel):
    """Response schema for like actions"""
    success: bool
    message: str
    is_liked: bool
    likes_count: int


# Feed schemas
class FeedResponse(BaseModel):
    """Response schema for feed"""
    posts: List[PostRead]
    count: int
    has_more: bool = False
    next_cursor: Optional[str] = None
    feed_metadata: Dict[str, Any] = {}


# Report schemas
class PostReportCreate(BaseModel):
    """Schema for creating post reports"""
    post_id: int
    reason: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=500)

    @validator('reason')
    def validate_reason(cls, v):
        allowed_reasons = [
            'spam', 'inappropriate', 'harassment', 'false_information',
            'violence', 'hate_speech', 'adult_content', 'other'
        ]
        if v not in allowed_reasons:
            raise ValueError(f'Reason must be one of: {", ".join(allowed_reasons)}')
        return v


class PostReportRead(BaseModel):
    """Schema for reading post reports"""
    id: int
    post_id: int
    reporter_id: int
    reason: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None

    # Related objects
    reporter: UserBasic

    class Config:
        from_attributes = True


# Batch operation schemas
class BatchViewRequest(BaseModel):
    """Schema for batch view operations"""
    post_ids: List[int] = Field(..., min_items=1, max_items=20)


class BatchViewResponse(BaseModel):
    """Response schema for batch view operations"""
    success: bool
    message: str
    processed_count: int
    failed_count: int = 0