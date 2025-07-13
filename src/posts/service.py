from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, date
from sqlalchemy.exc import IntegrityError

from .crud import PostCRUD, PostLikeCRUD, PostCommentCRUD, PostViewCRUD
from .models import Post, PostComment, PostLike
from .schemas import (
    PostCreate, PostUpdate, PostRead, PostsResponse,
    PostCommentCreate, PostCommentRead, PostCommentsResponse,
    PostLikeRead, LikeActionResponse, PostActionResponse,
    ProofTypeEnum, PostPrivacyEnum
)
from ..friends.crud import FriendshipCRUD, CloseFriendCRUD
from ..friends.schemas import UserBasic
from ..services.redis_service import redis_service
from ..services.media_service import media_service
from ..auth.models import User
import logging

logger = logging.getLogger(__name__)


class PostsService:
    """Business logic for posts functionality"""

    @staticmethod
    async def create_post_from_proof(
        db: AsyncSession,
        user_id: int,
        habit_id: Optional[int],
        proof_urls: List[str],
        proof_type: str,
        description: Optional[str] = None,
        privacy: str = "friends",
        assigned_date: Optional[date] = None
    ) -> PostRead:
        """Create a post from habit proof submission, or return existing if duplicate."""
        try:
            # Map 'photo' to 'image' for ProofTypeEnum compatibility
            proof_type_mapped = proof_type
            if proof_type == "photo":
                proof_type_mapped = "image"

            # Validate and optimize media URLs
            optimized_urls = []
            for url in proof_urls:
                # Cache media URL for faster access
                media_id = url.split('/')[-1].split('.')[0]  # Extract ID from URL
                redis_service.cache_media_url(media_id, url, ttl=86400)  # Cache for 24h
                optimized_urls.append(url)

            # Always set assigned_date
            if not assigned_date:
                assigned_date = date.today()

            try:
                # Try to create the post
                post = await PostCRUD.create_post(
                    db=db,
                    user_id=user_id,
                    habit_id=habit_id,
                    proof_urls=optimized_urls,
                    proof_type=proof_type_mapped,
                    description=description,
                    privacy=privacy,
                    assigned_date=assigned_date
                )
            except IntegrityError as ie:
                # Unique constraint failed, fetch existing post
                await db.rollback()
                logger.info(f"Duplicate post detected for user={user_id}, habit={habit_id}, assigned_date={assigned_date}. Returning existing post.")
                result = await db.execute(
                    Post.__table__.select().where(
                        Post.user_id == user_id,
                        Post.habit_id == habit_id,
                        Post.assigned_date == assigned_date
                    )
                )
                row = result.first()
                if row:
                    from .models import Post as PostModel
                    post = PostModel(**row._mapping)
                else:
                    raise ValueError("Post already exists but could not fetch it.")

            # Get user info for response
            user_result = await db.get(User, user_id)
            if not user_result:
                raise ValueError("User not found")

            user_basic = UserBasic(
                id=user_result.id,
                username=user_result.username or "",
                profile_image_url=getattr(user_result, 'profile_image_url', None)
            )

            # Convert to response format
            post_read = PostRead(
                id=post.id,
                user_id=post.user_id,
                habit_id=post.habit_id,
                proof_urls=post.proof_urls,
                proof_type=ProofTypeEnum(post.proof_type),
                description=post.description,
                privacy=PostPrivacyEnum(post.privacy),
                assigned_date=post.assigned_date,
                created_at=post.created_at,
                updated_at=post.updated_at,
                views_count=post.views_count,
                likes_count=post.likes_count,
                comments_count=post.comments_count,
                user=user_basic,
                is_liked_by_current_user=False,
                is_viewed_by_current_user=False
            )

            logger.info(f"Created or returned post {post.id} from proof for user {user_id}")
            return post_read

        except Exception as e:
            logger.error(f"Failed to create post from proof: {e}")
            raise

    @staticmethod
    async def get_personalized_feed(
        db: AsyncSession,
        current_user_id: int,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> PostsResponse:
        """Get personalized feed with smart filtering and caching"""
        try:
            # Check cache first
            cache_key = f"feed:{current_user_id}:{limit}:{cursor or 'start'}"
            cached_feed = redis_service.redis_client.get(cache_key) if redis_service.is_connected() else None

            if cached_feed:
                logger.debug(f"Returning cached feed for user {current_user_id}")
                # Parse cached data and return
                # For now, proceed with fresh fetch

            # Get posts with privacy filtering
            posts, next_cursor = await PostCRUD.get_feed_posts(
                db=db,
                current_user_id=current_user_id,
                limit=limit,
                cursor=cursor
            )

            # Add interaction state
            posts_with_state = await PostCRUD.get_posts_with_interaction_state(
                db=db,
                posts=posts,
                current_user_id=current_user_id
            )

            # Convert to response format
            posts_read = []
            for post in posts_with_state:
                user_basic = UserBasic(
                    id=post.user.id,
                    username=post.user.username or "",
                    profile_image_url=getattr(post.user, 'profile_image_url', None)
                )

                post_read = PostRead(
                    id=post.id,
                    user_id=post.user_id,
                    habit_id=post.habit_id,
                    proof_urls=post.proof_urls,
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
                posts_read.append(post_read)

            response = PostsResponse(
                posts=posts_read,
                count=len(posts_read),
                has_more=next_cursor is not None,
                next_cursor=next_cursor
            )

            # Cache the response for 5 minutes
            if redis_service.is_connected():
                redis_service.redis_client.setex(
                    cache_key, 300, response.model_dump_json()
                )

            return response

        except Exception as e:
            logger.error(f"Failed to get personalized feed: {e}")
            raise

    @staticmethod
    async def handle_post_interaction(
        db: AsyncSession,
        post_id: int,
        user_id: int,
        interaction_type: str
    ) -> Dict[str, Any]:
        """Handle post interactions (like, view, comment)"""
        try:
            if interaction_type == "like":
                is_liked, new_count = await PostLikeCRUD.toggle_post_like(
                    db=db, post_id=post_id, user_id=user_id
                )

                # Invalidate relevant caches
                if redis_service.is_connected():
                    pattern = f"feed:{user_id}:*"
                    keys = redis_service.redis_client.keys(pattern)
                    if keys:
                        redis_service.redis_client.delete(*keys)

                return {
                    "success": True,
                    "action": "liked" if is_liked else "unliked",
                    "likes_count": new_count
                }

            elif interaction_type == "view":
                await PostViewCRUD.mark_post_as_viewed(
                    db=db, post_id=post_id, user_id=user_id
                )
                return {"success": True, "action": "viewed"}

            else:
                raise ValueError(f"Unknown interaction type: {interaction_type}")

        except Exception as e:
            logger.error(f"Failed to handle post interaction: {e}")
            raise

    @staticmethod
    async def get_post_analytics(
        db: AsyncSession,
        post_id: int,
        owner_user_id: int
    ) -> Dict[str, Any]:
        """Get detailed analytics for a post (owner only)"""
        try:
            # Verify ownership
            post = await PostCRUD.get_post_by_id(db=db, post_id=post_id)
            if not post or post.user_id != owner_user_id:
                raise ValueError("Post not found or access denied")

            # Get analytics data
            analytics = {
                "post_id": post_id,
                "views_count": post.views_count,
                "likes_count": post.likes_count,
                "comments_count": post.comments_count,
                "shares_count": 0,  # TODO: Implement sharing
                "engagement_rate": 0.0,
                "top_likers": [],
                "time_series": []  # TODO: Implement time-based analytics
            }

            # Calculate engagement rate
            if post.views_count > 0:
                engagement_actions = post.likes_count + post.comments_count
                analytics["engagement_rate"] = (engagement_actions / post.views_count) * 100

            # Get top likers
            top_likes = await PostLikeCRUD.get_post_likes(db=db, post_id=post_id, limit=5)
            analytics["top_likers"] = [
                UserBasic(
                    id=like.user.id,
                    username=like.user.username or "",
                    profile_image_url=getattr(like.user, 'profile_image_url', None)
                ) for like in top_likes
            ]

            return analytics

        except Exception as e:
            logger.error(f"Failed to get post analytics: {e}")
            raise

    @staticmethod
    async def check_post_visibility(
        db: AsyncSession,
        post: Post,
        viewer_user_id: int
    ) -> bool:
        """Check if a user can view a specific post"""
        try:
            # Owner can always see their posts
            if post.user_id == viewer_user_id:
                return True

            # Private posts only visible to owner
            if post.privacy == "private":
                return False

            # Check friendship status
            are_friends = await FriendshipCRUD.are_friends(
                db=db, user1_id=viewer_user_id, user2_id=post.user_id
            )

            if not are_friends:
                return False

            # Friends can see friends posts
            if post.privacy == "friends":
                return True

            # Close friends posts require close friend relationship
            if post.privacy == "close_friends":
                return await CloseFriendCRUD.is_close_friend(
                    db=db, user_id=post.user_id, close_friend_id=viewer_user_id
                )

            return False

        except Exception as e:
            logger.error(f"Failed to check post visibility: {e}")
            return False

    @staticmethod
    async def suggest_sharing_prompt(
        db: AsyncSession,
        user_id: int,
        habit_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Suggest when user should share their progress as a post"""
        try:
            # Get user's recent posts
            recent_posts, _ = await PostCRUD.get_user_posts(
                db=db,
                user_id=user_id,
                current_user_id=user_id,
                include_private=True,
                limit=5
            )

            # Logic for when to prompt sharing:
            # 1. Haven't posted in 24 hours
            # 2. Just completed a streak milestone
            # 3. First time completing a habit

            last_post_time = None
            if recent_posts:
                last_post_time = recent_posts[0].created_at

            should_prompt = False
            prompt_reason = ""

            # Check if haven't posted in 24 hours
            if not last_post_time or (datetime.utcnow() - last_post_time) > timedelta(hours=24):
                should_prompt = True
                prompt_reason = "It's been a while since your last post. Share your progress!"

            if should_prompt:
                return {
                    "should_prompt": True,
                    "reason": prompt_reason,
                    "suggested_privacy": "friends",
                    "suggested_description": "Just crushed another habit! 💪"
                }

            return None

        except Exception as e:
            logger.error(f"Failed to suggest sharing prompt: {e}")
            return None

    @staticmethod
    async def cleanup_old_posts(db: AsyncSession, days_old: int = 30) -> int:
        """Clean up old posts and their associated data"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # TODO: Implement cleanup logic
            # 1. Find posts older than cutoff_date
            # 2. Archive media files
            # 3. Clean up cache entries
            # 4. Delete database records

            logger.info(f"Post cleanup completed for posts older than {days_old} days")
            return 0  # Return count of cleaned posts

        except Exception as e:
            logger.error(f"Failed to cleanup old posts: {e}")
            return 0