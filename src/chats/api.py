import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_db
from ..auth.dependencies import get_current_user
from ..auth.models import User as UserModel
from .schemas import (
    ConversationResponse, ConversationListResponse, ConversationCreate,
    MessageResponse, MessageListResponse, MessageCreate, ErrorResponse
)
from .service import ChatService
from .websocket_manager import chat_websocket_manager
from .websocket_auth import websocket_auth_required, extract_token_from_query

router = APIRouter()
logger = logging.getLogger(__name__)


# REST API Endpoints

@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get all conversations for the current user"""
    try:
        conversations = await ChatService.get_user_conversations(
            db, current_user.id, limit, offset
        )
        return ConversationListResponse(conversations=conversations)
    except Exception as e:
        logger.error(f"Error getting conversations for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversations")


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new conversation or return existing one"""
    try:
        conversation = await ChatService.create_or_get_conversation(
            db, current_user.id, conversation_data
        )
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating conversation for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get detailed conversation information"""
    try:
        conversation = await ChatService.get_conversation_info(
            db, conversation_id, current_user.id
        )
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id} for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation")


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def get_messages(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    before_message_id: Optional[int] = Query(None),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get messages for a conversation with pagination"""
    try:
        messages, total_count, has_more = await ChatService.get_conversation_messages(
            db, conversation_id, current_user.id, limit, offset, before_message_id
        )
        return MessageListResponse(
            messages=messages,
            total_count=total_count,
            has_more=has_more
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: int,
    message_data: MessageCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Send a new message to a conversation"""
    try:
        message = await ChatService.send_message(
            db, conversation_id, current_user.id, message_data
        )
        return message
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message to conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")


@router.post("/conversations/{conversation_id}/read")
async def mark_messages_as_read(
    conversation_id: int,
    last_message_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Mark messages as read up to a specific message"""
    try:
        await ChatService.mark_messages_as_read(
            db, conversation_id, current_user.id, last_message_id
        )
        return {"status": "success", "message": "Messages marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking messages as read in conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark messages as read")


# WebSocket Endpoint

@router.websocket("/ws/{conversation_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    WebSocket endpoint for real-time chat functionality.
    Requires authentication token in query parameters.
    """
    user_id = None

    try:
        # Extract and validate authentication token
        token = extract_token_from_query(websocket)
        if not token:
            await websocket.close(code=1008, reason="Authentication token required")
            return

        # Authenticate user
        user_id = await websocket_auth_required(websocket, token)

        # Connect to WebSocket manager
        await chat_websocket_manager.connect(websocket, user_id, conversation_id, db)

        logger.info(f"WebSocket connected: user {user_id}, conversation {conversation_id}")

        # Listen for incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)

                event_type = message_data.get("event_type")
                event_data = message_data.get("data", {})

                if event_type == "send_message":
                    # Handle new message
                    content = event_data.get("content")
                    if content and content.strip():
                        message_create = MessageCreate(content=content.strip())
                        message_response = await ChatService.send_message(
                            db, conversation_id, user_id, message_create
                        )

                        # Send confirmation back to sender
                        await chat_websocket_manager.send_to_websocket(
                            websocket,
                            {
                                "type": "message_sent",
                                "data": message_response.model_dump()
                            }
                        )

                elif event_type == "typing":
                    # Handle typing indicator
                    is_typing = event_data.get("is_typing", False)
                    await ChatService.handle_typing_indicator(
                        conversation_id, user_id, is_typing
                    )

                elif event_type == "mark_read":
                    # Handle marking messages as read
                    last_message_id = event_data.get("last_message_id")
                    if last_message_id:
                        await ChatService.mark_messages_as_read(
                            db, conversation_id, user_id, last_message_id
                        )

                else:
                    logger.warning(f"Unknown event type: {event_type}")

            except json.JSONDecodeError:
                logger.error("Invalid JSON received from WebSocket")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }))

            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Failed to process message"}
                }))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user {user_id}, conversation {conversation_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket.client_state.name != "DISCONNECTED":
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except:
                pass

    finally:
        # Clean up connection
        if user_id:
            try:
                await chat_websocket_manager.disconnect(
                    websocket, user_id, conversation_id, db
                )
            except Exception as e:
                logger.error(f"Error during WebSocket cleanup: {e}")


# Health check endpoint
@router.get("/health")
async def chat_health_check():
    """Health check for chat service"""
    return {
        "status": "ok",
        "service": "chat",
        "websocket_connections": {
            "active_conversations": len(chat_websocket_manager.conversation_connections),
            "active_users": len(chat_websocket_manager.user_connections)
        }
    }