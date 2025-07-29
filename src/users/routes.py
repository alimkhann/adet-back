from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timezone
import logging

from ..database import get_async_db
from ..auth.dependencies import get_current_user
from ..models.user import User
from ..models.post import Post
from ..models.friendship import Friendship
from ..models.friend_request import FriendRequest
from ..schemas.user import UserResponse, UserUpdateRequest, UsernameUpdateRequest
from ..schemas.batch import UserDataBatch

router = APIRouter()
logger = logging.getLogger(__name__)

# ... existing code ...

@router.get("/me/batch", response_model=UserDataBatch)
async def get_user_data_batch(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get user data, post count, friend count, and pending friend requests in a single request.
    This reduces multiple API calls to improve performance.
    """
    try:
        # Get user data
        user_data = UserResponse.from_orm(current_user)

        # Get post count
        post_count_result = await db.execute(
            select(func.count(Post.id)).where(Post.user_id == current_user.id)
        )
        post_count = post_count_result.scalar() or 0

        # Get friend count
        friend_count_result = await db.execute(
            select(func.count(Friendship.id)).where(
                Friendship.user_id == current_user.id,
                Friendship.status == "active"
            )
        )
        friend_count = friend_count_result.scalar() or 0

        # Get pending friend requests count
        pending_requests_result = await db.execute(
            select(func.count(FriendRequest.id)).where(
                FriendRequest.receiver_id == current_user.id,
                FriendRequest.status == "pending"
            )
        )
        pending_requests = pending_requests_result.scalar() or 0

        return UserDataBatch(
            user=user_data,
            postCount=post_count,
            friendCount=friend_count,
            pendingFriendRequests=pending_requests
        )

    except Exception as e:
        logger.error(f"Error fetching user data batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user data batch"
        )