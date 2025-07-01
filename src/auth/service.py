"""
Auth service layer containing business logic for authentication.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from .crud import UserDAO
from .exceptions import UserNotFoundException, UserAlreadyExistsException
from .models import User as UserModel

class AuthService:
    @staticmethod
    async def update_username(
        user_id: int,
        username: str,
        db: AsyncSession
    ) -> UserModel:
        """Update user username."""
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
        """Delete user account."""
        user = await UserDAO.get_user_by_id_or_raise(user_id, db)
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