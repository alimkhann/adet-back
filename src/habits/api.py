from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import date, datetime, timedelta
from pytz import UTC

from src.database import get_async_db
from src.auth.dependencies import get_current_user
from src.auth.models import User as UserModel
from src.ai import get_ai_orchestrator, TaskGenerationContext, AIAgentResponse
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

# --- Task Completion Endpoints ---

@router.get("/{habit_id}/today-task", response_model=schemas.TaskEntryRead)
async def get_today_task(
    habit_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get today's task for a habit"""
    # Verify habit exists and belongs to user
    habit = await crud.get_habit(db=db, habit_id=habit_id, user_id=current_user.id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    # Get today's task
    task = await crud.get_today_task(db=db, habit_id=habit_id, user_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="No task found for today")

    return task

@router.get("/pending-tasks", response_model=List[schemas.TaskEntryRead])
async def get_pending_tasks(
    limit: int = 10,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get pending tasks for the user"""
    tasks = await crud.get_pending_tasks(db=db, user_id=current_user.id, limit=limit)
    return tasks

@router.post("/{habit_id}/generate-and-create-task")
async def generate_and_create_task(
    habit_id: int,
    task_request: schemas.AITaskRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Generate AI task and create it in the database"""
    try:
        # Get habit details
        habit = await crud.get_habit(db=db, habit_id=habit_id, user_id=current_user.id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")

        # Check if task already exists for today
        existing_task = await crud.get_today_task(db=db, habit_id=habit_id, user_id=current_user.id)
        if existing_task:
            raise HTTPException(status_code=400, detail="Task already exists for today")

        # Get recent performance for context
        recent_performance = await crud.get_recent_performance(
            db=db,
            user_id=current_user.id,
            habit_id=habit_id,
            days=7
        )

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
            current_time=datetime.utcnow(),
            day_of_week=datetime.utcnow().strftime("%A"),
            user_timezone=task_request.user_timezone or "UTC"
        )

        # Generate task using AI orchestrator
        ai_orchestrator = get_ai_orchestrator()
        response = await ai_orchestrator.generate_personalized_task(
            context=context,
            recent_performance=recent_performance
        )

        # If full AI generation fails, try quick fallback
        if not response.success:
            logger.warning(f"Full AI generation failed: {response.error}. Trying quick fallback...")
            response = await ai_orchestrator.generate_quick_task(
                habit_name=habit.name,
                base_difficulty=habit.difficulty,
                proof_style=habit.proof_style,
                language="en"
            )

        if not response.success:
            raise HTTPException(status_code=500, detail=f"Failed to generate task: {response.error}")

        # Create task entry in database
        task_entry = await crud.create_task_entry(
            db=db,
            habit_id=habit_id,
            user_id=current_user.id,
            task_data=response.data,
            assigned_date=date.today(),
            due_date=datetime.utcnow() + timedelta(hours=4)
        )

        # Commit and refresh the entry
        await db.commit()
        await db.refresh(task_entry)

        # Return task creation response format
        return {
            "success": True,
            "task": task_entry,
            "ai_metadata": response.metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate and create task: {str(e)}")

@router.post("/tasks/{task_id}/submit-proof")
async def submit_task_proof(
    task_id: int,
    proof_data: schemas.TaskProofSubmit,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Submit proof for a task"""
    try:
        # Submit proof
        task = await crud.submit_task_proof(
            db=db,
            task_id=task_id,
            user_id=current_user.id,
            proof_type=proof_data.proof_type,
            proof_content=proof_data.proof_content
        )

        # TODO: Add AI validation here in Phase 3
        # For now, mark as validated
        await crud.validate_task_proof(
            db=db,
            task_id=task_id,
            validation_result=True,
            confidence=0.8,
            feedback="Proof submitted successfully"
        )

        return {
            "success": True,
            "task": task,
            "message": "Proof submitted successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit proof: {str(e)}")

@router.put("/tasks/{task_id}/status")
async def update_task_status(
    task_id: int,
    status_update: schemas.TaskStatusUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Update task status (complete, fail, miss)"""
    try:
        task = await crud.update_task_status(
            db=db,
            task_id=task_id,
            user_id=current_user.id,
            status=status_update.status
        )

        return {
            "success": True,
            "task": task,
            "message": f"Task status updated to {status_update.status}"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task status: {str(e)}")

# --- AI Task Generation Endpoints ---

@router.post("/{habit_id}/generate-task")
async def generate_ai_task(
    habit_id: int,
    task_request: schemas.AITaskRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Generate a personalized AI task for the habit using BJ Fogg's Tiny Habits methodology
    """
    try:
        # Get habit details
        habit = await crud.get_habit(db=db, habit_id=habit_id, user_id=current_user.id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")

        # Get recent performance for context
        recent_performance = await crud.get_recent_performance(
            db=db,
            user_id=current_user.id,
            habit_id=habit_id,
            days=7
        )

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
            current_time=datetime.utcnow(),
            day_of_week=datetime.utcnow().strftime("%A"),
            user_timezone=task_request.user_timezone or "UTC"
        )

        # Generate task using AI orchestrator
        ai_orchestrator = get_ai_orchestrator()
        response = await ai_orchestrator.generate_personalized_task(
            context=context,
            recent_performance=recent_performance
        )

        if not response.success:
            raise HTTPException(status_code=500, detail=response.error)

        return {
            "success": True,
            "task": response.data,
            "metadata": response.metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate task: {str(e)}")

@router.post("/{habit_id}/generate-quick-task")
async def generate_quick_task(
    habit_id: int,
    quick_request: schemas.QuickTaskRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Generate a quick task without full context (fallback method)
    """
    try:
        # Get habit details
        habit = await crud.get_habit(db=db, habit_id=habit_id, user_id=current_user.id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")

        # Generate quick task
        ai_orchestrator = get_ai_orchestrator()
        response = await ai_orchestrator.generate_quick_task(
            habit_name=habit.name,
            base_difficulty=quick_request.base_difficulty,
            proof_style=quick_request.proof_style,
            language=quick_request.user_language or "en"
        )

        if not response.success:
            raise HTTPException(status_code=500, detail=response.error)

        return {
            "success": True,
            "task": response.data,
            "metadata": response.metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quick task: {str(e)}")

@router.get("/{habit_id}/performance-analysis")
async def analyze_performance(
    habit_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Analyze habit performance and provide insights
    """
    try:
        # Get habit details
        habit = await crud.get_habit(db=db, habit_id=habit_id, user_id=current_user.id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")

        # Get performance history
        performance_history = await crud.get_performance_history(
            db=db,
            user_id=current_user.id,
            habit_id=habit_id,
            days=30
        )

        # Analyze performance
        ai_orchestrator = get_ai_orchestrator()
        response = await ai_orchestrator.analyze_performance_trends(
            habit_name=habit.name,
            performance_history=performance_history,
            language="en"  # TODO: Get from user preferences
        )

        if not response.success:
            raise HTTPException(status_code=500, detail=response.error)

        return {
            "success": True,
            "analysis": response.data,
            "metadata": response.metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze performance: {str(e)}")

@router.get("/{habit_id}/improvement-suggestions")
async def get_improvement_suggestions(
    habit_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get AI-powered improvement suggestions for the habit
    """
    try:
        # Get habit details
        habit = await crud.get_habit(db=db, habit_id=habit_id, user_id=current_user.id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")

        # Get performance history
        performance_history = await crud.get_performance_history(
            db=db,
            user_id=current_user.id,
            habit_id=habit_id,
            days=30
        )

        # Generate suggestions
        ai_orchestrator = get_ai_orchestrator()
        response = await ai_orchestrator.suggest_habit_improvements(
            habit_name=habit.name,
            habit_description=habit.description or "",
            performance_history=performance_history,
            language="en"  # TODO: Get from user preferences
        )

        if not response.success:
            raise HTTPException(status_code=500, detail=response.error)

        return {
            "success": True,
            "suggestions": response.data,
            "metadata": response.metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")

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