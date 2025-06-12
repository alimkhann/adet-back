from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from .models import OnboardingProgress
from .schema import OnboardingProgressCreate, OnboardingProgressUpdate
from .exceptions import OnboardingProgressNotFound

class OnboardingCRUD:

    @staticmethod
    async def create_onboarding_progress(db: AsyncSession, data: OnboardingProgressCreate) -> OnboardingProgress:
        db_progress = OnboardingProgress(
            user_id=data.user_id,
            current_step=data.current_step,
            is_completed=data.is_completed,
            data=data.data.json() if data.data else None
        )
        db.add(db_progress)
        await db.commit()
        await db.refresh(db_progress)
        return db_progress

    @staticmethod
    async def get_onboarding_progress(db: AsyncSession, user_id: int) -> Optional[OnboardingProgress]:
        query = select(OnboardingProgress).where(OnboardingProgress.user_id == user_id)
        result = await db.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_onboarding_progress_or_raise(db: AsyncSession, user_id: int) -> OnboardingProgress:
        progress = await OnboardingCRUD.get_onboarding_progress(db, user_id)
        if progress is None:
            raise OnboardingProgressNotFound(user_id)
        return progress

    @staticmethod
    async def update_onboarding_progress(db: AsyncSession, user_id: int, data: OnboardingProgressUpdate) -> OnboardingProgress:
        db_progress = await OnboardingCRUD.get_onboarding_progress_or_raise(db, user_id)

        update_data = data.model_dump(exclude_unset=True)
        if "data" in update_data and update_data["data"] is not None: # Convert dict to JSON string for storage
            update_data["data"] = json.dumps(update_data["data"])

        if update_data:
            await db.execute(
                update(OnboardingProgress).where(OnboardingProgress.user_id == user_id).values(**update_data)
            )
            await db.commit()
            await db.refresh(db_progress)
        return db_progress

    @staticmethod
    async def delete_onboarding_progress(db: AsyncSession, user_id: int) -> bool:
        db_progress = await OnboardingCRUD.get_onboarding_progress_or_raise(db, user_id)
        await db.delete(db_progress)
        await db.commit()
        return True

import json # Added import for json