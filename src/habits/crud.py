from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from . import models, schemas

async def get_habits_by_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.Habit).filter(models.Habit.user_id == user_id))
    return result.scalars().all()

async def get_habit(db: AsyncSession, habit_id: int, user_id: int):
    result = await db.execute(
        select(models.Habit).filter(
            models.Habit.id == habit_id,
            models.Habit.user_id == user_id
        )
    )
    return result.scalar_one_or_none()

async def create_user_habit(db: AsyncSession, habit_data: schemas.HabitCreate, user_id: int):
    # Use the provided habit_data, which should already contain all required fields
    db_habit = models.Habit(
        name=habit_data.name,
        description=habit_data.description,
        frequency=habit_data.frequency,
        validation_time=habit_data.validation_time,
        difficulty=habit_data.difficulty,
        proof_style=habit_data.proof_style,
        user_id=user_id
    )

    db.add(db_habit)
    await db.commit()
    await db.refresh(db_habit)
    return db_habit

async def update_habit(db: AsyncSession, habit_id: int, habit_data: schemas.HabitUpdate, user_id: int):
    db_habit = await get_habit(db=db, habit_id=habit_id, user_id=user_id)
    if not db_habit:
        return None

    update_data = habit_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_habit, key, value)

    await db.commit()
    await db.refresh(db_habit)
    return db_habit

async def delete_habit(db: AsyncSession, habit_id: int, user_id: int):
    db_habit = await get_habit(db=db, habit_id=habit_id, user_id=user_id)
    if db_habit:
        await db.delete(db_habit)
        await db.commit()
    return db_habit