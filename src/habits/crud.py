from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import json
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

# --- Task Completion CRUD ---

async def create_task_entry(
    db: AsyncSession,
    habit_id: int,
    user_id: int,
    task_data: dict,
    assigned_date: date,
    due_date: datetime
) -> models.TaskEntry:
    """Create a new AI-generated task entry"""
    db_task = models.TaskEntry(
        habit_id=habit_id,
        user_id=user_id,
        task_description=task_data["task_description"],
        difficulty_level=task_data["difficulty_level"],
        estimated_duration=task_data["estimated_duration"],
        success_criteria=task_data["success_criteria"],
        celebration_message=task_data["celebration_message"],
        easier_alternative=task_data.get("easier_alternative"),
        harder_alternative=task_data.get("harder_alternative"),
        anchor_suggestion=task_data.get("anchor_suggestion"),
        proof_requirements=task_data["proof_requirements"],
        assigned_date=assigned_date,
        due_date=due_date,
        ai_generation_metadata=json.dumps(task_data.get("metadata", {})),
        calibration_metadata=json.dumps(task_data.get("calibration_metadata", {}))
    )

    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

async def get_today_task(
    db: AsyncSession,
    habit_id: int,
    user_id: int
) -> Optional[models.TaskEntry]:
    """Get today's task for a habit"""
    today = date.today()
    result = await db.execute(
        select(models.TaskEntry).filter(
            models.TaskEntry.habit_id == habit_id,
            models.TaskEntry.user_id == user_id,
            models.TaskEntry.assigned_date == today
        )
    )
    return result.scalar_one_or_none()

async def get_pending_tasks(
    db: AsyncSession,
    user_id: int,
    limit: int = 10
) -> List[models.TaskEntry]:
    """Get pending tasks for a user"""
    result = await db.execute(
        select(models.TaskEntry)
        .filter(
            models.TaskEntry.user_id == user_id,
            models.TaskEntry.status == models.TaskStatus.pending
        )
        .order_by(desc(models.TaskEntry.due_date))
        .limit(limit)
    )
    return result.scalars().all()

async def submit_task_proof(
    db: AsyncSession,
    task_id: int,
    user_id: int,
    proof_type: str,
    proof_content: str
) -> models.TaskEntry:
    """Submit proof for a task"""
    result = await db.execute(
        select(models.TaskEntry).filter(
            models.TaskEntry.id == task_id,
            models.TaskEntry.user_id == user_id
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise ValueError("Task not found")

    if task.status != models.TaskStatus.pending:
        raise ValueError("Task is not pending")

    # Update task with proof
    task.proof_type = proof_type
    task.proof_content = proof_content
    task.status = models.TaskStatus.completed
    task.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)
    return task

async def validate_task_proof(
    db: AsyncSession,
    task_id: int,
    validation_result: bool,
    confidence: float,
    feedback: str,
    suggestions: List[str] = None
) -> models.TaskValidation:
    """Create AI validation result for task proof"""
    db_validation = models.TaskValidation(
        task_entry_id=task_id,
        is_valid=validation_result,
        confidence=confidence,
        feedback=feedback,
        suggestions=json.dumps(suggestions or []),
        validation_model="vertex_ai_gemini_1_5_pro"
    )

    db.add(db_validation)
    await db.commit()
    await db.refresh(db_validation)
    return db_validation

async def update_task_status(
    db: AsyncSession,
    task_id: int,
    user_id: int,
    status: str
) -> models.TaskEntry:
    """Update task status"""
    result = await db.execute(
        select(models.TaskEntry).filter(
            models.TaskEntry.id == task_id,
            models.TaskEntry.user_id == user_id
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise ValueError("Task not found")

    task.status = status
    if status == models.TaskStatus.completed:
        task.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)
    return task

# --- Performance History CRUD ---

async def get_recent_performance(
    db: AsyncSession,
    user_id: int,
    habit_id: int,
    days: int = 7
) -> List[Dict[str, Any]]:
    """Get recent performance data for AI context"""
    start_date = date.today() - timedelta(days=days)

    result = await db.execute(
        select(models.TaskEntry).filter(
            models.TaskEntry.habit_id == habit_id,
            models.TaskEntry.user_id == user_id,
            models.TaskEntry.assigned_date >= start_date
        ).order_by(desc(models.TaskEntry.assigned_date))
    )

    tasks = result.scalars().all()

    performance_data = []
    for task in tasks:
        performance_data.append({
            "date": task.assigned_date.isoformat(),
            "completed": task.status == models.TaskStatus.completed,
            "difficulty": task.difficulty_level,
            "status": task.status
        })

    return performance_data

async def get_performance_history(
    db: AsyncSession,
    user_id: int,
    habit_id: int,
    days: int = 30
) -> List[Dict[str, Any]]:
    """Get performance history for analysis"""
    start_date = date.today() - timedelta(days=days)

    result = await db.execute(
        select(models.TaskEntry).filter(
            models.TaskEntry.habit_id == habit_id,
            models.TaskEntry.user_id == user_id,
            models.TaskEntry.assigned_date >= start_date
        ).order_by(desc(models.TaskEntry.assigned_date))
    )

    tasks = result.scalars().all()

    history_data = []
    for task in tasks:
        history_data.append({
            "date": task.assigned_date.isoformat(),
            "completed": task.status == models.TaskStatus.completed,
            "difficulty": task.difficulty_level,
            "status": task.status,
            "proof_type": task.proof_type,
            "validation_result": task.proof_validation_result,
            "validation_confidence": task.proof_validation_confidence
        })

    return history_data

# --- Motivation/Ability CRUD ---
from sqlalchemy import select
from .models import MotivationEntry, AbilityEntry

def _habit_id(habit_id):
    return int(habit_id)

async def get_motivation_entry(db: AsyncSession, user_id: str, habit_id: str, date):
    result = await db.execute(
        select(MotivationEntry).filter(
            MotivationEntry.user_id == user_id,
            MotivationEntry.habit_id == _habit_id(habit_id),
            MotivationEntry.date == date
        )
    )
    return result.scalar_one_or_none()

async def create_motivation_entry(db: AsyncSession, user_id: str, entry):
    db_entry = MotivationEntry(
        user_id=user_id,
        habit_id=_habit_id(entry.habit_id),
        date=entry.date,
        level=entry.level
    )
    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)
    return db_entry

async def get_ability_entry(db: AsyncSession, user_id: str, habit_id: str, date):
    result = await db.execute(
        select(AbilityEntry).filter(
            AbilityEntry.user_id == user_id,
            AbilityEntry.habit_id == _habit_id(habit_id),
            AbilityEntry.date == date
        )
    )
    return result.scalar_one_or_none()

async def create_ability_entry(db: AsyncSession, user_id: str, entry):
    db_entry = AbilityEntry(
        user_id=user_id,
        habit_id=_habit_id(entry.habit_id),
        date=entry.date,
        level=entry.level
    )
    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)
    return db_entry