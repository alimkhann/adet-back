from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .crud import OnboardingCRUD
from .schema import OnboardingProgressCreate, OnboardingProgressUpdate, OnboardingProgressResponse
from .exceptions import OnboardingProgressNotFound

class OnboardingService:

    @staticmethod
    async def get_user_onboarding_progress(db: AsyncSession, user_id: int) -> Optional[OnboardingProgressResponse]:
        progress = await OnboardingCRUD.get_onboarding_progress(db, user_id)
        if progress:
            # Convert JSON string back to dict for response
            progress.data = json.loads(progress.data) if progress.data else None
            return OnboardingProgressResponse.model_validate(progress)
        return None

    @staticmethod
    async def get_user_onboarding_progress_or_raise(db: AsyncSession, user_id: int) -> OnboardingProgressResponse:
        progress = await OnboardingCRUD.get_onboarding_progress_or_raise(db, user_id)
        # Convert JSON string back to dict for response
        progress.data = json.loads(progress.data) if progress.data else None
        return OnboardingProgressResponse.model_validate(progress)

    @staticmethod
    async def create_user_onboarding_progress(db: AsyncSession, user_id: int, initial_data: Optional[Dict[str, Any]] = None) -> OnboardingProgressResponse:
        existing_progress = await OnboardingCRUD.get_onboarding_progress(db, user_id)
        if existing_progress:
            # If progress already exists, return it (or update if needed, based on specific logic)
            existing_progress.data = json.loads(existing_progress.data) if existing_progress.data else None
            return OnboardingProgressResponse.model_validate(existing_progress)

        onboarding_create = OnboardingProgressCreate(
            user_id=user_id,
            data=initial_data
        )
        new_progress = await OnboardingCRUD.create_onboarding_progress(db, onboarding_create)
        new_progress.data = json.loads(new_progress.data) if new_progress.data else None
        return OnboardingProgressResponse.model_validate(new_progress)

    @staticmethod
    async def update_user_onboarding_progress(db: AsyncSession, user_id: int, update_data: OnboardingProgressUpdate) -> OnboardingProgressResponse:
        updated_progress = await OnboardingCRUD.update_onboarding_progress(db, user_id, update_data)
        updated_progress.data = json.loads(updated_progress.data) if updated_progress.data else None
        return OnboardingProgressResponse.model_validate(updated_progress)

    @staticmethod
    async def complete_onboarding(db: AsyncSession, user_id: int) -> OnboardingProgressResponse:
        update_data = OnboardingProgressUpdate(is_completed=True)
        completed_progress = await OnboardingCRUD.update_onboarding_progress(db, user_id, update_data)
        completed_progress.data = json.loads(completed_progress.data) if completed_progress.data else None
        return OnboardingProgressResponse.model_validate(completed_progress)

import json # Added import for json