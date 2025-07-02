from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy import and_, or_, desc, func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
import logging

from .models import Conversation, Message, ConversationParticipant
from ..friends.models import Friendship

logger = logging.getLogger(__name__)


class ConversationCRUD:
    """CRUD operations for conversations"""

    @staticmethod
    async def get_conversation_between_users(
        db: AsyncSession, user_id: int, other_user_id: int
    ) -> Optional[Conversation]:
        """Get existing conversation between two users"""
        query = select(Conversation).where(
            or_(
                and_(
                    Conversation.participant_1_id == user_id,
                    Conversation.participant_2_id == other_user_id
                ),
                and_(
                    Conversation.participant_1_id == other_user_id,
                    Conversation.participant_2_id == user_id
                )
            )
        ).options(
            selectinload(Conversation.participant_1),
            selectinload(Conversation.participant_2)
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_conversation(
        db: AsyncSession, user_id: int, other_user_id: int
    ) -> Conversation:
        """Create a new conversation between two users"""
        # Ensure consistent ordering (smaller ID first)
        participant_1_id = min(user_id, other_user_id)
        participant_2_id = max(user_id, other_user_id)

        conversation = Conversation(
            participant_1_id=participant_1_id,
            participant_2_id=participant_2_id
        )

        db.add(conversation)
        await db.flush()

        # Create participant records for both users
        participant_1 = ConversationParticipant(
            conversation_id=conversation.id,
            user_id=participant_1_id
        )
        participant_2 = ConversationParticipant(
            conversation_id=conversation.id,
            user_id=participant_2_id
        )

        db.add(participant_1)
        db.add(participant_2)
        await db.commit()

        # Reload with relationships
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def get_user_conversations(
        db: AsyncSession, user_id: int, limit: int = 50, offset: int = 0
    ) -> List[Conversation]:
        """Get all conversations for a user, ordered by last message"""
        query = (
            select(Conversation)
            .where(
                or_(
                    Conversation.participant_1_id == user_id,
                    Conversation.participant_2_id == user_id
                )
            )
            .options(
                selectinload(Conversation.participant_1),
                selectinload(Conversation.participant_2),
                selectinload(Conversation.messages).selectinload(Message.sender)
            )
            .order_by(desc(Conversation.last_message_at))
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_conversation_last_message(
        db: AsyncSession, conversation_id: int, timestamp: datetime
    ):
        """Update the last message timestamp for conversation ordering"""
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_message_at=timestamp)
        )
        await db.commit()

    @staticmethod
    async def check_users_are_friends(
        db: AsyncSession, user_id: int, other_user_id: int
    ) -> bool:
        """Check if two users are friends (required for messaging)"""
        query = select(Friendship).where(
            and_(
                Friendship.user_id == user_id,
                Friendship.friend_id == other_user_id,
                Friendship.status == "active"
            )
        )

        result = await db.execute(query)
        return result.scalar_one_or_none() is not None


class MessageCRUD:
    """CRUD operations for messages"""

    @staticmethod
    async def create_message(
        db: AsyncSession,
        conversation_id: int,
        sender_id: int,
        content: str,
        message_type: str = "text",
        replied_to_message_id: Optional[int] = None
    ) -> Message:
        """Create a new message"""
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            status="sent",
            replied_to_message_id=replied_to_message_id
        )

        db.add(message)
        await db.flush()

        # Update conversation last message timestamp
        await ConversationCRUD.update_conversation_last_message(
            db, conversation_id, message.created_at
        )

        # Update unread counts for other participants
        await ParticipantCRUD.increment_unread_count(
            db, conversation_id, sender_id
        )

        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_conversation_messages(
        db: AsyncSession,
        conversation_id: int,
        limit: int = 50,
        offset: int = 0,
        before_message_id: Optional[int] = None
    ) -> Tuple[List[Message], int]:
        """Get messages for a conversation with pagination"""
        base_query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .options(selectinload(Message.sender))
        )

        if before_message_id:
            base_query = base_query.where(Message.id < before_message_id)

        # Get total count
        count_query = select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
        if before_message_id:
            count_query = count_query.where(Message.id < before_message_id)

        count_result = await db.execute(count_query)
        total_count = count_result.scalar()

        # Get messages
        query = (
            base_query
            .order_by(desc(Message.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        messages = list(reversed(result.scalars().all()))  # Reverse to show oldest first

        return messages, total_count

    @staticmethod
    async def update_message_status(
        db: AsyncSession,
        message_id: int,
        status: str,
        timestamp: Optional[datetime] = None
    ) -> Optional[Message]:
        """Update message status (delivered, read)"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        update_data = {"status": status}
        if status == "delivered":
            update_data["delivered_at"] = timestamp
        elif status == "read":
            update_data["read_at"] = timestamp

        await db.execute(
            update(Message)
            .where(Message.id == message_id)
            .values(**update_data)
        )
        await db.commit()

        # Get updated message
        query = select(Message).where(Message.id == message_id).options(
            selectinload(Message.sender)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_message_content(
        db: AsyncSession,
        message_id: int,
        sender_id: int,
        content: str
    ) -> Optional[Message]:
        """Update message content (only by sender within time limit)"""
        # Get the message first
        query = select(Message).where(
            and_(
                Message.id == message_id,
                Message.sender_id == sender_id
            )
        ).options(selectinload(Message.sender))

        result = await db.execute(query)
        message = result.scalar_one_or_none()

        if not message:
            return None

        # Check if message is within edit time limit (30 minutes)
        time_limit = timedelta(minutes=30)
        if datetime.utcnow() - message.created_at.replace(tzinfo=None) > time_limit:
            return None

        # Update the message
        await db.execute(
            update(Message)
            .where(Message.id == message_id)
            .values(content=content)
        )
        await db.commit()

        # Return updated message
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_message(
        db: AsyncSession,
        message_id: int,
        sender_id: int,
        delete_for_everyone: bool = False
    ) -> bool:
        """Delete message (soft delete with different behavior for delete_for_everyone)"""
        logger.info(f"Attempting to delete message {message_id} by user {sender_id}, delete_for_everyone={delete_for_everyone}")

        # First try to get the message if the user is the sender
        query = select(Message).where(
            and_(
                Message.id == message_id,
                Message.sender_id == sender_id
            )
        )

        result = await db.execute(query)
        message = result.scalar_one_or_none()

        logger.info(f"First query (by sender) found message: {message is not None}")

        # If not found and it's a bulk delete operation, try to get any message with this ID
        # that is already soft-deleted (either "Deleted for me" or "Message deleted")
        if not message:
            logger.info(f"Message not found by sender, trying fallback query for message {message_id}")
            query = select(Message).where(Message.id == message_id)
            result = await db.execute(query)
            message = result.scalar_one_or_none()

            if message:
                logger.info(f"Fallback query found message with content: '{message.content}'")
            else:
                logger.info(f"Fallback query found no message with id {message_id}")

            # Only allow deletion if the message is already soft-deleted
            if not message or (message.content not in ["Deleted for me", "Message deleted"]):
                logger.info(f"Rejecting deletion - message {'not found' if not message else 'content not soft-deleted: ' + message.content}")
                return False

        if delete_for_everyone:
            # If message is already deleted for everyone, remove it completely
            if message.content == "Message deleted":
                try:
                    # First, clear any references to this message in conversation_participants
                    from sqlalchemy import update
                    from ..chats.models import ConversationParticipant

                    # Update any conversation participants that have this as their last_read_message_id
                    update_stmt = (
                        update(ConversationParticipant)
                        .where(ConversationParticipant.last_read_message_id == message_id)
                        .values(last_read_message_id=None)
                    )
                    await db.execute(update_stmt)

                    # Now we can safely delete the message
                    await db.delete(message)
                    await db.commit()
                    return True
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Error deleting message {message_id}: {e}")
                    return False
            else:
                # Check if message is within delete time limit (30 minutes)
                time_limit = datetime.now(timezone.utc) - timedelta(minutes=30)
                if message.created_at < time_limit:
                    return False

                # Soft delete for everyone
                message.content = "Message deleted"
                message.message_type = "system"

                try:
                    await db.commit()
                    return True
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Error updating message {message_id}: {e}")
                    return False
        else:
            # Delete for me logic
            if message.content == "Deleted for me":
                # If already deleted for me, remove completely (same as delete for everyone)
                try:
                    # Clear any references to this message in conversation_participants
                    from sqlalchemy import update
                    from ..chats.models import ConversationParticipant

                    update_stmt = (
                        update(ConversationParticipant)
                        .where(ConversationParticipant.last_read_message_id == message_id)
                        .values(last_read_message_id=None)
                    )
                    await db.execute(update_stmt)

                    # Now we can safely delete the message
                    await db.delete(message)
                    await db.commit()
                    return True
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Error deleting message {message_id}: {e}")
                    return False
            elif message.content == "Message deleted":
                # If deleted for everyone, also remove completely
                try:
                    # Clear any references to this message in conversation_participants
                    from sqlalchemy import update
                    from ..chats.models import ConversationParticipant

                    update_stmt = (
                        update(ConversationParticipant)
                        .where(ConversationParticipant.last_read_message_id == message_id)
                        .values(last_read_message_id=None)
                    )
                    await db.execute(update_stmt)

                    # Now we can safely delete the message
                    await db.delete(message)
                    await db.commit()
                    return True
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Error deleting message {message_id}: {e}")
                    return False
            else:
                # First time deleting for me
                message.content = "Deleted for me"
                message.message_type = "system"

                try:
                    await db.commit()
                    return True
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Error updating message {message_id}: {e}")
                    return False


class ParticipantCRUD:
    """CRUD operations for conversation participants"""

    @staticmethod
    async def get_participant(
        db: AsyncSession, conversation_id: int, user_id: int
    ) -> Optional[ConversationParticipant]:
        """Get participant record"""
        query = select(ConversationParticipant).where(
            and_(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_online_status(
        db: AsyncSession, conversation_id: int, user_id: int, is_online: bool
    ):
        """Update user's online status in conversation"""
        timestamp = datetime.utcnow() if not is_online else None

        await db.execute(
            update(ConversationParticipant)
            .where(
                and_(
                    ConversationParticipant.conversation_id == conversation_id,
                    ConversationParticipant.user_id == user_id
                )
            )
            .values(
                is_online=is_online,
                last_seen_at=timestamp if not is_online else ConversationParticipant.last_seen_at
            )
        )
        await db.commit()

    @staticmethod
    async def increment_unread_count(
        db: AsyncSession, conversation_id: int, exclude_user_id: int
    ):
        """Increment unread count for all participants except sender"""
        await db.execute(
            update(ConversationParticipant)
            .where(
                and_(
                    ConversationParticipant.conversation_id == conversation_id,
                    ConversationParticipant.user_id != exclude_user_id
                )
            )
            .values(
                unread_count=ConversationParticipant.unread_count + 1
            )
        )

    @staticmethod
    async def mark_messages_as_read(
        db: AsyncSession, conversation_id: int, user_id: int, last_message_id: int
    ):
        """Mark messages as read and reset unread count"""
        await db.execute(
            update(ConversationParticipant)
            .where(
                and_(
                    ConversationParticipant.conversation_id == conversation_id,
                    ConversationParticipant.user_id == user_id
                )
            )
            .values(
                last_read_message_id=last_message_id,
                unread_count=0
            )
        )
        await db.commit()

    @staticmethod
    async def get_unread_count(
        db: AsyncSession, conversation_id: int, user_id: int
    ) -> int:
        """Get unread message count for user in conversation"""
        query = select(ConversationParticipant.unread_count).where(
            and_(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id
            )
        )
        result = await db.execute(query)
        count = result.scalar_one_or_none()
        return count or 0