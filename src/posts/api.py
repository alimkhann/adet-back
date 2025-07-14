from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date

from ..database import get_async_db
from ..auth.dependencies import get_current_user
from .crud import PostCRUD, PostLikeCRUD, PostCommentCRUD, PostViewCRUD
from .service import PostsService
from .schemas import (
    PostCreate, PostUpdate, PostRead, PostsResponse,
    PostCommentCreate, PostCommentRead, PostCommentsResponse,
    PostLikeRead, LikeActionResponse, PostActionResponse, CommentActionResponse,
    PostAnalytics, BatchViewRequest, BatchViewResponse,
    ProofTypeEnum, PostPrivacyEnum, PostResponse
)
from ..friends.schemas import UserBasic
import logging
from ..services.file_upload import file_upload_service
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi import status as fastapi_status
import traceback
from src.habits.crud import get_habit, update_habit_streak

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/posts", tags=["posts"])


def _get_proof_urls_with_privacy(post, privacy):
    urls = post.proof_urls or []
    # Always return signed URLs, regardless of privacy
    return [file_upload_service.generate_signed_url(url, container="proof-posts") for url in urls]


async def _create_post_handler(
    post_data: PostCreate,
    db: AsyncSession,
    current_user
):
    """Shared handler for creating posts"""
    try:
        post = await PostCRUD.create_post(
            db=db,
            user_id=current_user.id,
            habit_id=post_data.habit_id,
            proof_urls=post_data.proof_urls,
            proof_type=post_data.proof_type.value,
            description=post_data.description,
            privacy=post_data.privacy.value
        )

        # Convert to response format with user info
        user_basic = UserBasic(
            id=current_user.id,
            username=getattr(current_user, "username", ""),
            profile_image_url=getattr(current_user, "profile_image_url", None)
        )

        privacy = post.privacy
        proof_urls = _get_proof_urls_with_privacy(post, privacy)

        post_read = PostRead(
            id=post.id,
            user_id=post.user_id,
            habit_id=post.habit_id,
            proof_urls=proof_urls,
            proof_type=ProofTypeEnum(post.proof_type),
            description=post.description,
            privacy=PostPrivacyEnum(post.privacy),
            created_at=post.created_at,
            updated_at=post.updated_at,
            views_count=post.views_count,
            likes_count=post.likes_count,
            comments_count=post.comments_count,
            user=user_basic,
            is_liked_by_current_user=False,
            is_viewed_by_current_user=False,
            assigned_date=post.assigned_date
        )

        return PostActionResponse(
            success=True,
            message="Post created successfully",
            post=post_read
        )

    except Exception as e:
        logger.error(f"Error creating post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post"
        )


# Patch: Log incoming POST /api/v1/posts requests
@router.post("/", response_model=PostResponse)
async def create_post(
    post: PostCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
    request: Request = None
):
    if request is not None:
        try:
            body = await request.body()
            logger.info(f"[POSTS] Incoming POST /api/v1/posts payload: {body}")
        except Exception as e:
            logger.error(f"[POSTS] Failed to log request body: {e}")
    # Determine assigned_date
    assigned_date = post.assigned_date or date.today()
    created_post = await PostsService.create_post_from_proof(
        db=db,
        user_id=current_user["id"] if isinstance(current_user, dict) else current_user.id,
        habit_id=post.habit_id,
        proof_urls=post.proof_urls or [],
        proof_type=post.proof_type.value if hasattr(post.proof_type, "value") else str(post.proof_type),
        description=post.description,
        privacy=post.privacy.value if hasattr(post.privacy, "value") else str(post.privacy),
        assigned_date=assigned_date
    )
    return PostResponse(post=created_post)


@router.post("/", response_model=PostActionResponse)
async def create_post_without_slash(
    post_data: PostCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user),
    request: Request = None
):
    if request is not None:
        try:
            body = await request.body()
            logger.info(f"[POSTS] Incoming POST /api/v1/posts payload: {body}")
        except Exception as e:
            logger.error(f"[POSTS] Failed to log request body: {e}")
    assigned_date = post_data.assigned_date or date.today()
    created_post = await PostsService.create_post_from_proof(
        db=db,
        user_id=current_user["id"] if isinstance(current_user, dict) else current_user.id,
        habit_id=post_data.habit_id,
        proof_urls=post_data.proof_urls or [],
        proof_type=post_data.proof_type.value if hasattr(post_data.proof_type, "value") else str(post_data.proof_type),
        description=post_data.description,
        privacy=post_data.privacy.value if hasattr(post_data.privacy, "value") else str(post_data.privacy),
        assigned_date=assigned_date
    )
    return PostActionResponse(success=True, message="Post created successfully", post=created_post)


@router.get("/feed", response_model=PostsResponse)
async def get_feed_posts(
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=50, description="Number of posts to return"),
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Get feed posts (3-day window with friend filtering)"""
    try:
        posts, next_cursor = await PostCRUD.get_feed_posts(
            db=db,
            current_user_id=current_user.id,
            limit=limit,
            cursor=cursor
        )

        # Add interaction state
        posts_with_state = await PostCRUD.get_posts_with_interaction_state(
            db=db,
            posts=posts,
            current_user_id=current_user.id
        )

        # Convert to response format
        posts_read = []
        for post in posts_with_state:
            user_basic = UserBasic(
                id=post.user.id,
                username=post.user.username or "",
                profile_image_url=getattr(post.user, 'profile_image_url', None)
            )

            privacy = post.privacy
            proof_urls = _get_proof_urls_with_privacy(post, privacy)

            post_read = PostRead(
                id=post.id,
                user_id=post.user_id,
                habit_id=post.habit_id,
                proof_urls=proof_urls,
                proof_type=ProofTypeEnum(post.proof_type),
                description=post.description,
                privacy=PostPrivacyEnum(post.privacy),
                created_at=post.created_at,
                updated_at=post.updated_at,
                views_count=post.views_count,
                likes_count=post.likes_count,
                comments_count=post.comments_count,
                user=user_basic,
                is_liked_by_current_user=getattr(post, 'is_liked_by_current_user', False),
                is_viewed_by_current_user=getattr(post, 'is_viewed_by_current_user', False),
                assigned_date=post.assigned_date
            )
            posts_read.append(post_read)

        return PostsResponse(
            posts=posts_read,
            count=len(posts_read),
            has_more=next_cursor is not None,
            next_cursor=next_cursor
        )

    except Exception as e:
        logger.error(f"Error getting feed posts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get feed posts"
        )


@router.get("/me", response_model=PostsResponse)
async def get_my_posts(
    limit: int = Query(20, ge=1, le=50, description="Number of posts to return"),
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Get posts for the authenticated user (profile view)"""
    try:
        posts, next_cursor = await PostCRUD.get_user_posts(
            db=db,
            user_id=current_user.id,
            current_user_id=current_user.id,
            include_private=True,
            limit=limit,
            cursor=cursor
        )

        # Add interaction state
        posts_with_state = await PostCRUD.get_posts_with_interaction_state(
            db=db,
            posts=posts,
            current_user_id=current_user.id
        )

        # Convert to response format
        posts_read = []
        for post in posts_with_state:
            # DEBUG: Print ORM post dict
            logger.info(f"[DEBUG] ORM Post dict: {post.__dict__}")
            user_basic = UserBasic(
                id=post.user.id,
                username=post.user.username or "",
                profile_image_url=getattr(post.user, 'profile_image_url', None)
            )
            privacy = post.privacy
            proof_urls = _get_proof_urls_with_privacy(post, privacy)
            post_read = PostRead(
                id=post.id,
                user_id=post.user_id,
                habit_id=post.habit_id,
                proof_urls=proof_urls,
                proof_type=ProofTypeEnum(post.proof_type),
                description=post.description,
                privacy=PostPrivacyEnum(post.privacy),
                created_at=post.created_at,
                updated_at=post.updated_at,
                views_count=post.views_count,
                likes_count=post.likes_count,
                comments_count=post.comments_count,
                user=user_basic,
                is_liked_by_current_user=getattr(post, 'is_liked_by_current_user', False),
                is_viewed_by_current_user=getattr(post, 'is_viewed_by_current_user', False),
                assigned_date=post.assigned_date  # Explicitly pass assigned_date
            )
            posts_read.append(post_read)

        return PostsResponse(
            posts=posts_read,
            count=len(posts_read),
            has_more=next_cursor is not None,
            next_cursor=next_cursor
        )
    except Exception as e:
        logger.error(f"Error getting my posts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get my posts"
        )


@router.get("/{post_id}", response_model=PostRead)
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Get a specific post by ID"""
    post = await PostCRUD.get_post_by_id(
        db=db,
        post_id=post_id,
        current_user_id=current_user.id
    )

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or access denied"
        )

    # Add interaction state
    posts_with_state = await PostCRUD.get_posts_with_interaction_state(
        db=db,
        posts=[post],
        current_user_id=current_user.id
    )
    post = posts_with_state[0]

    # Convert to response format
    user_basic = UserBasic(
        id=post.user.id,
        username=post.user.username or "",
        profile_image_url=getattr(post.user, 'profile_image_url', None)
    )

    privacy = post.privacy
    proof_urls = _get_proof_urls_with_privacy(post, privacy)

    return PostRead(
        id=post.id,
        user_id=post.user_id,
        habit_id=post.habit_id,
        proof_urls=proof_urls,
        proof_type=ProofTypeEnum(post.proof_type),
        description=post.description,
        privacy=PostPrivacyEnum(post.privacy),
        created_at=post.created_at,
        updated_at=post.updated_at,
        views_count=post.views_count,
        likes_count=post.likes_count,
        comments_count=post.comments_count,
        user=user_basic,
        is_liked_by_current_user=getattr(post, 'is_liked_by_current_user', False),
        is_viewed_by_current_user=getattr(post, 'is_viewed_by_current_user', False)
    )


@router.put("/{post_id}", response_model=PostActionResponse)
async def update_post(
    post_id: int,
    update_data: PostUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Update a post (description and privacy only)"""
    # Fetch the original post
    post = await PostCRUD.get_post_by_id(db, post_id)
    if not post or post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or access denied"
        )

    # Check if privacy is being changed from private to friends/close_friends
    privacy_changing = (
        post.privacy == "private" and
        update_data.privacy.value in ("friends", "close_friends")
    )

    updated_post = await PostCRUD.update_post(
        db=db,
        post_id=post_id,
        user_id=current_user.id,
        description=update_data.description,
        privacy=update_data.privacy.value
    )

    # If privacy is changing, check if streak should be incremented
    if privacy_changing:
        # Check if there is already a shared post for this habit and date
        from .models import Post
        from sqlalchemy import select
        existing_shared = await db.execute(
            select(Post)
            .where(
                Post.user_id == current_user.id,
                Post.habit_id == post.habit_id,
                Post.assigned_date == post.assigned_date,
                Post.privacy.in_(["friends", "close_friends"])
            )
        )
        already_shared = existing_shared.scalars().first()
        if not already_shared:
            # Increment streak for this habit
            habit = await get_habit(db, habit_id=post.habit_id, user_id=current_user.id)
            if habit:
                new_streak = (habit.streak or 0) + 1
                await update_habit_streak(db, habit_id=habit.id, streak_count=new_streak)

    return PostActionResponse(
        success=True,
        message="Post updated successfully"
    )


@router.put("/{post_id}/privacy", response_model=PostActionResponse)
async def update_post_privacy(
    post_id: int,
    privacy_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Update post privacy only"""
    try:
        new_privacy = privacy_data.get("privacy")
        if not new_privacy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Privacy value is required"
            )
        # Validate privacy value
        if new_privacy not in ["only_me", "friends", "close_friends"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid privacy value"
            )
        updated_post = await PostCRUD.update_post(
            db=db,
            post_id=post_id,
            user_id=current_user.id,
            description=None,  # Don't update description
            privacy=new_privacy
        )
        if not updated_post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found or access denied"
            )
        return PostActionResponse(
            success=True,
            message=f"Post privacy updated to {new_privacy}"
        )
    except Exception as e:
        logger.error(f"Error updating post privacy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update post privacy"
        )


@router.post("/{post_id}/like", response_model=LikeActionResponse)
async def toggle_post_like(
    post_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Toggle like on a post"""
    try:
        is_liked, new_count = await PostLikeCRUD.toggle_post_like(
            db=db,
            post_id=post_id,
            user_id=current_user.id
        )

        message = "Post liked" if is_liked else "Post unliked"

        return LikeActionResponse(
            success=True,
            message=message,
            is_liked=is_liked,
            likes_count=new_count
        )

    except Exception as e:
        logger.error(f"Error toggling post like: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle like"
        )


@router.get("/{post_id}/likes", response_model=List[PostLikeRead])
async def get_post_likes(
    post_id: int,
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user)
):
    """Get users who liked a post"""
    likes = await PostLikeCRUD.get_post_likes(
        db=db,
        post_id=post_id,
        limit=limit
    )

    return [
        PostLikeRead(
            id=like.id,
            post_id=like.post_id,
            comment_id=like.comment_id,
            user_id=like.user_id,
            created_at=like.created_at,
            user=UserBasic(
                id=like.user.id,
                username=like.user.username or "",
                profile_image_url=getattr(like.user, 'profile_image_url', None)
            )
        )
        for like in likes
    ]


@router.post("/comments/{comment_id}/like", response_model=LikeActionResponse)
async def toggle_comment_like(
    comment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Toggle like on a comment"""
    try:
        is_liked, new_count = await PostLikeCRUD.toggle_comment_like(
            db=db,
            comment_id=comment_id,
            user_id=current_user.id
        )
        message = "Comment liked" if is_liked else "Comment unliked"
        return LikeActionResponse(
            success=True,
            message=message,
            is_liked=is_liked,
            likes_count=new_count
        )
    except Exception as e:
        logger.error(f"Error toggling comment like: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle comment like"
        )


@router.get("/{post_id}/comments", response_model=PostCommentsResponse)
async def get_post_comments(
    post_id: int,
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_user)
):
    """Get comments for a post"""
    comments, next_cursor = await PostCommentCRUD.get_post_comments(
        db=db,
        post_id=post_id,
        limit=limit,
        cursor=cursor
    )

    # Get liked comment ids for current user
    comment_ids = [comment.id for comment in comments]
    liked_comment_ids = set()
    if comment_ids:
        from .models import PostLike
        from sqlalchemy import select, and_
        likes_result = await db.execute(
            select(PostLike.comment_id)
            .where(and_(
                PostLike.user_id == (current_user["id"] if isinstance(current_user, dict) else current_user.id),
                PostLike.comment_id.in_(comment_ids)
            ))
        )
        liked_comment_ids = set(row[0] for row in likes_result.fetchall())

    comments_read = []
    for comment in comments:
        user_basic = UserBasic(
            id=comment.user.id,
            username=comment.user.username or "",
            profile_image_url=getattr(comment.user, 'profile_image_url', None)
        )

        comment_read = PostCommentRead(
            id=comment.id,
            post_id=comment.post_id,
            user_id=comment.user_id,
            parent_comment_id=comment.parent_comment_id,
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            likes_count=comment.likes_count,
            replies_count=comment.replies_count,
            user=user_basic,
            is_liked_by_current_user=comment.id in liked_comment_ids
        )
        comments_read.append(comment_read)

    return PostCommentsResponse(
        comments=comments_read,
        count=len(comments_read),
        has_more=next_cursor is not None,
        next_cursor=next_cursor
    )


@router.post("/comments", response_model=CommentActionResponse)
async def create_comment(
    comment_data: PostCommentCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Create a new comment"""
    try:
        comment = await PostCommentCRUD.create_comment(
            db=db,
            post_id=comment_data.post_id,
            user_id=current_user.id,
            content=comment_data.content,
            parent_comment_id=comment_data.parent_comment_id
        )

        return CommentActionResponse(
            success=True,
            message="Comment created successfully"
        )

    except Exception as e:
        logger.error(f"Error creating comment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment"
        )


@router.delete("/comments/{comment_id}", response_model=CommentActionResponse)
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Delete a comment (owner only)"""
    try:
        deleted = await PostCommentCRUD.delete_comment(db, comment_id=comment_id, user_id=current_user.id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found or not owned by user"
            )
        return CommentActionResponse(success=True, message="Comment deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting comment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete comment"
        )

@router.post("/comments/{comment_id}/report", response_model=CommentActionResponse)
async def report_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user),
    reason: str = Body(..., embed=True),
    description: Optional[str] = Body(None, embed=True)
):
    """Report a comment for moderation"""
    try:
        reported = await PostCommentCRUD.report_comment(db, comment_id=comment_id, reporter_id=current_user.id, reason=reason, description=description)
        if not reported:
            return CommentActionResponse(success=False, message="You have already reported this comment.")
        return CommentActionResponse(success=True, message="Comment reported successfully.")
    except Exception as e:
        logger.error(f"Error reporting comment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to report comment"
        )


@router.post("/{post_id}/view", response_model=PostActionResponse)
async def mark_post_as_viewed(
    post_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Mark a post as viewed"""
    try:
        await PostViewCRUD.mark_post_as_viewed(
            db=db,
            post_id=post_id,
            user_id=current_user.id
        )

        return PostActionResponse(
            success=True,
            message="Post marked as viewed"
        )

    except Exception as e:
        logger.error(f"Error marking post as viewed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark post as viewed"
        )


@router.post("/batch/view", response_model=BatchViewResponse)
async def batch_mark_as_viewed(
    batch_data: BatchViewRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    """Mark multiple posts as viewed"""
    try:
        processed_count = await PostViewCRUD.batch_mark_as_viewed(
            db=db,
            post_ids=batch_data.post_ids,
            user_id=current_user.id
        )

        failed_count = len(batch_data.post_ids) - processed_count

        return BatchViewResponse(
            success=True,
            message=f"Processed {processed_count} posts",
            processed_count=processed_count,
            failed_count=failed_count
        )

    except Exception as e:
        logger.error(f"Error batch marking posts as viewed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process batch view request"
        )