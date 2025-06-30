import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from .crud import ParticipantCRUD
from .schemas import (
    MessageEvent, TypingEvent, PresenceEvent, MessageStatusEvent,
    ConnectionEvent, WebSocketMessage
)

logger = logging.getLogger(__name__)


class ChatWebSocketManager:
    """
    Manages WebSocket connections for real-time chat functionality.
    Handles connection pooling, message broadcasting, and presence tracking.
    """

    def __init__(self):
        # Map of conversation_id -> set of (websocket, user_id) tuples
        self.conversation_connections: Dict[int, Set[tuple]] = {}
        # Map of user_id -> set of (websocket, conversation_id) tuples
        self.user_connections: Dict[int, Set[tuple]] = {}
        # Track typing status: conversation_id -> user_id -> is_typing
        self.typing_status: Dict[int, Dict[int, bool]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        conversation_id: int,
        db: AsyncSession
    ):
        """Accept WebSocket connection and add to tracking"""
        try:
            await websocket.accept()

            # Add to conversation connections
            if conversation_id not in self.conversation_connections:
                self.conversation_connections[conversation_id] = set()
            self.conversation_connections[conversation_id].add((websocket, user_id))

            # Add to user connections
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add((websocket, conversation_id))

            # Update online status in database
            await ParticipantCRUD.update_online_status(
                db, conversation_id, user_id, is_online=True
            )

            # Notify other participants that user is online
            await self.broadcast_presence_update(
                conversation_id, user_id, is_online=True, exclude_user=user_id
            )

            # Send connection confirmation
            await self.send_to_websocket(websocket, ConnectionEvent(
                type="connection",
                status="connected",
                message="Successfully connected to chat"
            ))

            logger.info(f"User {user_id} connected to conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Error connecting user {user_id} to conversation {conversation_id}: {e}")
            await websocket.close(code=1011, reason="Connection error")

    async def disconnect(
        self,
        websocket: WebSocket,
        user_id: int,
        conversation_id: int,
        db: AsyncSession
    ):
        """Remove WebSocket connection and update presence"""
        try:
            # Remove from conversation connections
            if conversation_id in self.conversation_connections:
                self.conversation_connections[conversation_id].discard((websocket, user_id))
                if not self.conversation_connections[conversation_id]:
                    del self.conversation_connections[conversation_id]

            # Remove from user connections
            if user_id in self.user_connections:
                self.user_connections[user_id].discard((websocket, conversation_id))
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]

            # Clear typing status
            if conversation_id in self.typing_status:
                self.typing_status[conversation_id].pop(user_id, None)
                if not self.typing_status[conversation_id]:
                    del self.typing_status[conversation_id]

            # Update online status in database
            await ParticipantCRUD.update_online_status(
                db, conversation_id, user_id, is_online=False
            )

            # Notify other participants that user is offline
            await self.broadcast_presence_update(
                conversation_id, user_id, is_online=False, exclude_user=user_id
            )

            logger.info(f"User {user_id} disconnected from conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Error disconnecting user {user_id} from conversation {conversation_id}: {e}")

    async def broadcast_message(
        self,
        conversation_id: int,
        message_data: dict,
        exclude_user: Optional[int] = None
    ):
        """Broadcast message to all participants in conversation"""
        if conversation_id not in self.conversation_connections:
            return

        event = MessageEvent(
            conversation_id=conversation_id,
            message=message_data
        )

        connections = self.conversation_connections[conversation_id].copy()
        for websocket, user_id in connections:
            if exclude_user and user_id == exclude_user:
                continue

            try:
                await self.send_to_websocket(websocket, event)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                # Remove broken connection
                self.conversation_connections[conversation_id].discard((websocket, user_id))

    async def broadcast_typing_indicator(
        self,
        conversation_id: int,
        user_id: int,
        is_typing: bool
    ):
        """Broadcast typing indicator to conversation participants"""
        # Update typing status
        if conversation_id not in self.typing_status:
            self.typing_status[conversation_id] = {}
        self.typing_status[conversation_id][user_id] = is_typing

        # If not typing, remove from status after a delay
        if not is_typing:
            self.typing_status[conversation_id].pop(user_id, None)

        if conversation_id not in self.conversation_connections:
            return

        event = TypingEvent(
            conversation_id=conversation_id,
            user_id=user_id,
            is_typing=is_typing
        )

        connections = self.conversation_connections[conversation_id].copy()
        for websocket, participant_id in connections:
            if participant_id == user_id:  # Don't send to sender
                continue

            try:
                await self.send_to_websocket(websocket, event)
            except Exception as e:
                logger.error(f"Error sending typing indicator to user {participant_id}: {e}")
                self.conversation_connections[conversation_id].discard((websocket, participant_id))

    async def broadcast_presence_update(
        self,
        conversation_id: int,
        user_id: int,
        is_online: bool,
        exclude_user: Optional[int] = None
    ):
        """Broadcast presence update to conversation participants"""
        if conversation_id not in self.conversation_connections:
            return

        event = PresenceEvent(
            conversation_id=conversation_id,
            user_id=user_id,
            is_online=is_online,
            last_seen=datetime.utcnow() if not is_online else None
        )

        connections = self.conversation_connections[conversation_id].copy()
        for websocket, participant_id in connections:
            if exclude_user and participant_id == exclude_user:
                continue

            try:
                await self.send_to_websocket(websocket, event)
            except Exception as e:
                logger.error(f"Error sending presence update to user {participant_id}: {e}")
                self.conversation_connections[conversation_id].discard((websocket, participant_id))

    async def broadcast_message_status(
        self,
        conversation_id: int,
        message_id: int,
        status: str,
        exclude_user: Optional[int] = None
    ):
        """Broadcast message status update (delivered, read)"""
        if conversation_id not in self.conversation_connections:
            return

        event = MessageStatusEvent(
            conversation_id=conversation_id,
            message_id=message_id,
            status=status,
            timestamp=datetime.utcnow()
        )

        connections = self.conversation_connections[conversation_id].copy()
        for websocket, user_id in connections:
            if exclude_user and user_id == exclude_user:
                continue

            try:
                await self.send_to_websocket(websocket, event)
            except Exception as e:
                logger.error(f"Error sending message status to user {user_id}: {e}")
                self.conversation_connections[conversation_id].discard((websocket, user_id))

    async def send_to_user(
        self,
        user_id: int,
        event: Any
    ):
        """Send event to all connections of a specific user"""
        if user_id not in self.user_connections:
            return

        connections = self.user_connections[user_id].copy()
        for websocket, conversation_id in connections:
            try:
                await self.send_to_websocket(websocket, event)
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                self.user_connections[user_id].discard((websocket, conversation_id))

    async def send_to_websocket(self, websocket: WebSocket, event: Any):
        """Send event to specific WebSocket connection"""
        try:
            if hasattr(event, 'model_dump'):
                data = event.model_dump()
            else:
                data = event.__dict__

            message = WebSocketMessage(
                event_type=data.get('type', 'unknown'),
                data=data
            )

            await websocket.send_text(message.model_dump_json())

        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            raise

    def get_conversation_participants(self, conversation_id: int) -> Set[int]:
        """Get list of currently connected user IDs for a conversation"""
        if conversation_id not in self.conversation_connections:
            return set()

        return {user_id for _, user_id in self.conversation_connections[conversation_id]}

    def get_user_conversations(self, user_id: int) -> Set[int]:
        """Get list of conversation IDs user is currently connected to"""
        if user_id not in self.user_connections:
            return set()

        return {conversation_id for _, conversation_id in self.user_connections[user_id]}

    def is_user_online_in_conversation(self, user_id: int, conversation_id: int) -> bool:
        """Check if user is currently connected to specific conversation"""
        if conversation_id not in self.conversation_connections:
            return False

        for _, participant_id in self.conversation_connections[conversation_id]:
            if participant_id == user_id:
                return True
        return False

    def get_typing_users(self, conversation_id: int) -> Set[int]:
        """Get list of users currently typing in conversation"""
        if conversation_id not in self.typing_status:
            return set()

        return {
            user_id for user_id, is_typing
            in self.typing_status[conversation_id].items()
            if is_typing
        }


# Global WebSocket manager instance
chat_websocket_manager = ChatWebSocketManager()