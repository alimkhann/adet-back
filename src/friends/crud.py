from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from .models import Friendship, FriendRequest, CloseFriend, BlockedUser, UserReport
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
        """Search users by username, excluding blocked users"""
        # Get users blocked by current user
        blocked_by_me_result = await db.execute(
            select(BlockedUser.blocked_id)
            .where(BlockedUser.blocker_id == current_user_id)
        )
        blocked_by_me = [row[0] for row in blocked_by_me_result.all()]

        # Get users who have blocked current user
        blocked_me_result = await db.execute(
            select(BlockedUser.blocker_id)
            .where(BlockedUser.blocked_id == current_user_id)
        )
        blocked_me = [row[0] for row in blocked_me_result.all()]

        # Combine all blocked user IDs
        all_blocked_ids = set(blocked_by_me + blocked_me)

        # Build exclusion list (current user + all blocked users)
        excluded_ids = {current_user_id} | all_blocked_ids

        result = await db.execute(
            select(UserModel)
            .where(and_(
                UserModel.username.ilike(f"%{query}%"),
                ~UserModel.id.in_(excluded_ids),  # Exclude current user and blocked users
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


class BlockedUserCRUD:
    """CRUD operations for blocked users"""

    @staticmethod
    async def block_user(
        db: AsyncSession,
        blocker_id: int,
        blocked_id: int,
        reason: Optional[str] = None
    ) -> BlockedUser:
        """Block a user"""
        # Check if already blocked
        existing_block = await BlockedUserCRUD.is_blocked(db, blocker_id, blocked_id)
        if existing_block:
            return existing_block

        # Create block relationship
        blocked_user = BlockedUser(
            blocker_id=blocker_id,
            blocked_id=blocked_id,
            reason=reason
        )

        db.add(blocked_user)
        await db.commit()
        await db.refresh(blocked_user)

        return blocked_user

    @staticmethod
    async def unblock_user(db: AsyncSession, blocker_id: int, blocked_id: int) -> bool:
        """Unblock a user"""
        result = await db.execute(
            select(BlockedUser)
            .where(and_(
                BlockedUser.blocker_id == blocker_id,
                BlockedUser.blocked_id == blocked_id
            ))
        )
        blocked_user = result.scalars().first()

        if blocked_user:
            await db.delete(blocked_user)
            await db.commit()
            return True

        return False

    @staticmethod
    async def is_blocked(db: AsyncSession, blocker_id: int, blocked_id: int) -> Optional[BlockedUser]:
        """Check if a user is blocked"""
        result = await db.execute(
            select(BlockedUser)
            .where(and_(
                BlockedUser.blocker_id == blocker_id,
                BlockedUser.blocked_id == blocked_id
            ))
        )
        return result.scalars().first()

    @staticmethod
    async def get_blocked_users(db: AsyncSession, user_id: int) -> List[BlockedUser]:
        """Get list of users blocked by a user"""
        result = await db.execute(
            select(BlockedUser)
            .where(BlockedUser.blocker_id == user_id)
            .options(selectinload(BlockedUser.blocked))
            .order_by(BlockedUser.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def is_user_blocked_by_anyone(db: AsyncSession, user_id: int, by_user_id: int) -> bool:
        """Check if user is blocked by another user (bidirectional check)"""
        # Check if by_user_id has blocked user_id
        result = await db.execute(
            select(BlockedUser)
            .where(and_(
                BlockedUser.blocker_id == by_user_id,
                BlockedUser.blocked_id == user_id
            ))
        )
        blocked_by_other = result.scalars().first() is not None

        # Check if user_id has blocked by_user_id
        result = await db.execute(
            select(BlockedUser)
            .where(and_(
                BlockedUser.blocker_id == user_id,
                BlockedUser.blocked_id == by_user_id
            ))
        )
        blocked_by_self = result.scalars().first() is not None

        return blocked_by_other or blocked_by_self


class UserReportCRUD:
    """CRUD operations for user reports"""

    @staticmethod
    async def create_report(
        db: AsyncSession,
        reporter_id: int,
        reported_id: int,
        category: str,
        description: Optional[str] = None
    ) -> UserReport:
        """Create a user report"""
        report = UserReport(
            reporter_id=reporter_id,
            reported_id=reported_id,
            category=category,
            description=description,
            status="pending"
        )

        db.add(report)
        await db.commit()
        await db.refresh(report)

        return report

    @staticmethod
    async def get_reports_by_reported_user(
        db: AsyncSession,
        reported_id: int,
        limit: int = 50
    ) -> List[UserReport]:
        """Get all reports for a specific reported user"""
        result = await db.execute(
            select(UserReport)
            .where(UserReport.reported_id == reported_id)
            .options(selectinload(UserReport.reporter))
            .order_by(UserReport.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_reports_by_status(
        db: AsyncSession,
        status: str,
        limit: int = 100
    ) -> List[UserReport]:
        """Get reports by status (for admin review)"""
        result = await db.execute(
            select(UserReport)
            .where(UserReport.status == status)
            .options(
                selectinload(UserReport.reporter),
                selectinload(UserReport.reported)
            )
            .order_by(UserReport.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def update_report_status(
        db: AsyncSession,
        report_id: int,
        status: str,
        reviewed_by: Optional[int] = None
    ) -> Optional[UserReport]:
        """Update report status"""
        result = await db.execute(
            select(UserReport)
            .where(UserReport.id == report_id)
        )
        report = result.scalars().first()

        if report:
            report.status = status
            report.updated_at = datetime.utcnow()
            if reviewed_by:
                report.reviewed_by = reviewed_by
                report.reviewed_at = datetime.utcnow()

            await db.commit()
            await db.refresh(report)

        return report

    @staticmethod
    async def get_report_by_id(db: AsyncSession, report_id: int) -> Optional[UserReport]:
        """Get a specific report by ID"""
        result = await db.execute(
            select(UserReport)
            .where(UserReport.id == report_id)
            .options(
                selectinload(UserReport.reporter),
                selectinload(UserReport.reported),
                selectinload(UserReport.reviewer)
            )
        )
        return result.scalars().first()

    @staticmethod
    async def has_user_reported(
        db: AsyncSession,
        reporter_id: int,
        reported_id: int
    ) -> bool:
        """Check if a user has already reported another user"""
        result = await db.execute(
            select(UserReport)
            .where(and_(
                UserReport.reporter_id == reporter_id,
                UserReport.reported_id == reported_id,
                UserReport.status.in_(["pending", "reviewed"])
            ))
        )
        return result.scalars().first() is not None
