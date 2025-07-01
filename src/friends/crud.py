from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from .models import Friendship, FriendRequest, CloseFriend
from ..auth.models import User as UserModel
from ..services.redis_service import redis_service


class FriendshipCRUD:
    """CRUD operations for friendships"""

    @staticmethod
    async def get_user_friends(db: AsyncSession, user_id: int) -> List[Friendship]:
        """Get all friends for a user"""
        result = await db.execute(
            select(Friendship)
            .where(and_(Friendship.user_id == user_id, Friendship.status == "active"))
            .options(selectinload(Friendship.friend))
            .order_by(Friendship.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_friendship(db: AsyncSession, user_id: int, friend_id: int) -> Optional[Friendship]:
        """Get specific friendship between two users"""
        result = await db.execute(
            select(Friendship)
            .where(and_(
                Friendship.user_id == user_id,
                Friendship.friend_id == friend_id
            ))
        )
        return result.scalars().first()

    @staticmethod
    async def create_friendship(db: AsyncSession, user_id: int, friend_id: int) -> Friendship:
        """Create a bidirectional friendship"""
        # Create friendship from user to friend
        friendship1 = Friendship(user_id=user_id, friend_id=friend_id, status="active")
        # Create friendship from friend to user
        friendship2 = Friendship(user_id=friend_id, friend_id=user_id, status="active")

        db.add(friendship1)
        db.add(friendship2)
        await db.commit()
        await db.refresh(friendship1)
        await db.refresh(friendship2)

        return friendship1

    @staticmethod
    async def delete_friendship(db: AsyncSession, user_id: int, friend_id: int) -> bool:
        """Delete a bidirectional friendship"""
        # Delete both directions of the friendship
        result1 = await db.execute(
            select(Friendship)
            .where(and_(
                Friendship.user_id == user_id,
                Friendship.friend_id == friend_id
            ))
        )
        friendship1 = result1.scalars().first()

        result2 = await db.execute(
            select(Friendship)
            .where(and_(
                Friendship.user_id == friend_id,
                Friendship.friend_id == user_id
            ))
        )
        friendship2 = result2.scalars().first()

        deleted = False
        if friendship1:
            await db.delete(friendship1)
            deleted = True

        if friendship2:
            await db.delete(friendship2)
            deleted = True

        if deleted:
            await db.commit()

        return deleted

    @staticmethod
    async def are_friends(db: AsyncSession, user_id: int, friend_id: int) -> bool:
        """Check if two users are friends"""
        result = await db.execute(
            select(Friendship)
            .where(and_(
                Friendship.user_id == user_id,
                Friendship.friend_id == friend_id,
                Friendship.status == "active"
            ))
        )
        return result.scalars().first() is not None


class FriendRequestCRUD:
    """CRUD operations for friend requests"""

    @staticmethod
    async def get_incoming_requests(db: AsyncSession, user_id: int) -> List[FriendRequest]:
        """Get incoming friend requests for a user"""
        result = await db.execute(
            select(FriendRequest)
            .where(and_(
                FriendRequest.receiver_id == user_id,
                FriendRequest.status == "pending"
            ))
            .options(selectinload(FriendRequest.sender))
            .order_by(FriendRequest.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_outgoing_requests(db: AsyncSession, user_id: int) -> List[FriendRequest]:
        """Get outgoing friend requests for a user"""
        result = await db.execute(
            select(FriendRequest)
            .where(and_(
                FriendRequest.sender_id == user_id,
                FriendRequest.status == "pending"
            ))
            .options(selectinload(FriendRequest.receiver))
            .order_by(FriendRequest.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_request_by_id(db: AsyncSession, request_id: int) -> Optional[FriendRequest]:
        """Get a friend request by ID"""
        result = await db.execute(
            select(FriendRequest)
            .where(FriendRequest.id == request_id)
            .options(selectinload(FriendRequest.sender), selectinload(FriendRequest.receiver))
        )
        return result.scalars().first()

    @staticmethod
    async def get_existing_request(db: AsyncSession, sender_id: int, receiver_id: int) -> Optional[FriendRequest]:
        """Check if a friend request already exists between two users"""
        result = await db.execute(
            select(FriendRequest)
            .where(and_(
                FriendRequest.sender_id == sender_id,
                FriendRequest.receiver_id == receiver_id,
                FriendRequest.status == "pending"
            ))
        )
        return result.scalars().first()

    @staticmethod
    async def create_friend_request(
        db: AsyncSession,
        sender_id: int,
        receiver_id: int,
        message: Optional[str] = None
    ) -> FriendRequest:
        """Create a new friend request"""
        expires_at = datetime.utcnow() + timedelta(days=30)  # Requests expire after 30 days

        friend_request = FriendRequest(
            sender_id=sender_id,
            receiver_id=receiver_id,
            status="pending",
            message=message,
            expires_at=expires_at
        )

        db.add(friend_request)
        await db.commit()
        await db.refresh(friend_request)

        return friend_request

    @staticmethod
    async def update_request_status(
        db: AsyncSession,
        request_id: int,
        status: str
    ) -> Optional[FriendRequest]:
        """Update the status of a friend request"""
        result = await db.execute(
            select(FriendRequest)
            .where(FriendRequest.id == request_id)
        )
        friend_request = result.scalars().first()

        if friend_request:
            friend_request.status = status
            friend_request.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(friend_request)

        return friend_request

    @staticmethod
    async def delete_request(db: AsyncSession, request_id: int) -> bool:
        """Delete a friend request"""
        result = await db.execute(
            select(FriendRequest)
            .where(FriendRequest.id == request_id)
        )
        friend_request = result.scalars().first()

        if friend_request:
            await db.delete(friend_request)
            await db.commit()
            return True

        return False


class CloseFriendCRUD:
    """CRUD operations for close friends"""

    @staticmethod
    async def get_close_friends(db: AsyncSession, user_id: int) -> List[UserModel]:
        """Get close friends for a user with caching"""
        # Try to get from cache first
        cached_friends = redis_service.get_cached_close_friends(user_id)
        if cached_friends is not None:
            # Get user details for cached IDs
            result = await db.execute(
                select(UserModel)
                .where(UserModel.id.in_(cached_friends))
                .order_by(UserModel.username)
            )
            return result.scalars().all()

        # Get from database
        result = await db.execute(
            select(CloseFriend)
            .where(CloseFriend.user_id == user_id)
            .options(selectinload(CloseFriend.close_friend))
            .order_by(CloseFriend.created_at.desc())
        )
        close_friends = result.scalars().all()

        # Extract user objects and IDs for caching
        user_objects = [cf.close_friend for cf in close_friends]
        user_ids = [cf.close_friend_id for cf in close_friends]

        # Cache the IDs
        redis_service.cache_close_friends(user_id, user_ids)

        return user_objects

    @staticmethod
    async def is_close_friend(db: AsyncSession, user_id: int, friend_id: int) -> bool:
        """Check if someone is a close friend"""
        # Try cache first
        cached_friends = redis_service.get_cached_close_friends(user_id)
        if cached_friends is not None:
            return friend_id in cached_friends

        # Check database
        result = await db.execute(
            select(CloseFriend)
            .where(and_(
                CloseFriend.user_id == user_id,
                CloseFriend.close_friend_id == friend_id
            ))
        )
        return result.scalars().first() is not None

    @staticmethod
    async def add_close_friend(db: AsyncSession, user_id: int, friend_id: int) -> Optional[CloseFriend]:
        """Add someone as a close friend"""
        # Check if they are actually friends first
        are_friends = await FriendshipCRUD.are_friends(db, user_id, friend_id)
        if not are_friends:
            return None

        # Check if already close friend
        is_already_close = await CloseFriendCRUD.is_close_friend(db, user_id, friend_id)
        if is_already_close:
            # Return existing relationship
            result = await db.execute(
                select(CloseFriend)
                .where(and_(
                    CloseFriend.user_id == user_id,
                    CloseFriend.close_friend_id == friend_id
                ))
                .options(selectinload(CloseFriend.close_friend))
            )
            return result.scalars().first()

        # Create new close friend relationship
        close_friend = CloseFriend(
            user_id=user_id,
            close_friend_id=friend_id
        )

        db.add(close_friend)
        await db.commit()
        await db.refresh(close_friend)

        # Invalidate cache
        redis_service.invalidate_close_friends_cache(user_id)

        return close_friend

    @staticmethod
    async def remove_close_friend(db: AsyncSession, user_id: int, friend_id: int) -> bool:
        """Remove someone from close friends"""
        result = await db.execute(
            select(CloseFriend)
            .where(and_(
                CloseFriend.user_id == user_id,
                CloseFriend.close_friend_id == friend_id
            ))
        )
        close_friend = result.scalars().first()

        if close_friend:
            await db.delete(close_friend)
            await db.commit()

            # Invalidate cache
            redis_service.invalidate_close_friends_cache(user_id)
            return True

        return False

    @staticmethod
    async def get_close_friends_count(db: AsyncSession, user_id: int) -> int:
        """Get count of close friends for a user"""
        # Try cache first
        cached_friends = redis_service.get_cached_close_friends(user_id)
        if cached_friends is not None:
            return len(cached_friends)

        # Count from database
        result = await db.execute(
            select(CloseFriend)
            .where(CloseFriend.user_id == user_id)
        )
        return len(result.scalars().all())


class UserSearchCRUD:
    """CRUD operations for user search"""

    @staticmethod
    async def search_users_by_username(
        db: AsyncSession,
        query: str,
        current_user_id: int,
        limit: int = 20
    ) -> List[UserModel]:
        """Search users by username"""
        result = await db.execute(
            select(UserModel)
            .where(and_(
                UserModel.username.ilike(f"%{query}%"),
                UserModel.id != current_user_id,  # Exclude current user
                UserModel.is_active == True
            ))
            .limit(limit)
            .order_by(UserModel.username)
        )
        return result.scalars().all()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[UserModel]:
        """Get user by ID for profile viewing"""
        result = await db.execute(
            select(UserModel)
            .where(and_(
                UserModel.id == user_id,
                UserModel.is_active == True
            ))
        )
        return result.scalars().first()

    @staticmethod
    async def get_friendship_status(
        db: AsyncSession,
        current_user_id: int,
        target_user_id: int
    ) -> str:
        """Get friendship status between two users"""
        # Check if they are friends
        friendship = await FriendshipCRUD.are_friends(db, current_user_id, target_user_id)
        if friendship:
            return "friends"

        # Check for pending request (either direction)
        outgoing_request = await FriendRequestCRUD.get_existing_request(
            db, current_user_id, target_user_id
        )
        if outgoing_request:
            return "request_sent"

        incoming_request = await FriendRequestCRUD.get_existing_request(
            db, target_user_id, current_user_id
        )
        if incoming_request:
            return "request_received"

        return "none"
