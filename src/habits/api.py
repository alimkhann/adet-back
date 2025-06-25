from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import date

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
    return await crud.create_user_habit(db=db, habit_data=habit, user_id=current_user.id)

@router.put("/{habit_id}", response_model=schemas.Habit)
async def update_habit(
    habit_id: int,
    habit: schemas.HabitCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_habit = await crud.get_habit(db=db, habit_id=habit_id, user_id=current_user.id)
    if db_habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    return await crud.update_habit(db=db, habit_id=habit_id, habit_data=habit, user_id=current_user.id)

@router.delete("/{habit_id}")
async def delete_habit(
    habit_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_habit = await crud.get_habit(db=db, habit_id=habit_id, user_id=current_user.id)
    if db_habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    await crud.delete_habit(db=db, habit_id=habit_id, user_id=current_user.id)
    return {"message": "Habit deleted successfully"}

# --- Motivation/Ability Endpoints ---

def _get_user_id(user: UserModel):
    # Use clerk_id for Motivation/Ability entries
    return user.clerk_id

@router.post("/{habit_id}/motivation", response_model=schemas.MotivationEntryRead)
async def submit_motivation_entry(habit_id: str, entry: schemas.MotivationEntryCreate, db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_user)):
    today = entry.date
    user_id = _get_user_id(current_user)
    existing = await crud.get_motivation_entry(db, user_id, habit_id, today)
    if existing:
        raise HTTPException(status_code=400, detail="Motivation entry already exists for today.")
    return await crud.create_motivation_entry(db, user_id, entry)

@router.get("/{habit_id}/motivation/today", response_model=schemas.MotivationEntryRead)
async def get_today_motivation_entry(habit_id: str, db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_user)):
    today = date.today()
    user_id = _get_user_id(current_user)
    entry = await crud.get_motivation_entry(db, user_id, habit_id, today)
    if not entry:
        raise HTTPException(status_code=404, detail="No motivation entry for today.")
    return entry

@router.post("/{habit_id}/ability", response_model=schemas.AbilityEntryRead)
async def submit_ability_entry(habit_id: str, entry: schemas.AbilityEntryCreate, db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_user)):
    today = entry.date
    user_id = _get_user_id(current_user)
    existing = await crud.get_ability_entry(db, user_id, habit_id, today)
    if existing:
        raise HTTPException(status_code=400, detail="Ability entry already exists for today.")
    return await crud.create_ability_entry(db, user_id, entry)

@router.get("/{habit_id}/ability/today", response_model=schemas.AbilityEntryRead)
async def get_today_ability_entry(habit_id: str, db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_user)):
    today = date.today()
    user_id = _get_user_id(current_user)
    entry = await crud.get_ability_entry(db, user_id, habit_id, today)
    if not entry:
        raise HTTPException(status_code=404, detail="No ability entry for today.")
    return entry