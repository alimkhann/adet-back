from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas

async def create_onboarding_answer(db: AsyncSession, answer: schemas.OnboardingAnswerCreate, user_id: int):
    db_answer = models.OnboardingAnswer(**answer.dict(), user_id=user_id)
    db.add(db_answer)
    await db.commit()
    await db.refresh(db_answer)
    return db_answer

async def get_onboarding_answer(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.OnboardingAnswer).filter(models.OnboardingAnswer.user_id == user_id))
    return result.scalars().first()

async def update_onboarding_answer(db: AsyncSession, answer: schemas.OnboardingAnswerCreate, user_id: int):
    result = await db.execute(select(models.OnboardingAnswer).filter(models.OnboardingAnswer.user_id == user_id))
    db_answer = result.scalars().first()
    if db_answer:
        # Update all fields
        db_answer.habit_name = answer.habit_name
        db_answer.habit_description = answer.habit_description
        db_answer.frequency = answer.frequency
        db_answer.validation_time = answer.validation_time
        db_answer.difficulty = answer.difficulty
        db_answer.proof_style = answer.proof_style
        await db.commit()
        await db.refresh(db_answer)
    return db_answer