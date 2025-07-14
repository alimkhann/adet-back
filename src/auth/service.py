"""
Auth service layer containing business logic for authentication.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from .crud import UserDAO
from .exceptions import UserNotFoundException, UserAlreadyExistsException
from .models import User as UserModel
from src.posts.models import Post
from src.habits.models import Habit
from src.auth.models import User as UserModel
from src.services.file_upload import file_upload_service
from sqlalchemy import select

class AuthService:
    @staticmethod
    async def update_username(
        user_id: int,
        username: str,
        db: AsyncSession
    ) -> UserModel:
        """Update user username."""
        username = username.lower() if username else None
        user = await UserDAO.get_user_by_id_or_raise(user_id, db)
        user.username = username
        return await UserDAO.update_user(user, db)

    @staticmethod
    async def update_profile_image(
        user_id: int,
        profile_image_url: str,
        db: AsyncSession
    ) -> UserModel:
        """Update user profile image URL."""
        user = await UserDAO.get_user_by_id_or_raise(user_id, db)
        user.profile_image_url = profile_image_url
        return await UserDAO.update_user(user, db)

    @staticmethod
    async def delete_profile_image(
        user_id: int,
        db: AsyncSession
    ) -> UserModel:
        """Delete user profile image by setting URL to None."""
        user = await UserDAO.get_user_by_id_or_raise(user_id, db)
        user.profile_image_url = None
        return await UserDAO.update_user(user, db)

    @staticmethod
    async def delete_user_account(user_id: int, db: AsyncSession) -> bool:
        """Delete user account and all related app data, including Azure blobs."""
        user = await UserDAO.get_user_by_id_or_raise(user_id, db)

        # 1. Delete all Azure blobs for profile image
        if user.profile_image_url:
            try:
                await file_upload_service.delete_blob_from_url(user.profile_image_url)
            except Exception as e:
                print(f"Failed to delete profile image blob: {e}")

        # 2. Delete all Azure blobs for proof media in posts
        posts = await db.execute(select(Post).where(Post.user_id == user_id))
        for post in posts.scalars():
            if hasattr(post, 'proof_urls') and post.proof_urls:
                for url in post.proof_urls:
                    try:
                        await file_upload_service.delete_blob_from_url(url)
                    except Exception as e:
                        print(f"Failed to delete proof blob: {e}")

        # 3. Delete all Azure blobs for habit-related media (if any)
        habits = await db.execute(select(Habit).where(Habit.user_id == user_id))
        for habit in habits.scalars():
            # If you ever store media on habits, delete here
            pass

        # 4. Delete user and all app-related data (cascades)
        return await UserDAO.delete_user(user, db)

    @staticmethod
    async def update_user_profile(
        user_id: int,
        db: AsyncSession,
        name: str = None,
        username: str = None,
        bio: str = None
    ) -> UserModel:
        """Update user profile information (name, username, bio)."""
        user = await UserDAO.get_user_by_id_or_raise(user_id, db)

        # Check if username is already taken by another user
        if username:
            username = username.lower()
        if username and username != user.username:
            existing_user = await UserDAO.get_user_by_username(username, db)
            if existing_user and existing_user.id != user_id:
                raise ValueError("Username already taken")

        # Update fields if provided
        if name is not None:
            user.name = name
        if username is not None:
            user.username = username
        if bio is not None:
            user.bio = bio

        return await UserDAO.update_user(user, db)