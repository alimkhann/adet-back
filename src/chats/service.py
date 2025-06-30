from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from .crud import ConversationCRUD, MessageCRUD, ParticipantCRUD
from .models import Conversation, Message
from .schemas import (
    ConversationResponse, ConversationCreate,
    MessageResponse, MessageCreate, UserBasic
)
from .websocket_manager import chat_websocket_manager


class ChatService:
    """Business logic for chat functionality"""

    @staticmethod
    async def get_user_conversations(
        db: AsyncSession, user_id: int, limit: int = 50, offset: int = 0
    ) -> List[ConversationResponse]:
        """Get all conversations for a user with rich data"""
        conversations = await ConversationCRUD.get_user_conversations(
            db, user_id, limit, offset
        )

        result = []
        for conv in conversations:
            # Determine the other participant
            other_participant_id = (
                conv.participant_2_id if conv.participant_1_id == user_id
                else conv.participant_1_id
            )

            other_participant = (
                conv.participant_2 if conv.participant_1_id == user_id
                else conv.participant_1
            )

            # Get last message
            last_message = None
            if conv.messages:
                latest_msg = max(conv.messages, key=lambda m: m.created_at)
                last_message = MessageResponse(
                    id=latest_msg.id,
                    conversation_id=latest_msg.conversation_id,
                    sender_id=latest_msg.sender_id,
                    content=latest_msg.content,
                    message_type=latest_msg.message_type,
                    status=latest_msg.status,
                    created_at=latest_msg.created_at,
                    delivered_at=latest_msg.delivered_at,
                    read_at=latest_msg.read_at,
                    sender=UserBasic(
                        id=latest_msg.sender.id,
                        username=latest_msg.sender.username,
                        name=latest_msg.sender.name,
                        profile_image_url=latest_msg.sender.profile_image_url
                    ),
                    replied_to_message_id=getattr(latest_msg, 'replied_to_message_id', None),
                    replied_to_message=None
                )

            # Get unread count and presence info
            unread_count = await ParticipantCRUD.get_unread_count(
                db, conv.id, user_id
            )

            is_other_online = chat_websocket_manager.is_user_online_in_conversation(
                other_participant_id, conv.id
            )

            # Get participant info for last seen
            participant = await ParticipantCRUD.get_participant(
                db, conv.id, other_participant_id
            )

            conversation_response = ConversationResponse(
                id=conv.id,
                participant_1_id=conv.participant_1_id,
                participant_2_id=conv.participant_2_id,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                last_message_at=conv.last_message_at,
                other_participant=UserBasic(
                    id=other_participant.id,
                    username=other_participant.username,
                    name=other_participant.name,
                    profile_image_url=other_participant.profile_image_url
                ),
                last_message=last_message,
                unread_count=unread_count,
                is_other_online=is_other_online,
                other_last_seen=participant.last_seen_at if participant else None
            )

            result.append(conversation_response)

        return result

    @staticmethod
    async def create_or_get_conversation(
        db: AsyncSession, user_id: int, conversation_create: ConversationCreate
    ) -> ConversationResponse:
        """Create new conversation or return existing one"""
        other_user_id = conversation_create.participant_id

        # Check if users are friends
        are_friends = await ConversationCRUD.check_users_are_friends(
            db, user_id, other_user_id
        )

        if not are_friends:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only start conversations with friends"
            )

        # Check if conversation already exists
        existing_conv = await ConversationCRUD.get_conversation_between_users(
            db, user_id, other_user_id
        )

        if existing_conv:
            conversation = existing_conv
        else:
            # Create new conversation
            conversation = await ConversationCRUD.create_conversation(
                db, user_id, other_user_id
            )

        # Convert to response format
        other_participant = (
            conversation.participant_2 if conversation.participant_1_id == user_id
            else conversation.participant_1
        )

        unread_count = await ParticipantCRUD.get_unread_count(
            db, conversation.id, user_id
        )

        return ConversationResponse(
            id=conversation.id,
            participant_1_id=conversation.participant_1_id,
            participant_2_id=conversation.participant_2_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            last_message_at=conversation.last_message_at,
            other_participant=UserBasic(
                id=other_participant.id,
                username=other_participant.username,
                name=other_participant.name,
                profile_image_url=other_participant.profile_image_url
            ),
            last_message=None,
            unread_count=unread_count,
            is_other_online=False,
            other_last_seen=None
        )

    @staticmethod
    async def get_conversation_messages(
        db: AsyncSession,
        conversation_id: int,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        before_message_id: Optional[int] = None
    ) -> Tuple[List[MessageResponse], int, bool]:
        """Get messages for a conversation with pagination"""
        # Verify user is participant in conversation
        participant = await ParticipantCRUD.get_participant(
            db, conversation_id, user_id
        )

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant in this conversation"
            )

        messages, total_count = await MessageCRUD.get_conversation_messages(
            db, conversation_id, limit, offset, before_message_id
        )

        # Convert to response format
        message_responses = []
        for msg in messages:
            message_response = MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                sender_id=msg.sender_id,
                content=msg.content,
                message_type=msg.message_type,
                status=msg.status,
                created_at=msg.created_at,
                delivered_at=msg.delivered_at,
                read_at=msg.read_at,
                sender=UserBasic(
                    id=msg.sender.id,
                    username=msg.sender.username,
                    name=msg.sender.name,
                    profile_image_url=msg.sender.profile_image_url
                ),
                replied_to_message_id=msg.replied_to_message_id,
                replied_to_message=None  # For now, we'll add this later if needed
            )
            message_responses.append(message_response)

        has_more = (offset + len(messages)) < total_count

        return message_responses, total_count, has_more

    @staticmethod
    async def send_message(
        db: AsyncSession, conversation_id: int, user_id: int, message_create: MessageCreate
    ) -> MessageResponse:
        """Send a message in a conversation"""
        # Verify user is participant in conversation
        participant = await ParticipantCRUD.get_participant(
            db, conversation_id, user_id
        )

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant in this conversation"
            )

        # Create the message
        message = await MessageCRUD.create_message(
            db,
            conversation_id=conversation_id,
            sender_id=user_id,
            content=message_create.content,
            message_type=message_create.message_type,
            replied_to_message_id=message_create.replied_to_message_id
        )

        # Convert to response format
        message_response = MessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            content=message.content,
            message_type=message.message_type,
            status=message.status,
            created_at=message.created_at,
            delivered_at=message.delivered_at,
            read_at=message.read_at,
            sender=UserBasic(
                id=message.sender.id,
                username=message.sender.username,
                name=message.sender.name,
                profile_image_url=message.sender.profile_image_url
            ),
            replied_to_message_id=message.replied_to_message_id,
            replied_to_message=None  # For now, we'll add this later if needed
        )

        # Broadcast message via WebSocket
        await chat_websocket_manager.broadcast_message(
            conversation_id,
            message_response.model_dump(),
            exclude_user=user_id
        )

        # Mark as delivered for online users
        online_participants = chat_websocket_manager.get_conversation_participants(conversation_id)
        if len(online_participants) > 1:  # More than just the sender
            await MessageCRUD.update_message_status(db, message.id, "delivered")
            await chat_websocket_manager.broadcast_message_status(
                conversation_id, message.id, "delivered", exclude_user=user_id
            )

        return message_response

    @staticmethod
    async def mark_messages_as_read(
        db: AsyncSession,
        conversation_id: int,
        user_id: int,
        last_message_id: int
    ):
        """Mark messages as read and notify sender"""
        # Verify user is participant
        participant = await ParticipantCRUD.get_participant(
            db, conversation_id, user_id
        )

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant in this conversation"
            )

        # Mark messages as read
        await ParticipantCRUD.mark_messages_as_read(
            db, conversation_id, user_id, last_message_id
        )

        # Update message status to read
        await MessageCRUD.update_message_status(db, last_message_id, "read")

        # Broadcast read status
        await chat_websocket_manager.broadcast_message_status(
            conversation_id, last_message_id, "read", exclude_user=user_id
        )

    @staticmethod
    async def handle_typing_indicator(
        conversation_id: int, user_id: int, is_typing: bool
    ):
        """Handle typing indicator events"""
        await chat_websocket_manager.broadcast_typing_indicator(
            conversation_id, user_id, is_typing
        )

    @staticmethod
    async def get_conversation_info(
        db: AsyncSession, conversation_id: int, user_id: int
    ) -> ConversationResponse:
        """Get detailed conversation information"""
        # Verify user is participant
        participant = await ParticipantCRUD.get_participant(
            db, conversation_id, user_id
        )

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant in this conversation"
            )

        # Get conversation directly by ID with proper async loading
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        query = select(Conversation).where(Conversation.id == conversation_id).options(
            selectinload(Conversation.participant_1),
            selectinload(Conversation.participant_2)
        )
        result = await db.execute(query)
        conv = result.scalar_one_or_none()

        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Determine other participant
        other_participant_id = (
            conv.participant_2_id if conv.participant_1_id == user_id
            else conv.participant_1_id
        )

        other_participant = (
            conv.participant_2 if conv.participant_1_id == user_id
            else conv.participant_1
        )

        # Get unread count
        unread_count = await ParticipantCRUD.get_unread_count(
            db, conversation_id, user_id
        )

        # Check online status
        is_other_online = chat_websocket_manager.is_user_online_in_conversation(
            other_participant_id, conversation_id
        )

        # Get other participant info
        other_participant_record = await ParticipantCRUD.get_participant(
            db, conversation_id, other_participant_id
        )

        return ConversationResponse(
            id=conv.id,
            participant_1_id=conv.participant_1_id,
            participant_2_id=conv.participant_2_id,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            last_message_at=conv.last_message_at,
            other_participant=UserBasic(
                id=other_participant.id,
                username=other_participant.username,
                name=other_participant.name,
                profile_image_url=other_participant.profile_image_url
            ),
            last_message=None,
            unread_count=unread_count,
            is_other_online=is_other_online,
            other_last_seen=other_participant_record.last_seen_at if other_participant_record else None
        )

    @staticmethod
    async def edit_message(
        db: AsyncSession,
        conversation_id: int,
        message_id: int,
        user_id: int,
        content: str
    ) -> MessageResponse:
        """Edit a message (only by sender within time limit)"""
        # Verify user is participant in conversation
        participant = await ParticipantCRUD.get_participant(
            db, conversation_id, user_id
        )

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant in this conversation"
            )

        # Update the message
        updated_message = await MessageCRUD.update_message_content(
            db, message_id, user_id, content
        )

        if not updated_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found or cannot be edited"
            )

        # Convert to response format
        message_response = MessageResponse(
            id=updated_message.id,
            conversation_id=updated_message.conversation_id,
            sender_id=updated_message.sender_id,
            content=updated_message.content,
            message_type=updated_message.message_type,
            status=updated_message.status,
            created_at=updated_message.created_at,
            delivered_at=updated_message.delivered_at,
            read_at=updated_message.read_at,
            sender=UserBasic(
                id=updated_message.sender.id,
                username=updated_message.sender.username,
                name=updated_message.sender.name,
                profile_image_url=updated_message.sender.profile_image_url
            ),
            replied_to_message_id=updated_message.replied_to_message_id,
            replied_to_message=None
        )

        # Broadcast updated message via WebSocket
        await chat_websocket_manager.broadcast_message_edit(
            conversation_id,
            message_response.model_dump(),
            exclude_user=user_id
        )

        return message_response

    @staticmethod
    async def delete_message(
        db: AsyncSession,
        conversation_id: int,
        message_id: int,
        user_id: int,
        delete_for_everyone: bool = False
    ):
        """Delete a message"""
        # Verify user is participant in conversation
        participant = await ParticipantCRUD.get_participant(
            db, conversation_id, user_id
        )

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant in this conversation"
            )

        # Delete the message
        success = await MessageCRUD.delete_message(
            db, message_id, user_id, delete_for_everyone
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found or cannot be deleted"
            )

        # Broadcast deletion via WebSocket
        await chat_websocket_manager.broadcast_message_delete(
            conversation_id,
            message_id,
            delete_for_everyone,
            exclude_user=user_id
        )

        return {"status": "success", "message": "Message deleted"}