"""
Auth service layer containing business logic for authentication.
"""
from datetime import timedelta
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .crud import UserDAO
from .exceptions import (InvalidCredentialsException,
                             UserAlreadyExistsException, UserNotFoundException)
from .schema import User, UserCredentials, UserUpdate, PasswordUpdate
from .utils import create_access_token, get_password_hash, verify_password
from .models import User as UserModel


class AuthService:
    @staticmethod
    async def authenticate_user(
        email: str,
        password: str,
        db: AsyncSession
    ) -> Dict[str, str]:
        user = await UserDAO.get_user_by_email(email, db)

        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsException()

        access_token_expires = timedelta(hours=1)
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    @staticmethod
    async def register_user(
        credentials: UserCredentials,
        db: AsyncSession
    ) -> Dict[str, str]:
        """
        Register a new user.
        Returns access token if successful.
        """
        # Check if user already exists
        if await UserDAO.user_exists(credentials.email, db):
            raise UserAlreadyExistsException(credentials.email)

        # Create new user
        hashed_password = get_password_hash(credentials.password)
        new_user = UserModel(
            email=credentials.email,
            username=credentials.username,
            hashed_password=hashed_password
        )

        created_user = await UserDAO.create_user(new_user, db)

        # Generate access token
        access_token = create_access_token(
            data={"sub": created_user.email}
        )

        refresh_token_expires = timedelta(days=7) # Typically longer than access token
        refresh_token = create_access_token(
            data={"sub": created_user.email, "type": "refresh"},
            expires_delta=refresh_token_expires
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    @staticmethod
    async def get_user_profile(user_id: int, db: AsyncSession) -> User:
        """Get user profile by ID."""
        return await UserDAO.get_user_by_id_or_raise(user_id, db)

    @staticmethod
    async def update_user_profile(
        user_id: int,
        user_update: UserUpdate,
        db: AsyncSession
    ) -> User:
        """Update user profile (email, username)."""
        user = await UserDAO.get_user_by_id_or_raise(user_id, db)

        if user_update.email and user_update.email != user.email:
            if await UserDAO.user_exists(user_update.email, db):
                raise UserAlreadyExistsException(user_update.email)
            user.email = user_update.email

        if user_update.username and user_update.username != user.username:
            user.username = user_update.username

        return await UserDAO.update_user(user, db)

    @staticmethod
    async def update_user_password(
        user_id: int,
        current_password: str,
        new_password: str,
        db: AsyncSession
    ) -> bool:
        """Update user password."""
        user = await UserDAO.get_user_by_id_or_raise(user_id, db)

        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsException()

        user.hashed_password = get_password_hash(new_password)
        await UserDAO.update_user(user, db)
        return True

    @staticmethod
    async def delete_user_account(user_id: int, db: AsyncSession) -> bool:
        """Delete user account."""
        user = await UserDAO.get_user_by_id_or_raise(user_id, db)
        return await UserDAO.delete_user(user, db)