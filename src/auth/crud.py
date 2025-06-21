from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .exceptions import (DatabaseException, UserAlreadyExistsException,
                             UserNotFoundException)
from .models import User


class UserDAO:

    @staticmethod
    async def get_or_create_user_by_clerk_id(
        db: AsyncSession, clerk_id: str, username: str
    ) -> User:
        """
        Retrieves a user by their Clerk ID. If the user does not exist,
        it creates a new one with the provided Clerk ID and username.
        """
        try:
            # First, try to get the user
            query = select(User).where(User.clerk_id == clerk_id)
            result = await db.execute(query)
            user = result.scalars().first()

            if user:
                # Optional: Update username if it has changed in Clerk
                if user.username != username:
                    user.username = username
                    await db.commit()
                    await db.refresh(user)
                return user

            # If user does not exist, create a new one
            new_user = User(clerk_id=clerk_id, username=username)
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            return new_user

        except IntegrityError:  # Should not happen with get-or-create logic, but as a safeguard
            await db.rollback()
            raise UserAlreadyExistsException(f"User with clerk_id {clerk_id} already exists.")
        except Exception as e:
            await db.rollback()
            raise DatabaseException(f"get_or_create_user_by_clerk_id: {str(e)}")

    @staticmethod
    async def get_user_by_id(user_id: int, db: AsyncSession) -> Optional[User]:
        """Get user by internal database ID."""
        try:
            query = select(User).where(User.id == user_id)
            result = await db.execute(query)
            user = result.scalars().first()
            if user:
                await db.refresh(user)
            return user
        except Exception as e:
            raise DatabaseException(f"get_user_by_id: {str(e)}")

    @staticmethod
    async def update_user(user: User, db: AsyncSession) -> User:
        """Update an existing user."""
        try:
            await db.commit()
            await db.refresh(user)
            return user
        except IntegrityError:
            await db.rollback()
            raise UserAlreadyExistsException(f"Integrity error on user update for clerk_id: {user.clerk_id}")
        except Exception as e:
            await db.rollback()
            raise DatabaseException(f"update_user: {str(e)}")

    @staticmethod
    async def delete_user(user: User, db: AsyncSession) -> bool:
        """Delete a user."""
        try:
            await db.delete(user)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise DatabaseException(f"delete_user: {str(e)}")

    @staticmethod
    async def get_user_by_id_or_raise(user_id: int, db: AsyncSession) -> User:
        """Get user by ID or raise UserNotFoundException."""
        user = await UserDAO.get_user_by_id(user_id, db)
        if user is None:
            raise UserNotFoundException(str(user_id))
        return user