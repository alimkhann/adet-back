from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.database import get_async_db
from src.auth.dependencies import get_current_user
from src.auth.models import User as UserModel
from . import crud, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.Habit])
async def read_habits(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    return await crud.get_habits_by_user(db=db, user_id=current_user.id)

@router.post("/", response_model=schemas.Habit)
async def create_habit(
    habit: schemas.HabitCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    return await crud.create_user_habit(db=db, habit=habit, user_id=current_user.id)