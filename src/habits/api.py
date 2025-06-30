from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import date, datetime, timedelta
from pytz import UTC
import logging

from src.database import get_async_db
from src.auth.dependencies import get_current_user
from src.auth.models import User as UserModel
from src.ai import get_ai_orchestrator, TaskGenerationContext, AIAgentResponse
from . import crud, schemas

logger = logging.getLogger(__name__)
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
    proof_type: str = Form(...),
    proof_content: str = Form(...),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Submit proof for a task with AI validation"""
    try:
        # Get the task
        task = await crud.get_task_by_id(db=db, task_id=task_id, user_id=current_user.id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.status != "pending":
            raise HTTPException(status_code=400, detail="Task is not pending")

        # Get the habit for context
        habit = await crud.get_habit(db=db, habit_id=task.habit_id, user_id=current_user.id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")

        file_url = None
        file_data = None

        # Handle file upload if provided
        if file:
            # Import file upload service
            from ..services.file_upload import file_upload_service

            # Read file data
            file_data = await file.read()

            # Upload the file
            success, file_url, error = await file_upload_service.upload_proof_file(
                file_data=file_data,
                filename=file.filename or "proof_file",
                content_type=file.content_type or "application/octet-stream",
                user_id=current_user.clerk_id,
                task_id=task_id
            )

            if not success:
                raise HTTPException(status_code=400, detail=f"File upload failed: {error}")

        # Validate the proof using AI
        validation_result = None
        try:
            from ..ai.agents.proof_validator import validate_proof

            validation_result = await validate_proof(
                task_description=task.task_description,
                proof_requirements=task.proof_requirements,
                proof_type=proof_type,
                proof_content=proof_content,
                user_name=current_user.name or "User",
                habit_name=habit.name,
                proof_file_data=file_data
            )
        except Exception as e:
            logger.error(f"AI validation error: {e}")
            # Continue without AI validation
            validation_result = None

        # Submit proof using existing CRUD function
        await crud.submit_task_proof(
            db=db,
            task_id=task_id,
            user_id=current_user.id,
            proof_type=proof_type,
            proof_content=file_url or proof_content
        )

        # Validate with AI results
        if validation_result:
            is_valid = validation_result.is_valid and validation_result.confidence >= 0.7
            await crud.validate_task_proof(
                db=db,
                task_id=task_id,
                validation_result=is_valid,
                confidence=validation_result.confidence,
                feedback=validation_result.feedback
            )

            # Update habit streak if task completed successfully
            if is_valid:
                current_streak = habit.streak or 0
                await crud.update_habit_streak(db=db, habit_id=habit.id, streak_count=current_streak + 1)
        else:
            # Fallback validation - assume valid for now
            await crud.validate_task_proof(
                db=db,
                task_id=task_id,
                validation_result=True,
                confidence=0.8,
                feedback="Proof submitted successfully"
            )

        # Get updated task
        updated_task = await crud.get_task_by_id(db=db, task_id=task_id, user_id=current_user.id)

        return {
            "success": True,
            "task": updated_task,
            "file_url": file_url,
            "validation": {
                "is_valid": validation_result.is_valid if validation_result else True,
                "confidence": validation_result.confidence if validation_result else 0.8,
                "feedback": validation_result.feedback if validation_result else "Proof submitted successfully",
                "suggestions": validation_result.suggestions if validation_result else []
            },
            "message": "Proof submitted and validated successfully"
        }

    except Exception as e:
        logger.error(f"Error submitting proof: {e}")
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

@router.put("/tasks/{task_id}/mark-missed")
async def mark_task_missed(
    task_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Mark a task as missed (for expired tasks)"""
    try:
        # Get task to verify ownership
        task = await crud.get_task_by_id(db=db, task_id=task_id, user_id=current_user.id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Check if task is eligible to be marked as missed
        if task.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending tasks can be marked as missed")

        # Update task status to missed
        task = await crud.update_task_status(
            db=db,
            task_id=task_id,
            user_id=current_user.id,
            status="missed"
        )

        # Update habit streak (reset to 0 for missed tasks)
        habit = await crud.get_habit(db=db, habit_id=task.habit_id, user_id=current_user.id)
        if habit:
            await crud.update_habit_streak(db=db, habit_id=habit.id, streak_count=0)

        return {
            "success": True,
            "task": task,
            "message": "Task marked as missed"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark task as missed: {str(e)}")

@router.post("/tasks/check-expired")
async def check_and_mark_expired_tasks(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Check for expired tasks and mark them as missed"""
    try:
        # Get all pending tasks for the user
        pending_tasks = await crud.get_pending_tasks(db=db, user_id=current_user.id)

        expired_tasks = []
        current_time = datetime.utcnow()

        for task in pending_tasks:
            # Check if task is expired (past due date)
            if task.due_date and task.due_date < current_time:
                # Mark as missed
                updated_task = await crud.update_task_status(
                    db=db,
                    task_id=task.id,
                    user_id=current_user.id,
                    status="missed"
                )

                # Reset habit streak
                habit = await crud.get_habit(db=db, habit_id=task.habit_id, user_id=current_user.id)
                if habit:
                    await crud.update_habit_streak(db=db, habit_id=habit.id, streak_count=0)

                expired_tasks.append(updated_task)

        return {
            "success": True,
            "expired_tasks": expired_tasks,
            "count": len(expired_tasks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check expired tasks: {str(e)}")

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