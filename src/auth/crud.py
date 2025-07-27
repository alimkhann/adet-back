import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from .exceptions import (DatabaseException, UserAlreadyExistsException,
                             UserNotFoundException)
from .models import User

logger = logging.getLogger(__name__)

class UserDAO:

    @staticmethod
    async def get_or_create_user_by_clerk_id(
        db: AsyncSession, clerk_id: str, email: str, username: str = None
    ) -> User:
        """
        Retrieves a user by their Clerk ID. If the user does not exist,
        it creates a new one with the provided Clerk ID, email, and username.
        Uses a more robust approach to handle race conditions.
        """
        logger.info(f"Attempting to get or create user with clerk_id: {clerk_id}")
        try:
            # First, try to get the user
            query = select(User).where(User.clerk_id == clerk_id)
            result = await db.execute(query)
            user = result.scalars().first()

            if user:
                logger.info(f"Found existing user with id: {user.id}")
                # Update email and username if they have changed in Clerk
                updated = False
                # Only update email if it's not a placeholder and different from current
                if email and not email.endswith("@placeholder.com") and user.email != email:
                    logger.info(f"Updating email for user {user.id} to {email}")
                    user.email = email
                    updated = True

                # Handle username update more carefully to avoid conflicts
                if username:
                    username = username.lower()
                    if user.username != username:
                        # Check if the new username is already taken by another user
                        existing_user_with_username = await UserDAO.get_user_by_username(username, db)
                        if existing_user_with_username and existing_user_with_username.id != user.id:
                            logger.warning(f"Username {username} is already taken by user {existing_user_with_username.id}. Skipping username update.")
                            # Don't update username if it's already taken
                        else:
                            logger.info(f"Updating username for user {user.id} to {username}")
                            user.username = username
                            updated = True

                if updated:
                    await db.commit()
                    await db.refresh(user)
                return user

            # If user does not exist, create a new one
            logger.info(f"User with clerk_id {clerk_id} not found. Creating new user.")
            new_user = User(
                clerk_id=clerk_id,
                email=email,
                username=username.lower() if username else None,
                streak_freezers=2  # Explicitly set streak freezers for new users
            )
            db.add(new_user)
            logger.info("Committing new user to the database...")
            await db.commit()
            logger.info("Commit successful. Refreshing user instance.")
            await db.refresh(new_user)
            logger.info(f"Successfully created new user with id: {new_user.id}")
            return new_user

        except IntegrityError as e:
            await db.rollback()
            # If we get a duplicate key error, try to fetch the existing user
            if "duplicate key value violates unique constraint" in str(e) and "ix_users_clerk_id" in str(e):
                logger.info(f"Duplicate key error for clerk_id {clerk_id}. Attempting to fetch existing user.")
                try:
                    query = select(User).where(User.clerk_id == clerk_id)
                    result = await db.execute(query)
                    existing_user = result.scalars().first()
                    if existing_user:
                        logger.info(f"Successfully retrieved existing user with id: {existing_user.id}")
                        return existing_user
                    else:
                        raise UserAlreadyExistsException(f"User with clerk_id {clerk_id} already exists but could not be retrieved.")
                except Exception as fetch_error:
                    logger.error(f"Error fetching existing user after duplicate key error: {fetch_error}")
                    raise UserAlreadyExistsException(f"User with clerk_id {clerk_id} already exists.")
            elif "duplicate key value violates unique constraint" in str(e) and "ix_users_username" in str(e):
                logger.warning(f"Username {username} is already taken. Attempting to create user with different username.")
                # Try to create user with a modified username
                if username:
                    import uuid
                    unique_username = f"{username}_{str(uuid.uuid4())[:8]}"
                    logger.info(f"Trying to create user with unique username: {unique_username}")
                    try:
                        new_user = User(
                            clerk_id=clerk_id,
                            email=email,
                            username=unique_username,
                            streak_freezers=2  # Explicitly set streak freezers for new users
                        )
                        db.add(new_user)
                        await db.commit()
                        await db.refresh(new_user)
                        logger.info(f"Successfully created new user with id: {new_user.id} and username: {unique_username}")
                        return new_user
                    except IntegrityError as retry_error:
                        await db.rollback()
                        logger.error(f"Failed to create user with unique username: {retry_error}")
                        raise UserAlreadyExistsException(f"Failed to create user: username conflict and retry failed.")
                else:
                    raise UserAlreadyExistsException(f"Failed to create user: username is required but not provided.")
            else:
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
    async def get_user_by_username(username: str, db: AsyncSession) -> Optional[User]:
        """Get user by username (case-insensitive, always lowercased)."""
        try:
            query = select(User).where(func.lower(User.username) == username.lower())
            result = await db.execute(query)
            user = result.scalars().first()
            if user:
                await db.refresh(user)
            return user
        except Exception as e:
            raise DatabaseException(f"get_user_by_username: {str(e)}")

    @staticmethod
    async def update_user(user: User, db: AsyncSession) -> User:
        """Update an existing user."""
        try:
            if user.username:
                user.username = user.username.lower()
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

    @staticmethod
    async def delete_user_by_clerk_id(db: AsyncSession, clerk_id: str) -> None:
        """
        Deletes a user from the database based on their Clerk ID.
        """
        stmt = select(User).where(User.clerk_id == clerk_id)
        result = await db.execute(stmt)
        user_to_delete = result.scalar_one_or_none()

        if user_to_delete:
            await db.delete(user_to_delete)
            await db.commit()