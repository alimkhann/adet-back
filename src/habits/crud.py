from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from . import models, schemas

async def get_habits_by_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.Habit).filter(models.Habit.user_id == user_id))
    return result.scalars().all()

async def create_user_habit(db: AsyncSession, habit: schemas.HabitCreate, user_id: int):
    db_habit = models.Habit(**habit.dict(), user_id=user_id)
    db.add(db_habit)
    await db.commit()
    await db.refresh(db_habit)
    return db_habit