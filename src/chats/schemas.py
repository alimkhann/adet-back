from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# User basic info (reused from friends module)
class UserBasic(BaseModel):
    id: int
    username: Optional[str] = None
    name: Optional[str] = None
    profile_image_url: Optional[str] = None

    class Config:
        from_attributes = True


# Message schemas
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)
    message_type: str = Field(default="text")
    replied_to_message_id: Optional[int] = None


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    message_type: str
    status: str
    created_at: datetime
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    sender: UserBasic
    replied_to_message_id: Optional[int] = None
    replied_to_message: Optional["MessageResponse"] = None

    class Config:
        from_attributes = True


# Conversation schemas
class ConversationCreate(BaseModel):
    participant_id: int = Field(..., description="ID of the friend to start conversation with")


class ConversationResponse(BaseModel):
    id: int
    participant_1_id: int
    participant_2_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_message_at: datetime
    other_participant: UserBasic
    last_message: Optional[MessageResponse] = None
    unread_count: int = 0
    is_other_online: bool = False
    other_last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]


# Message list with pagination
class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total_count: int
    has_more: bool = False


# WebSocket event schemas
class WebSocketEvent(BaseModel):
    type: str
    data: dict


class MessageEvent(BaseModel):
    type: str = "message"
    conversation_id: int
    message: MessageResponse


class TypingEvent(BaseModel):
    type: str = "typing"
    conversation_id: int
    user_id: int
    is_typing: bool


class PresenceEvent(BaseModel):
    type: str = "presence"
    conversation_id: int
    user_id: int
    is_online: bool
    last_seen: Optional[datetime] = None


class MessageStatusEvent(BaseModel):
    type: str = "message_status"
    conversation_id: int
    message_id: int
    status: str  # delivered, read
    timestamp: datetime


class ConnectionEvent(BaseModel):
    type: str = "connection"
    status: str  # connected, disconnected, error
    message: Optional[str] = None


# WebSocket message wrapper
class WebSocketMessage(BaseModel):
    event_type: str
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Error response
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class MessageDeleteRequest(BaseModel):
    delete_for_everyone: bool = False