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
    async def delete_user_account(user_id: int, db: AsyncSession) -> bool:
        """Delete user account."""
        user = await UserDAO.get_user_by_id_or_raise(user_id, db)
        return await UserDAO.delete_user(user, db)