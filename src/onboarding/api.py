from fastapi import APIRouter, Depends, Body, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user
from ..auth.models import User as AuthUser # Renamed to avoid conflict with Pydantic User
from ..database import get_async_db
from .service import OnboardingService
from .schema import OnboardingProgressResponse, OnboardingProgressUpdate
from .exceptions import raise_onboarding_http_exception, OnboardingProgressNotFound

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

@router.get(
    "/me",
    response_model=OnboardingProgressResponse,
    summary="Get User Onboarding Progress",
    description="Retrieves the onboarding progress for the currently authenticated user."
)
async def get_my_onboarding_progress(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        progress = await OnboardingService.get_user_onboarding_progress_or_raise(db, current_user.id)
        return progress
    except OnboardingProgressNotFound as e:
        raise_onboarding_http_exception(e)

@router.post(
    "/start",
    response_model=OnboardingProgressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start User Onboarding",
    description="Initiates the onboarding process for the currently authenticated user."
)
async def start_my_onboarding(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        progress = await OnboardingService.create_user_onboarding_progress(db, current_user.id)
        return progress
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to start onboarding: {e}")

@router.put(
    "/me",
    response_model=OnboardingProgressResponse,
    summary="Update User Onboarding Progress",
    description="Updates the onboarding progress for the currently authenticated user."
)
async def update_my_onboarding_progress(
    update_data: OnboardingProgressUpdate = Body(...),
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        progress = await OnboardingService.update_user_onboarding_progress(db, current_user.id, update_data)
        return progress
    except OnboardingProgressNotFound as e:
        raise_onboarding_http_exception(e)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update onboarding: {e}")

@router.post(
    "/complete",
    response_model=OnboardingProgressResponse,
    summary="Complete User Onboarding",
    description="Marks the onboarding process as complete for the currently authenticated user."
)
async def complete_my_onboarding(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        progress = await OnboardingService.complete_onboarding(db, current_user.id)
        return progress
    except OnboardingProgressNotFound as e:
        raise_onboarding_http_exception(e)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to complete onboarding: {e}")