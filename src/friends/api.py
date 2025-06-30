from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..auth.models import User as UserModel
from ..database import get_async_db
from . import schemas
from .service import FriendsService

router = APIRouter()


@router.get("/", response_model=schemas.FriendsListResponse, summary="Get User's Friends")
async def get_friends(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get the current user's friends list.
    """
    friends = await FriendsService.get_user_friends(db, current_user.id)

    return schemas.FriendsListResponse(
        friends=friends,
        count=len(friends)
    )


@router.get("/requests", response_model=schemas.FriendRequestsResponse, summary="Get Friend Requests")
async def get_friend_requests(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get incoming and outgoing friend requests for the current user.
    """
    incoming, outgoing = await FriendsService.get_friend_requests(db, current_user.id)

    return schemas.FriendRequestsResponse(
        incoming_requests=incoming,
        outgoing_requests=outgoing,
        incoming_count=len(incoming),
        outgoing_count=len(outgoing)
    )


@router.post("/request/{user_id}", response_model=schemas.FriendRequestActionResponse, summary="Send Friend Request")
async def send_friend_request(
    user_id: int,
    request_data: schemas.FriendRequestCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Send a friend request to another user.
    """
    friend_request = await FriendsService.send_friend_request(
        db, current_user.id, user_id, request_data.message
    )

    return schemas.FriendRequestActionResponse(
        success=True,
        message="Friend request sent successfully",
        request=friend_request
    )


@router.post("/request/{request_id}/accept", response_model=schemas.FriendRequestActionResponse, summary="Accept Friend Request")
async def accept_friend_request(
    request_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Accept a friend request.
    """
    friend_request, friendship = await FriendsService.accept_friend_request(
        db, request_id, current_user.id
    )

    return schemas.FriendRequestActionResponse(
        success=True,
        message="Friend request accepted successfully",
        request=friend_request
    )


@router.post("/request/{request_id}/decline", response_model=schemas.FriendRequestActionResponse, summary="Decline Friend Request")
async def decline_friend_request(
    request_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Decline a friend request.
    """
    friend_request = await FriendsService.decline_friend_request(
        db, request_id, current_user.id
    )

    return schemas.FriendRequestActionResponse(
        success=True,
        message="Friend request declined",
        request=friend_request
    )


@router.post("/request/{request_id}/cancel", response_model=schemas.FriendRequestActionResponse, summary="Cancel Friend Request")
async def cancel_friend_request(
    request_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Cancel a friend request.
    """
    friend_request = await FriendsService.cancel_friend_request(
        db, request_id, current_user.id
    )

    return schemas.FriendRequestActionResponse(
        success=True,
        message="Friend request cancelled",
        request=friend_request
    )


@router.delete("/{friend_id}", response_model=schemas.FriendActionResponse, summary="Remove Friend")
async def remove_friend(
    friend_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Remove a friend from the user's friends list.
    """
    success = await FriendsService.remove_friend(db, current_user.id, friend_id)

    return schemas.FriendActionResponse(
        success=success,
        message="Friend removed successfully"
    )


# MARK: - Close Friends Endpoints

@router.get("/close-friends", response_model=schemas.CloseFriendsResponse, summary="Get Close Friends")
async def get_close_friends(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get the current user's close friends list.
    """
    close_friends = await FriendsService.get_close_friends(db, current_user.id)

    return schemas.CloseFriendsResponse(
        close_friends=close_friends,
        count=len(close_friends)
    )


@router.post("/close-friends", response_model=schemas.CloseFriendActionResponse, summary="Update Close Friend")
async def update_close_friend(
    request_data: schemas.CloseFriendCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Add or remove someone from close friends list.
    """
    if request_data.is_close_friend:
        # Add to close friends
        close_friend = await FriendsService.add_close_friend(
            db, current_user.id, request_data.friend_id
        )

        if not close_friend:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add non-friend as close friend"
            )

        return schemas.CloseFriendActionResponse(
            success=True,
            message="Added to close friends",
            close_friend=close_friend
        )
    else:
        # Remove from close friends
        success = await FriendsService.remove_close_friend(
            db, current_user.id, request_data.friend_id
        )

        return schemas.CloseFriendActionResponse(
            success=success,
            message="Removed from close friends" if success else "Not in close friends"
        )


@router.get("/close-friends/{friend_id}/check", summary="Check Close Friend Status")
async def check_close_friend_status(
    friend_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Check if a specific friend is in the close friends list.
    """
    is_close_friend = await FriendsService.is_close_friend(db, current_user.id, friend_id)

    return {
        "friend_id": friend_id,
        "is_close_friend": is_close_friend
    }


@router.get("/search", response_model=schemas.UserSearchResponse, summary="Search Users")
async def search_users(
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    limit: int = Query(20, le=50, description="Maximum number of results"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Search users by username. Returns users excluding the current user.
    """
    users = await FriendsService.search_users(db, q, current_user.id, limit)

    return schemas.UserSearchResponse(
        users=users,
        count=len(users),
        query=q
    )


@router.get("/user/{user_id}/profile", response_model=schemas.UserBasic, summary="Get User Profile")
async def get_user_profile(
    user_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get another user's public profile information.
    """
    user, friendship_status = await FriendsService.get_user_profile(
        db, user_id, current_user.id
    )

    # Convert to UserBasic schema and add friendship status as metadata
    user_profile = schemas.UserBasic.from_orm(user)

    # You could add the friendship status to the response if needed
    # For now, we'll return just the user profile
    return user_profile


@router.get("/user/{user_id}/friendship-status", summary="Get Friendship Status")
async def get_friendship_status(
    user_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get the friendship status between current user and another user.
    Returns: none, friends, request_sent, request_received
    """
    from .crud import UserSearchCRUD

    # Validate user exists
    user = await UserSearchCRUD.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    friendship_status = await UserSearchCRUD.get_friendship_status(
        db, current_user.id, user_id
    )

    return {
        "user_id": user_id,
        "friendship_status": friendship_status
    }