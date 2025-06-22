from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.dependencies import get_current_user
from src.auth.models import User as UserModel
from src.database import get_async_db
from . import crud, schemas

router = APIRouter()

@router.post("/", response_model=schemas.OnboardingAnswer)
async def create_onboarding_answers_for_user(
    answer: schemas.OnboardingAnswerCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_answer = await crud.get_onboarding_answer(db, user_id=current_user.id)
    if db_answer:
        raise HTTPException(status_code=400, detail="Onboarding answers already exist for this user")
    return await crud.create_onboarding_answer(db=db, answer=answer, user_id=current_user.id)

@router.get("/", response_model=schemas.OnboardingAnswer)
async def read_onboarding_answers(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_answer = await crud.get_onboarding_answer(db, user_id=current_user.id)
    if db_answer is None:
        raise HTTPException(status_code=404, detail="Onboarding answers not found")
    return db_answer