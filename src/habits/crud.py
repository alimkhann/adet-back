from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.exc import IntegrityError
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
    print(f"Attempting to delete habit {habit_id} for user {user_id}")
    db_habit = await get_habit(db=db, habit_id=habit_id, user_id=user_id)
    if db_habit:
        print(f"Found habit to delete: {db_habit.name} (ID: {db_habit.id})")
        await db.delete(db_habit)
        await db.commit()
        print(f"Successfully deleted habit {habit_id}")
    else:
        print(f"Habit {habit_id} not found for user {user_id}")
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
        proof_requirements=task_data["proof_requirements"],
        assigned_date=assigned_date,
        due_date=due_date,
        ai_generation_metadata=json.dumps(task_data.get("metadata", {})),
        calibration_metadata=json.dumps(task_data.get("calibration_metadata", {})),
        attempts_left=3  # Set default attempts
    )

    db.add(db_task)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return await get_today_task(db, habit_id, user_id, assigned_date)

    await db.refresh(db_task)
    return db_task

async def get_today_task(
    db: AsyncSession,
    habit_id: int,
    user_id: int,
    for_date: date = None
) -> Optional[models.TaskEntry]:
    print(f"DEBUG get_today_task: habit_id={habit_id} ({type(habit_id)}), user_id={user_id} ({type(user_id)}), for_date={for_date} ({type(for_date)})")
    if for_date is None:
        for_date = date.today()
    stmt = (
        select(models.TaskEntry)
        .filter(
            models.TaskEntry.habit_id == habit_id,
            models.TaskEntry.user_id == user_id,
            models.TaskEntry.assigned_date == for_date
        )
        .order_by(desc(models.TaskEntry.created_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()

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
    days: int = 7,
    reference_date: date = None
) -> List[Dict[str, Any]]:
    """Get recent performance data for AI context"""
    if reference_date is None:
        from datetime import date
        reference_date = date.today()
    start_date = reference_date - timedelta(days=days)

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
    days: int = 30,
    reference_date: date = None
) -> List[Dict[str, Any]]:
    """Get performance history for analysis"""
    if reference_date is None:
        from datetime import date
        reference_date = date.today()
    start_date = reference_date - timedelta(days=days)

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

async def update_motivation_entry(db: AsyncSession, user_id: str, habit_id: str, date, level: str):
    result = await db.execute(
        select(MotivationEntry).filter(
            MotivationEntry.user_id == user_id,
            MotivationEntry.habit_id == _habit_id(habit_id),
            MotivationEntry.date == date
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        return None
    entry.level = level
    await db.commit()
    await db.refresh(entry)
    return entry

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

async def get_task_by_id(
    db: AsyncSession,
    task_id: int,
    user_id: int
) -> Optional[models.TaskEntry]:
    """Get a task by ID and verify ownership"""
    result = await db.execute(
        select(models.TaskEntry).filter(
            models.TaskEntry.id == task_id,
            models.TaskEntry.user_id == user_id
        )
    )
    return result.scalar_one_or_none()

async def update_habit_streak(
    db: AsyncSession,
    habit_id: int,
    streak_count: int
) -> models.Habit:
    result = await db.execute(
        select(models.Habit).filter(models.Habit.id == habit_id)
    )
    habit = result.scalar_one_or_none()
    if habit:
        # Award a freezer to the user at every 10 streaks
        if streak_count > 0 and streak_count % 10 == 0:
            await increment_streak_freezer_for_user(db, habit.user_id, 1)
        habit.streak = streak_count
        await db.commit()
        await db.refresh(habit)
    return habit

# --- Streak Freezer Helpers (per user) ---
async def get_streak_freezers_by_user(db: AsyncSession, user_id: int) -> int:
    from src.auth.models import User
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    return user.streak_freezers if user else 0

async def increment_streak_freezer_for_user(db: AsyncSession, user_id: int, amount: int = 1):
    from src.auth.models import User
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.streak_freezers += amount
        await db.commit()
        await db.refresh(user)
    return user

async def decrement_streak_freezer_for_user(db: AsyncSession, user_id: int, amount: int = 1):
    from src.auth.models import User
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and user.streak_freezers > 0:
        user.streak_freezers = max(0, user.streak_freezers - amount)
        await db.commit()
        await db.refresh(user)
    return user

async def generate_and_create_task(
    db: AsyncSession,
    habit,
    user_id: int,
    task_request,
    assigned_date: date
):
    """Generate and create a task entry using AI orchestrator"""
    from ..ai.orchestrator import get_ai_orchestrator
    from ..ai.schemas import TaskGenerationContext
    from datetime import datetime, timedelta
    import pytz

    # Get recent performance for context
    recent_performance = await get_recent_performance(
        db=db,
        user_id=user_id,
        habit_id=habit.id,
        days=7,
        reference_date=assigned_date
    )

    # Get current streak from habit
    streak = habit.streak or 0

    # Get most recent feedback from latest completed TaskEntry for this habit
    recent_feedback = ""
    recent_task = await db.execute(
        select(models.TaskEntry)
        .filter(models.TaskEntry.habit_id == habit.id, models.TaskEntry.user_id == user_id, models.TaskEntry.status == "completed")
        .order_by(desc(models.TaskEntry.assigned_date))
    )
    recent_task_obj = recent_task.scalars().first()
    if recent_task_obj and recent_task_obj.proof_feedback:
        recent_feedback = recent_task_obj.proof_feedback

    # Calculate due date in user's timezone if provided
    user_tz = None
    if hasattr(task_request, 'user_timezone') and task_request.user_timezone:
        try:
            user_tz = pytz.timezone(task_request.user_timezone)
        except Exception:
            user_tz = pytz.timezone('UTC')
    else:
        user_tz = pytz.timezone('UTC')

    now_local = datetime.now(user_tz)
    due_date_local = now_local + timedelta(hours=4)
    due_date_utc = due_date_local.astimezone(pytz.utc)

    # Create task generation context
    context = TaskGenerationContext(
        habit_name=habit.name,
        habit_description=habit.description or "",
        base_difficulty=task_request.base_difficulty,
        motivation_level=task_request.motivation_level,
        ability_level=task_request.ability_level,
        proof_style=task_request.proof_style,
        user_language=task_request.user_language or "en",
        recent_performance=recent_performance,
        current_time=now_local,
        day_of_week=now_local.strftime("%A"),
        user_timezone=task_request.user_timezone or "UTC",
        streak=streak,
        recent_feedback=recent_feedback
    )

    # Generate task using AI orchestrator
    ai_orchestrator = get_ai_orchestrator()
    response = await ai_orchestrator.generate_personalized_task(
        context=context,
        recent_performance=recent_performance,
        streak=streak,
        recent_feedback=recent_feedback
    )

    # If full AI generation fails, try quick fallback
    if not response.success:
        response = await ai_orchestrator.generate_quick_task(
            habit_name=habit.name,
            base_difficulty=habit.difficulty,
            proof_style=habit.proof_style,
            language="en"
        )

    if not response.success:
        raise Exception(f"Failed to generate task: {response.error}")

    # Create task entry in database
    task_entry = await create_task_entry(
        db=db,
        habit_id=habit.id,
        user_id=user_id,
        task_data=response.data,
        assigned_date=assigned_date,
        due_date=due_date_utc.replace(tzinfo=None)  # store as naive UTC
    )

    # Commit and refresh the entry
    await db.commit()
    await db.refresh(task_entry)

    return task_entry