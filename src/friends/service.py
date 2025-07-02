"""
Friends service layer containing business logic for friendship operations.
"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from .crud import FriendshipCRUD, FriendRequestCRUD, UserSearchCRUD, CloseFriendCRUD, BlockedUserCRUD, UserReportCRUD
from .models import Friendship, FriendRequest, CloseFriend, BlockedUser, UserReport
from ..auth.models import User as UserModel


class FriendsService:
    """Service layer for friendship operations"""

    @staticmethod
    async def get_user_friends(db: AsyncSession, user_id: int) -> List[Friendship]:
        """Get all friends for a user"""
        return await FriendshipCRUD.get_user_friends(db, user_id)

    @staticmethod
    async def get_friend_requests(
        db: AsyncSession,
        user_id: int
    ) -> Tuple[List[FriendRequest], List[FriendRequest]]:
        """Get incoming and outgoing friend requests for a user"""
        incoming = await FriendRequestCRUD.get_incoming_requests(db, user_id)
        outgoing = await FriendRequestCRUD.get_outgoing_requests(db, user_id)
        return incoming, outgoing

    @staticmethod
    async def send_friend_request(
        db: AsyncSession,
        sender_id: int,
        receiver_id: int,
        message: str = None
    ) -> FriendRequest:
        """Send a friend request"""
        # Validate users exist and are not the same
        if sender_id == receiver_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot send a friend request to yourself"
            )

        # Check if receiver exists
        receiver = await UserSearchCRUD.get_user_by_id(db, receiver_id)
        if not receiver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if they are already friends
        are_friends = await FriendshipCRUD.are_friends(db, sender_id, receiver_id)
        if are_friends:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already friends with this user"
            )

        # Check if request already exists (either direction)
        existing_request = await FriendRequestCRUD.get_existing_request(db, sender_id, receiver_id)
        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Friend request already sent"
            )

        reverse_request = await FriendRequestCRUD.get_existing_request(db, receiver_id, sender_id)
        if reverse_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This user has already sent you a friend request"
            )

        # Create the friend request
        return await FriendRequestCRUD.create_friend_request(
            db, sender_id, receiver_id, message
        )

    @staticmethod
    async def accept_friend_request(
        db: AsyncSession,
        request_id: int,
        current_user_id: int
    ) -> Tuple[FriendRequest, Friendship]:
        """Accept a friend request and create friendship"""
        # Get the request
        friend_request = await FriendRequestCRUD.get_request_by_id(db, request_id)
        if not friend_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friend request not found"
            )

        # Verify the current user is the receiver
        if friend_request.receiver_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only accept your own friend requests"
            )

        # Verify the request is still pending
        if friend_request.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This friend request is no longer pending"
            )

        # Update request status to accepted
        friend_request = await FriendRequestCRUD.update_request_status(
            db, request_id, "accepted"
        )

        # Create the friendship
        friendship = await FriendshipCRUD.create_friendship(
            db, friend_request.sender_id, friend_request.receiver_id
        )

        return friend_request, friendship

    @staticmethod
    async def decline_friend_request(
        db: AsyncSession,
        request_id: int,
        current_user_id: int
    ) -> FriendRequest:
        """Decline a friend request"""
        # Get the request
        friend_request = await FriendRequestCRUD.get_request_by_id(db, request_id)
        if not friend_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friend request not found"
            )

        # Verify the current user is the receiver
        if friend_request.receiver_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only decline your own friend requests"
            )

        # Verify the request is still pending
        if friend_request.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This friend request is no longer pending"
            )

        # Delete the request instead of marking it as declined
        await FriendRequestCRUD.delete_request(db, request_id)

        # Return the friend request with declined status for response consistency
        friend_request.status = "declined"
        return friend_request

    @staticmethod
    async def cancel_friend_request(
        db: AsyncSession,
        request_id: int,
        current_user_id: int
    ) -> FriendRequest:
        """Cancel a friend request"""
        # Get the request
        friend_request = await FriendRequestCRUD.get_request_by_id(db, request_id)
        if not friend_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friend request not found"
            )

        # Verify the current user is the sender
        if friend_request.sender_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own friend requests"
            )

        # Verify the request is still pending
        if friend_request.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This friend request is no longer pending"
            )

        # Delete the request instead of marking it as cancelled
        await FriendRequestCRUD.delete_request(db, request_id)

        # Return the friend request with cancelled status for response consistency
        friend_request.status = "cancelled"
        return friend_request

    @staticmethod
    async def remove_friend(
        db: AsyncSession,
        current_user_id: int,
        friend_id: int
    ) -> bool:
        """Remove a friend"""
        # Validate friend exists
        friend = await UserSearchCRUD.get_user_by_id(db, friend_id)
        if not friend:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if they are actually friends
        are_friends = await FriendshipCRUD.are_friends(db, current_user_id, friend_id)
        if not are_friends:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are not friends with this user"
            )

        # Remove from close friends if applicable
        await CloseFriendCRUD.remove_close_friend(db, current_user_id, friend_id)

        # Remove the friendship
        return await FriendshipCRUD.delete_friendship(db, current_user_id, friend_id)

    # MARK: - Close Friends Methods

    @staticmethod
    async def get_close_friends(db: AsyncSession, user_id: int) -> List[UserModel]:
        """Get close friends for a user"""
        return await CloseFriendCRUD.get_close_friends(db, user_id)

    @staticmethod
    async def is_close_friend(db: AsyncSession, user_id: int, friend_id: int) -> bool:
        """Check if someone is a close friend"""
        return await CloseFriendCRUD.is_close_friend(db, user_id, friend_id)

    @staticmethod
    async def add_close_friend(
        db: AsyncSession,
        user_id: int,
        friend_id: int
    ) -> Optional[CloseFriend]:
        """Add someone as a close friend"""
        # Validate friend exists
        friend = await UserSearchCRUD.get_user_by_id(db, friend_id)
        if not friend:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Add as close friend (removed limit check)
        close_friend = await CloseFriendCRUD.add_close_friend(db, user_id, friend_id)
        if not close_friend:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can only add friends as close friends"
            )

        return close_friend

    @staticmethod
    async def remove_close_friend(
        db: AsyncSession,
        user_id: int,
        friend_id: int
    ) -> bool:
        """Remove someone from close friends"""
        return await CloseFriendCRUD.remove_close_friend(db, user_id, friend_id)

    @staticmethod
    async def search_users(
        db: AsyncSession,
        query: str,
        current_user_id: int,
        limit: int = 20
    ) -> List[UserModel]:
        """Search users by username"""
        if not query.strip():
            return []

        # Minimum query length
        if len(query.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query must be at least 2 characters long"
            )

        return await UserSearchCRUD.search_users_by_username(
            db, query.strip(), current_user_id, limit
        )

    @staticmethod
    async def get_user_profile(
        db: AsyncSession,
        user_id: int,
        current_user_id: int
    ) -> Tuple[UserModel, str]:
        """Get user profile with friendship status"""
        # Get the user
        user = await UserSearchCRUD.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get friendship status
        friendship_status = await UserSearchCRUD.get_friendship_status(
            db, current_user_id, user_id
        )

        return user, friendship_status

    @staticmethod
    async def get_friends_count(db: AsyncSession, user_id: int) -> int:
        """Get the count of friends for a user"""
        friends = await FriendshipCRUD.get_user_friends(db, user_id)
        return len(friends)

    # MARK: - Blocking Methods

    @staticmethod
    async def block_user(
        db: AsyncSession,
        blocker_id: int,
        blocked_id: int,
        reason: Optional[str] = None
    ) -> BlockedUser:
        """Block a user and remove any existing relationships"""
        # Validate users exist and are not the same
        if blocker_id == blocked_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot block yourself"
            )

        # Check if user to block exists
        blocked_user_obj = await UserSearchCRUD.get_user_by_id(db, blocked_id)
        if not blocked_user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if already blocked
        existing_block = await BlockedUserCRUD.is_blocked(db, blocker_id, blocked_id)
        if existing_block:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already blocked"
            )

        # Remove any existing friendship
        await FriendshipCRUD.delete_friendship(db, blocker_id, blocked_id)

        # Remove from close friends
        await CloseFriendCRUD.remove_close_friend(db, blocker_id, blocked_id)

        # Cancel any pending friend requests between them
        outgoing_request = await FriendRequestCRUD.get_existing_request(db, blocker_id, blocked_id)
        if outgoing_request:
            await FriendRequestCRUD.delete_request(db, outgoing_request.id)

        incoming_request = await FriendRequestCRUD.get_existing_request(db, blocked_id, blocker_id)
        if incoming_request:
            await FriendRequestCRUD.delete_request(db, incoming_request.id)

        # Create the block
        return await BlockedUserCRUD.block_user(db, blocker_id, blocked_id, reason)

    @staticmethod
    async def unblock_user(
        db: AsyncSession,
        blocker_id: int,
        blocked_id: int
    ) -> bool:
        """Unblock a user"""
        # Validate user to unblock exists
        blocked_user_obj = await UserSearchCRUD.get_user_by_id(db, blocked_id)
        if not blocked_user_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if actually blocked
        existing_block = await BlockedUserCRUD.is_blocked(db, blocker_id, blocked_id)
        if not existing_block:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not blocked"
            )

        return await BlockedUserCRUD.unblock_user(db, blocker_id, blocked_id)

    @staticmethod
    async def get_blocked_users(db: AsyncSession, user_id: int) -> List[BlockedUser]:
        """Get list of users blocked by a user"""
        return await BlockedUserCRUD.get_blocked_users(db, user_id)

    @staticmethod
    async def is_user_blocked(
        db: AsyncSession,
        user_id: int,
        by_user_id: int
    ) -> bool:
        """Check if a user is blocked by another user (bidirectional)"""
        return await BlockedUserCRUD.is_user_blocked_by_anyone(db, user_id, by_user_id)

    # MARK: - Reporting Methods

    @staticmethod
    async def report_user(
        db: AsyncSession,
        reporter_id: int,
        reported_id: int,
        category: str,
        description: Optional[str] = None
    ) -> UserReport:
        """Report a user for inappropriate behavior"""
        # Validate users exist and are not the same
        if reporter_id == reported_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot report yourself"
            )

        # Check if reported user exists
        reported_user = await UserSearchCRUD.get_user_by_id(db, reported_id)
        if not reported_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Validate category
        valid_categories = ["harassment", "spam", "inappropriate_content", "fake_account", "other"]
        if category not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}"
            )

        # Check if user has already reported this user (prevent spam)
        has_reported = await UserReportCRUD.has_user_reported(db, reporter_id, reported_id)
        if has_reported:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reported this user"
            )

        return await UserReportCRUD.create_report(
            db, reporter_id, reported_id, category, description
        )

    @staticmethod
    async def get_user_reports(
        db: AsyncSession,
        reported_id: int,
        limit: int = 50
    ) -> List[UserReport]:
        """Get reports for a specific user (admin only)"""
        return await UserReportCRUD.get_reports_by_reported_user(db, reported_id, limit)

    @staticmethod
    async def get_reports_by_status(
        db: AsyncSession,
        status: str,
        limit: int = 100
    ) -> List[UserReport]:
        """Get reports by status (admin only)"""
        valid_statuses = ["pending", "reviewed", "resolved", "dismissed"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )

        return await UserReportCRUD.get_reports_by_status(db, status, limit)

    @staticmethod
    async def update_report_status(
        db: AsyncSession,
        report_id: int,
        status: str,
        reviewed_by: int
    ) -> Optional[UserReport]:
        """Update report status (admin only)"""
        # Validate report exists
        report = await UserReportCRUD.get_report_by_id(db, report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )

        # Validate status
        valid_statuses = ["reviewed", "resolved", "dismissed"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )

        return await UserReportCRUD.update_report_status(db, report_id, status, reviewed_by)
