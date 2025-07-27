from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.dependencies import get_current_user
from src.auth.models import User as UserModel
from src.database import get_async_db
from . import crud, schemas
from src.habits import crud as habits_crud, schemas as habits_schemas

router = APIRouter()

@router.post("/", response_model=schemas.OnboardingAnswer)
async def create_onboarding_answers_for_user(
    answer: schemas.OnboardingAnswerCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_answer = await crud.get_onboarding_answer(db, user_id=current_user.id)
    if db_answer:
        # Update existing onboarding answers instead of throwing error
        db_answer = await crud.update_onboarding_answer(db=db, answer=answer, user_id=current_user.id)
    else:
        # Create new onboarding answers
        db_answer = await crud.create_onboarding_answer(db=db, answer=answer, user_id=current_user.id)

        # --- Create a Habit for the user from onboarding answer (only for new users) ---
        habit_data = habits_schemas.HabitCreate(
            name=answer.habit_name,
            description=answer.habit_description,
            frequency=answer.frequency,
            validation_time=answer.validation_time,
            difficulty=answer.difficulty,
            proofStyle=answer.proof_style  # Use camelCase as expected by the schema
        )
        await habits_crud.create_user_habit(db=db, habit_data=habit_data, user_id=current_user.id)

    return db_answer

@router.get("/", response_model=schemas.OnboardingAnswer)
async def read_onboarding_answers(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_answer = await crud.get_onboarding_answer(db, user_id=current_user.id)
    if db_answer is None:
        raise HTTPException(status_code=404, detail="Onboarding answers not found")
    return db_answer