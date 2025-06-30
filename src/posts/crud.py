from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, case, text
from sqlalchemy.orm import selectinload, joinedload

from .models import Post, PostComment, PostLike, PostView, PostReport
from ..auth.models import User as UserModel
from ..friends.crud import CloseFriendCRUD, FriendshipCRUD
from ..services.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)


class PostCRUD:
    """CRUD operations for posts with privacy filtering"""

    @staticmethod
    async def create_post(
        db: AsyncSession,
        user_id: int,
        habit_id: Optional[int],
        proof_urls: List[str],
        proof_type: str,
        description: Optional[str],
        privacy: str
    ) -> Post:
        """Create a new post"""
        post = Post(
            user_id=user_id,
            habit_id=habit_id,
            proof_urls=proof_urls,
            proof_type=proof_type,
            description=description,
            privacy=privacy
        )

        db.add(post)
        await db.commit()
        await db.refresh(post)

        logger.info(f"Created post {post.id} for user {user_id}")
        return post

    @staticmethod
    async def get_post_by_id(
        db: AsyncSession,
        post_id: int,
        current_user_id: Optional[int] = None
    ) -> Optional[Post]:
        """Get a post by ID with privacy filtering"""
        result = await db.execute(
            select(Post)
            .where(Post.id == post_id)
            .options(
                selectinload(Post.user),
                selectinload(Post.habit)
            )
        )
        post = result.scalars().first()

        if not post:
            return None

        # Check privacy permissions
        if current_user_id and not await PostCRUD._can_view_post(db, post, current_user_id):
            return None

        return post

    @staticmethod
    async def get_feed_posts(
        db: AsyncSession,
        current_user_id: int,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> Tuple[List[Post], Optional[str]]:
        """Get feed posts (3-day window) with privacy filtering"""
        # 3-day window (BeReal style)
        three_days_ago = datetime.utcnow() - timedelta(days=3)

        # Build query
        query = (
            select(Post)
            .where(Post.created_at >= three_days_ago)
            .options(
                selectinload(Post.user),
                selectinload(Post.habit)
            )
            .order_by(desc(Post.created_at))
            .limit(limit + 1)  # +1 to check if there are more
        )

        # Add cursor filtering
        if cursor:
            try:
                cursor_date = datetime.fromisoformat(cursor)
                query = query.where(Post.created_at < cursor_date)
            except ValueError:
                logger.warning(f"Invalid cursor format: {cursor}")

        result = await db.execute(query)
        all_posts = result.scalars().all()

        # Filter posts based on privacy and friendship
        visible_posts = []
        for post in all_posts[:limit]:  # Only process up to limit
            if await PostCRUD._can_view_post(db, post, current_user_id):
                visible_posts.append(post)

        # Determine next cursor
        next_cursor = None
        if len(all_posts) > limit:
            next_cursor = visible_posts[-1].created_at.isoformat() if visible_posts else None

        return visible_posts, next_cursor

    @staticmethod
    async def get_user_posts(
        db: AsyncSession,
        user_id: int,
        current_user_id: Optional[int] = None,
        include_private: bool = False,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> Tuple[List[Post], Optional[str]]:
        """Get posts for a specific user with privacy filtering"""
        query = (
            select(Post)
            .where(Post.user_id == user_id)
            .options(
                selectinload(Post.user),
                selectinload(Post.habit)
            )
            .order_by(desc(Post.created_at))
            .limit(limit + 1)
        )

        # Add cursor filtering
        if cursor:
            try:
                cursor_date = datetime.fromisoformat(cursor)
                query = query.where(Post.created_at < cursor_date)
            except ValueError:
                logger.warning(f"Invalid cursor format: {cursor}")

        result = await db.execute(query)
        all_posts = result.scalars().all()

        # Filter based on privacy
        visible_posts = []
        for post in all_posts[:limit]:
            if include_private or await PostCRUD._can_view_post(db, post, current_user_id):
                visible_posts.append(post)

        # Determine next cursor
        next_cursor = None
        if len(all_posts) > limit:
            next_cursor = visible_posts[-1].created_at.isoformat() if visible_posts else None

        return visible_posts, next_cursor

    @staticmethod
    async def update_post(
        db: AsyncSession,
        post_id: int,
        user_id: int,
        description: Optional[str] = None,
        privacy: Optional[str] = None
    ) -> Optional[Post]:
        """Update a post (only description and privacy)"""
        result = await db.execute(
            select(Post)
            .where(and_(Post.id == post_id, Post.user_id == user_id))
        )
        post = result.scalars().first()

        if not post:
            return None

        if description is not None:
            post.description = description
        if privacy is not None:
            post.privacy = privacy

        post.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(post)

        return post

    @staticmethod
    async def delete_post(db: AsyncSession, post_id: int, user_id: int) -> bool:
        """Delete a post (owner only)"""
        result = await db.execute(
            select(Post)
            .where(and_(Post.id == post_id, Post.user_id == user_id))
        )
        post = result.scalars().first()

        if not post:
            return False

        await db.delete(post)
        await db.commit()

        logger.info(f"Deleted post {post_id} by user {user_id}")
        return True

    @staticmethod
    async def _can_view_post(db: AsyncSession, post: Post, current_user_id: int) -> bool:
        """Check if current user can view the post based on privacy settings"""
        # Owner can always see their posts
        if post.user_id == current_user_id:
            return True

        # Private posts only visible to owner
        if post.privacy == "private":
            return False

        # Check if users are friends
        are_friends = await FriendshipCRUD.are_friends(db, current_user_id, post.user_id)
        if not are_friends:
            return False

        # Friends can see friends posts
        if post.privacy == "friends":
            return True

        # Close friends posts require close friend relationship
        if post.privacy == "close_friends":
            return await CloseFriendCRUD.is_close_friend(db, post.user_id, current_user_id)

        return False

    @staticmethod
    async def get_posts_with_interaction_state(
        db: AsyncSession,
        posts: List[Post],
        current_user_id: int
    ) -> List[Post]:
        """Add interaction state (liked, viewed) to posts"""
        if not posts:
            return posts

        post_ids = [post.id for post in posts]

        # Get likes
        likes_result = await db.execute(
            select(PostLike.post_id)
            .where(and_(
                PostLike.user_id == current_user_id,
                PostLike.post_id.in_(post_ids)
            ))
        )
        liked_post_ids = set(row[0] for row in likes_result.fetchall())

        # Get views
        views_result = await db.execute(
            select(PostView.post_id)
            .where(and_(
                PostView.user_id == current_user_id,
                PostView.post_id.in_(post_ids)
            ))
        )
        viewed_post_ids = set(row[0] for row in views_result.fetchall())

        # Add interaction state to posts
        for post in posts:
            post.is_liked_by_current_user = post.id in liked_post_ids
            post.is_viewed_by_current_user = post.id in viewed_post_ids

        return posts


class PostLikeCRUD:
    """CRUD operations for post likes"""

    @staticmethod
    async def toggle_post_like(
        db: AsyncSession,
        post_id: int,
        user_id: int
    ) -> Tuple[bool, int]:
        """Toggle like on a post, returns (is_liked, new_count)"""
        # Check if already liked
        existing_like = await db.execute(
            select(PostLike)
            .where(and_(
                PostLike.post_id == post_id,
                PostLike.user_id == user_id
            ))
        )
        like = existing_like.scalars().first()

        if like:
            # Remove like
            await db.delete(like)
            await db.execute(
                text("UPDATE posts SET likes_count = likes_count - 1 WHERE id = :post_id"),
                {"post_id": post_id}
            )
            await db.commit()

            # Get new count
            new_count = await PostLikeCRUD._get_post_likes_count(db, post_id)
            return False, new_count
        else:
            # Add like
            new_like = PostLike(post_id=post_id, user_id=user_id)
            db.add(new_like)
            await db.execute(
                text("UPDATE posts SET likes_count = likes_count + 1 WHERE id = :post_id"),
                {"post_id": post_id}
            )
            await db.commit()

            # Get new count
            new_count = await PostLikeCRUD._get_post_likes_count(db, post_id)
            return True, new_count

    @staticmethod
    async def toggle_comment_like(
        db: AsyncSession,
        comment_id: int,
        user_id: int
    ) -> Tuple[bool, int]:
        """Toggle like on a comment, returns (is_liked, new_count)"""
        # Check if already liked
        existing_like = await db.execute(
            select(PostLike)
            .where(and_(
                PostLike.comment_id == comment_id,
                PostLike.user_id == user_id
            ))
        )
        like = existing_like.scalars().first()

        if like:
            # Remove like
            await db.delete(like)
            await PostLikeCRUD._update_comment_likes_count(db, comment_id, -1)
            await db.commit()

            # Get new count
            new_count = await PostLikeCRUD._get_comment_likes_count(db, comment_id)
            return False, new_count
        else:
            # Add like
            new_like = PostLike(comment_id=comment_id, user_id=user_id)
            db.add(new_like)
            await PostLikeCRUD._update_comment_likes_count(db, comment_id, 1)
            await db.commit()

            # Get new count
            new_count = await PostLikeCRUD._get_comment_likes_count(db, comment_id)
            return True, new_count

    @staticmethod
    async def get_post_likes(
        db: AsyncSession,
        post_id: int,
        limit: int = 20
    ) -> List[PostLike]:
        """Get users who liked a post"""
        result = await db.execute(
            select(PostLike)
            .where(PostLike.post_id == post_id)
            .options(selectinload(PostLike.user))
            .order_by(desc(PostLike.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def _update_post_likes_count(db: AsyncSession, post_id: int, delta: int):
        """Update post likes count"""
        await db.execute(
            f"UPDATE posts SET likes_count = likes_count + {delta} WHERE id = {post_id}"
        )

    @staticmethod
    async def _update_comment_likes_count(db: AsyncSession, comment_id: int, delta: int):
        """Update comment likes count"""
        await db.execute(
            f"UPDATE post_comments SET likes_count = likes_count + {delta} WHERE id = {comment_id}"
        )

    @staticmethod
    async def _get_post_likes_count(db: AsyncSession, post_id: int) -> int:
        """Get current post likes count"""
        result = await db.execute(
            select(Post.likes_count).where(Post.id == post_id)
        )
        return result.scalar() or 0

    @staticmethod
    async def _get_comment_likes_count(db: AsyncSession, comment_id: int) -> int:
        """Get current comment likes count"""
        result = await db.execute(
            select(PostComment.likes_count).where(PostComment.id == comment_id)
        )
        return result.scalar() or 0


class PostCommentCRUD:
    """CRUD operations for post comments"""

    @staticmethod
    async def create_comment(
        db: AsyncSession,
        post_id: int,
        user_id: int,
        content: str,
        parent_comment_id: Optional[int] = None
    ) -> PostComment:
        """Create a new comment"""
        comment = PostComment(
            post_id=post_id,
            user_id=user_id,
            content=content,
            parent_comment_id=parent_comment_id
        )

        db.add(comment)

        # Update post comments count
        await db.execute(
            text("UPDATE posts SET comments_count = comments_count + 1 WHERE id = :post_id"),
            {"post_id": post_id}
        )

        # Update parent comment replies count if this is a reply
        if parent_comment_id:
            await db.execute(
                f"UPDATE post_comments SET replies_count = replies_count + 1 WHERE id = {parent_comment_id}"
            )

        await db.commit()
        await db.refresh(comment)

        return comment

    @staticmethod
    async def get_post_comments(
        db: AsyncSession,
        post_id: int,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> Tuple[List[PostComment], Optional[str]]:
        """Get comments for a post (top-level only)"""
        query = (
            select(PostComment)
            .where(and_(
                PostComment.post_id == post_id,
                PostComment.parent_comment_id.is_(None)
            ))
            .options(selectinload(PostComment.user))
            .order_by(desc(PostComment.created_at))
            .limit(limit + 1)
        )

        # Add cursor filtering
        if cursor:
            try:
                cursor_date = datetime.fromisoformat(cursor)
                query = query.where(PostComment.created_at < cursor_date)
            except ValueError:
                pass

        result = await db.execute(query)
        all_comments = result.scalars().all()

        comments = all_comments[:limit]
        next_cursor = None
        if len(all_comments) > limit:
            next_cursor = comments[-1].created_at.isoformat() if comments else None

        return comments, next_cursor

    @staticmethod
    async def get_comment_replies(
        db: AsyncSession,
        comment_id: int,
        limit: int = 10,
        cursor: Optional[str] = None
    ) -> Tuple[List[PostComment], Optional[str]]:
        """Get replies to a comment"""
        query = (
            select(PostComment)
            .where(PostComment.parent_comment_id == comment_id)
            .options(selectinload(PostComment.user))
            .order_by(PostComment.created_at)  # Ascending for replies
            .limit(limit + 1)
        )

        # Add cursor filtering
        if cursor:
            try:
                cursor_date = datetime.fromisoformat(cursor)
                query = query.where(PostComment.created_at > cursor_date)
            except ValueError:
                pass

        result = await db.execute(query)
        all_replies = result.scalars().all()

        replies = all_replies[:limit]
        next_cursor = None
        if len(all_replies) > limit:
            next_cursor = replies[-1].created_at.isoformat() if replies else None

        return replies, next_cursor


class PostViewCRUD:
    """CRUD operations for post views"""

    @staticmethod
    async def mark_post_as_viewed(
        db: AsyncSession,
        post_id: int,
        user_id: int,
        view_duration: Optional[int] = None
    ) -> PostView:
        """Mark a post as viewed (upsert)"""
        # Check if view already exists
        existing_view = await db.execute(
            select(PostView)
            .where(and_(
                PostView.post_id == post_id,
                PostView.user_id == user_id
            ))
        )
        view = existing_view.scalars().first()

        if view:
            # Update existing view
            view.viewed_at = datetime.utcnow()
            if view_duration is not None:
                view.view_duration = view_duration
        else:
            # Create new view
            view = PostView(
                post_id=post_id,
                user_id=user_id,
                view_duration=view_duration
            )
            db.add(view)

            # Update post views count
            await db.execute(
                text("UPDATE posts SET views_count = views_count + 1 WHERE id = :post_id"),
                {"post_id": post_id}
            )

        await db.commit()
        await db.refresh(view)

        return view

    @staticmethod
    async def batch_mark_as_viewed(
        db: AsyncSession,
        post_ids: List[int],
        user_id: int
    ) -> int:
        """Mark multiple posts as viewed, returns count of newly viewed posts"""
        processed = 0

        for post_id in post_ids:
            try:
                await PostViewCRUD.mark_post_as_viewed(db, post_id, user_id)
                processed += 1
            except Exception as e:
                logger.warning(f"Failed to mark post {post_id} as viewed: {e}")

        return processed