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