from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import MultipleResultsFound
from typing import List
from datetime import date, datetime
import logging
from sqlalchemy import desc, select

from src.database import get_async_db, get_db
from src.auth.dependencies import get_current_user
from src.auth.models import User as UserModel
from src.ai import get_ai_orchestrator, TaskGenerationContext
from ..ai.agents.proof_validator import validate_proof
from . import crud, schemas
from .models import TaskEntry, Habit, TaskValidation
from ..services.file_upload import file_upload_service
from src.posts.service import PostsService

logger = logging.getLogger(__name__)
router = APIRouter()

def _get_response_message(task_status: str, validation_result) -> str:
    """Get appropriate response message based on validation result"""
    if task_status == "completed":
        return "🎉 Amazing! Your proof was validated successfully. Keep up the great work!"
    elif task_status == "failed":
        return "Your proof couldn't be validated this time. Check the feedback and try again!"
    elif task_status == "pending_review":
        return "Proof submitted! Our AI is temporarily unavailable, so this will be reviewed manually."
    else:
        return "Proof submitted successfully"

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
    user_date: str = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Get today's task for a habit, including latest validation as nested object"""
    # Verify habit exists and belongs to user
    habit = await crud.get_habit(db=db, habit_id=habit_id, user_id=current_user.id)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    from datetime import date
    if user_date:
        try:
            today = date.fromisoformat(user_date)
        except Exception as e:
            logger.warning(f"[API] Invalid user_date '{user_date}': {e}. Falling back to backend date.today() (UTC)")
            today = date.today()
    else:
        logger.warning("[API] No user_date provided. Falling back to backend date.today() (UTC)")
        today = date.today()
    try:
        task = await crud.get_today_task(db=db, habit_id=habit_id, user_id=current_user.id, for_date=today)
    except MultipleResultsFound:
        task = (await db.execute(
            select(TaskEntry)
            .filter(
                TaskEntry.habit_id == habit_id,
                TaskEntry.user_id == current_user.id,
                TaskEntry.assigned_date == today
            )
            .order_by(desc(TaskEntry.created_at))
            .limit(1)
        )).scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="No task found for today")

    # --- Fetch latest validation and attach as .validation ---
    latest_validation = await crud.get_latest_task_validation(db, task.id)
    validation_dict = None
    if latest_validation:
        import json
        suggestions = []
        reasoning = None
        if latest_validation.suggestions:
            try:
                suggestions = json.loads(latest_validation.suggestions)
            except Exception:
                suggestions = []
        if latest_validation.validation_response:
            try:
                resp = json.loads(latest_validation.validation_response)
                reasoning = resp.get("reasoning")
            except Exception:
                reasoning = None
        validation_dict = {
            "is_valid": latest_validation.is_valid,
            "is_nsfw": False,  # Set to False unless you store this
            "confidence": latest_validation.confidence,
            "feedback": latest_validation.feedback,
            "reasoning": reasoning,
            "suggestions": suggestions,
        }

    # Convert task to dict and add validation
    task_dict = task.__dict__.copy()
    task_dict["validation"] = validation_dict

    return task_dict

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
    logger.info(f"[TaskGen] Called for habit_id={habit_id}, user_id={current_user.id}")
    logger.info(f"[TaskGen] Full request body: {task_request}")

    import asyncio
    from datetime import datetime

    try:
        start_time = datetime.utcnow()

        # --- Use user_date for all 'today' logic ---
        from datetime import date
        user_date = None
        if hasattr(task_request, 'user_date') and task_request.user_date:
            try:
                user_date = date.fromisoformat(task_request.user_date)
                logger.info(f"[TaskGen] Using user_date: {user_date}")
            except Exception as e:
                logger.warning(f"[TaskGen] Invalid user_date '{task_request.user_date}': {e}. Falling back to backend date.today() (UTC)")
                user_date = date.today()
        else:
            logger.warning("[TaskGen] No user_date provided. Falling back to backend date.today() (UTC)")
            user_date = date.today()

        # Get habit details
        logger.info(f"[TaskGen] Fetching habit {habit_id} for user {current_user.id}")
        habit = await crud.get_habit(db=db, habit_id=habit_id, user_id=current_user.id)
        if not habit:
            logger.error(f"[TaskGen] Habit {habit_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Habit not found")

        # Check if task already exists for today
        logger.info(f"[TaskGen] Checking for existing task on {user_date}")
        existing_task = await crud.get_today_task(db=db, habit_id=habit_id, user_id=current_user.id, for_date=user_date)
        if existing_task:
            logger.info(f"[TaskGen] Task already exists for user_date {user_date} for habit {habit_id}")
            raise HTTPException(status_code=400, detail="Task already exists for today")

        # Generate task with timeout
        logger.info(f"[TaskGen] Starting AI task generation (timeout: 45s)")
        try:
            task_entry = await asyncio.wait_for(
                crud.generate_and_create_task(
                    db=db,
                    habit=habit,
                    user_id=current_user.id,
                    task_request=task_request,
                    assigned_date=user_date
                ),
                timeout=45.0  # 45 second timeout
            )

            generation_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"[TaskGen] Task generated successfully in {generation_time:.2f}s")
            return {"success": True, "message": "Task generated and created successfully", "task_id": task_entry.id}

        except asyncio.TimeoutError:
            logger.error(f"[TaskGen] Task generation timed out after 45 seconds")
            raise HTTPException(
                status_code=408,
                content={"success": False, "detail": "Task generation timed out. Please try again in a moment."}
            )

    except HTTPException:
        # Re-raise HTTP exceptions as-is (don't wrap in 500)
        raise
    except Exception as e:
        import traceback
        logger.error(f"[TaskGen] Exception: {e}")
        tb = traceback.format_exc()
        logger.error(tb)
        raise HTTPException(status_code=500, content={"success": False, "detail": f"Failed to generate and create task: {str(e)}"})

@router.post("/tasks/{task_id}/submit-proof")
async def submit_task_proof(
    task_id: int,
    request: Request,
    proof_type: Optional[str] = Form(None),
    proof_content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_current_user),
):
    """
    Submit proof for a task and run AI validation BEFORE saving file permanently.
    Accepts both JSON and form-data for proof_type and proof_content.
    """
    # --- PATCH: Accept JSON or form-data ---
    json_proof_type = None
    json_proof_content = None
    if request.headers.get("content-type", "").startswith("application/json"):
        data = await request.json()
        json_proof_type = data.get("proof_type")
        json_proof_content = data.get("proof_content")
    # Prefer form-data if present, else use JSON
    effective_proof_type = proof_type or json_proof_type
    effective_proof_content = proof_content or json_proof_content
    # --- END PATCH ---
    validation_result = None
    file_url: str | None = None
    file_data: bytes | None = None

    # 1. Pre-flight checks
    task = await db.execute(
        select(TaskEntry).where(
            TaskEntry.id == task_id, TaskEntry.user_id == current_user.id
        )
    )
    task = task.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ("pending", "failed") or (task.status == "failed" and getattr(task, "attempts_left", 0) == 0):
        raise HTTPException(status_code=400, detail="Task is not available for proof submission")

    habit = await db.execute(select(Habit).where(Habit.id == task.habit_id))
    habit = habit.scalars().first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    # 2. Read file (but do NOT save yet)
    if file:
        file_data = await file.read()
    else:
        file_data = None

    # 3. Run AI validation (including NSFW check)
    try:
        validation_result = await validate_proof(
            task_description=task.task_description,
            proof_requirements=task.proof_requirements,
            proof_type=effective_proof_type,
            proof_content=effective_proof_content,
            user_name=current_user.username or "User",
            habit_name=habit.name,
            proof_file_data=file_data,
        )
    except Exception as ai_err:
        validation_result = None

    # 4. Save file to Azure ONLY if valid and not NSFW
    is_valid = False
    is_nsfw = False
    confidence = 0.0
    feedback = ""
    reasoning = None
    suggestions = []
    if validation_result:
        is_valid = getattr(validation_result, "is_valid", False)
        is_nsfw = getattr(validation_result, "is_nsfw", False)
        confidence = getattr(validation_result, "confidence", 0.0)
        feedback = getattr(validation_result, "feedback", "")
        reasoning = getattr(validation_result, "reasoning", None)
        suggestions = getattr(validation_result, "suggestions", [])

    if file_data and is_valid and not is_nsfw:
        ok, file_url, err = await file_upload_service.upload_proof_file(
            file_data=file_data,
            filename=file.filename or "proof_file",
            content_type=file.content_type or "application/octet-stream",
            user_id=current_user.clerk_id,
            task_id=task_id,
        )
        if not ok:
            raise HTTPException(status_code=400, detail=f"File upload failed: {err}")
    else:
        file_url = None

    # 5. Update task and DB
    task.proof_type = effective_proof_type
    if effective_proof_type == "text":
        task.proof_content = effective_proof_content
    else:
        task.proof_content = file_url or effective_proof_content
    if validation_result:
        task.proof_validation_result = validation_result.is_valid
        task.proof_validation_confidence = validation_result.confidence
        task.proof_feedback = validation_result.feedback
        if validation_result.is_valid and validation_result.confidence >= 0.7:
            task.status = "completed"
            task.completed_at = datetime.utcnow()
        else:
            # Failed validation: decrement attempts_left, reset to pending if attempts remain
            if hasattr(task, "attempts_left") and task.attempts_left is not None:
                task.attempts_left = max(task.attempts_left - 1, 0)
                if task.attempts_left > 0:
                    task.status = "pending"
                else:
                    task.status = "failed"
            else:
                task.status = "failed"
    else:  # AI unavailable
        task.proof_validation_result = None
        task.proof_validation_confidence = 0.5
        task.proof_feedback = (
            "Proof submitted. AI validation temporarily unavailable – manual review required."
        )
        task.status = "pending_review"

    # Create or update TaskValidation row only when AI produced a result
    if validation_result:
        # Try to find existing TaskValidation for this task
        existing_validation = await db.execute(
            select(TaskValidation).where(TaskValidation.task_entry_id == task.id)
        )
        existing_validation = existing_validation.scalars().first()
        if existing_validation:
            # Update existing row
            existing_validation.is_valid = is_valid
            existing_validation.confidence = confidence
            existing_validation.feedback = feedback
            existing_validation.suggestions = json.dumps(suggestions)
            existing_validation.validation_model = "gemini-1.5-pro"
            existing_validation.validation_prompt = "AI proof validation"
            existing_validation.validation_response = json.dumps({
                "reasoning": reasoning,
                "confidence": confidence,
            })
        else:
            db.add(
                TaskValidation(
                    task_entry_id=task.id,
                    is_valid=is_valid,
                    confidence=confidence,
                    feedback=feedback,
                    suggestions=json.dumps(suggestions),
                    validation_model="gemini-1.5-pro",
                    validation_prompt="AI proof validation",
                    validation_response=json.dumps({
                        "reasoning": reasoning,
                        "confidence": confidence,
                    }),
                )
            )

    await db.commit()
    await db.refresh(task)

    # --- Auto-create private post after successful proof submission ---
    auto_created_post = None
    if task.status == "completed":
        try:
            if effective_proof_type == "text":
                optimized_urls = [task.proof_content] if task.proof_content else []
            else:
                optimized_urls = [file_url] if file_url else []
            post = await PostsService.create_post_from_proof(
                db=db,
                user_id=current_user.id,
                habit_id=task.habit_id,
                proof_urls=optimized_urls,
                proof_type=effective_proof_type,
                description=f"Completed: {task.task_description}",
                privacy="private",
                assigned_date=task.assigned_date,  # Always pass assigned_date
                proof_content=task.proof_content if effective_proof_type == "text" else None
            )
            auto_created_post = {
                "id": post.id,
                "privacy": post.privacy.value if hasattr(post.privacy, 'value') else post.privacy,
                "description": post.description,
                "created_at": post.created_at.isoformat() if hasattr(post, 'created_at') else None
            }
            # Include proof_content for text posts
            if post.proof_type == "text":
                auto_created_post["proof_content"] = post.proof_content
            logger.info(f"Auto-created private post {post.id} for user {current_user.id} after proof submission")
        except Exception as e:
            logger.error(f"Failed to auto-create post after proof: {e}")

    # 6. Build response
    response = {
        "success": task.status == "completed",
        "task": {
            "id": task.id,
            "status": task.status,
            "proof_type": task.proof_type,
            "proof_content": task.proof_content,
            "proof_validation_result": task.proof_validation_result,
            "proof_validation_confidence": task.proof_validation_confidence,
            "proof_feedback": task.proof_feedback,
            "completed_at": (
                task.completed_at.isoformat() if task.completed_at else None
            ),
            "celebration_message": (
                task.celebration_message if task.status == "completed" else None
            ),
            "attempts_left": task.attempts_left,
        },
        "file_url": file_url,
        "validation": {
            "is_valid": is_valid,
            "is_nsfw": is_nsfw,
            "confidence": confidence,
            "feedback": feedback,
            "reasoning": reasoning,
            "suggestions": suggestions,
        },
        "message": _get_response_message(task.status, validation_result),
    }
    if auto_created_post:
        response["auto_created_post"] = auto_created_post
    return JSONResponse(status_code=200, content=response)

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
            user_freezers = await crud.get_streak_freezers_by_user(db=db, user_id=current_user.id)
            if user_freezers > 0:
                await crud.decrement_streak_freezer_for_user(db=db, user_id=current_user.id)
                # Do not reset streak
            else:
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
                    user_freezers = await crud.get_streak_freezers_by_user(db=db, user_id=current_user.id)
                    if user_freezers > 0:
                        await crud.decrement_streak_freezer_for_user(db=db, user_id=current_user.id)
                        # Do not reset streak
                    else:
                        await crud.update_habit_streak(db=db, habit_id=habit.id, streak_count=0)

                expired_tasks.append(updated_task)

        return {
            "success": True,
            "expired_tasks": expired_tasks,
            "count": len(expired_tasks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check expired tasks: {str(e)}")

@router.post("/habits/{habit_id}/mark-missed-no-task")
async def mark_habit_missed_no_task(
    habit_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Mark a habit as missed when no task was generated but window expired"""
    try:
        # Get habit to verify ownership
        habit = await crud.get_habit(db=db, habit_id=habit_id, user_id=current_user.id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")

        # Check if there's already a task for today
        from datetime import date
        today = date.today()
        existing_task = await crud.get_today_task(db=db, habit_id=habit_id, user_id=current_user.id, for_date=today)

        if existing_task:
            raise HTTPException(status_code=400, detail="Task already exists for today")

        # Handle streak freezer logic for missed habit (no task generated)
        user_freezers = await crud.get_streak_freezers_by_user(db=db, user_id=current_user.id)
        if user_freezers > 0:
            await crud.decrement_streak_freezer_for_user(db=db, user_id=current_user.id)
            logger.info(f"Consumed streak freezer for user {current_user.id}, habit {habit_id}. Freezers remaining: {user_freezers - 1}")
        else:
            await crud.update_habit_streak(db=db, habit_id=habit.id, streak_count=0)
            logger.info(f"Reset streak to 0 for user {current_user.id}, habit {habit_id}")

        return {
            "success": True,
            "message": "Habit marked as missed (no task generated)",
            "freezers_consumed": user_freezers > 0,
            "streak_reset": user_freezers == 0
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark habit as missed: {str(e)}")

@router.get("/tasks/{task_id}/proof-url")
async def get_fresh_proof_url(
    task_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Return a fresh signed (SAS) URL for the proof image of a given task.
    """
    task = await db.execute(
        select(TaskEntry).where(TaskEntry.id == task_id, TaskEntry.user_id == current_user.id)
    )
    task = task.scalars().first()
    if not task or not task.proof_content:
        raise HTTPException(status_code=404, detail="No proof found for this task.")
    signed_url = file_upload_service.generate_signed_url(task.proof_content, container=file_upload_service.proof_container_name)
    return {"url": signed_url}

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
            days=7,
            reference_date=task_request.user_date if task_request.user_date else date.today()
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
            days=30,
            reference_date=date.today()
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
            days=30,
            reference_date=date.today()
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
async def get_today_motivation_entry(
    habit_id: str,
    user_date: str = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    from datetime import date
    if user_date:
        try:
            today = date.fromisoformat(user_date)
        except Exception as e:
            logger.warning(f"[API] Invalid user_date '{user_date}': {e}. Falling back to backend date.today() (UTC)")
            today = date.today()
    else:
        logger.warning("[API] No user_date provided. Falling back to backend date.today() (UTC)")
        today = date.today()
    user_id = _get_user_id(current_user)
    entry = await crud.get_motivation_entry(db, user_id, habit_id, today)
    if not entry:
        raise HTTPException(status_code=404, detail="No motivation entry for today.")
    return entry

@router.patch("/{habit_id}/motivation/today", response_model=schemas.MotivationEntryRead)
async def update_today_motivation_entry(
    habit_id: str,
    entry: schemas.MotivationEntryCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    user_id = _get_user_id(current_user)
    updated = await crud.update_motivation_entry(db, user_id, habit_id, entry.date, entry.level)
    if not updated:
        raise HTTPException(status_code=404, detail="No motivation entry for today.")
    return updated

@router.post("/{habit_id}/ability", response_model=schemas.AbilityEntryRead)
async def submit_ability_entry(habit_id: str, entry: schemas.AbilityEntryCreate, db: AsyncSession = Depends(get_async_db), current_user: UserModel = Depends(get_current_user)):
    today = entry.date
    user_id = _get_user_id(current_user)
    existing = await crud.get_ability_entry(db, user_id, habit_id, today)
    if existing:
        raise HTTPException(status_code=400, detail="Ability entry already exists for today.")
    return await crud.create_ability_entry(db, user_id, entry)

@router.get("/{habit_id}/ability/today", response_model=schemas.AbilityEntryRead)
async def get_today_ability_entry(
    habit_id: str,
    user_date: str = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    from datetime import date
    if user_date:
        try:
            today = date.fromisoformat(user_date)
        except Exception as e:
            logger.warning(f"[API] Invalid user_date '{user_date}': {e}. Falling back to backend date.today() (UTC)")
            today = date.today()
    else:
        logger.warning("[API] No user_date provided. Falling back to backend date.today() (UTC)")
        today = date.today()
    user_id = _get_user_id(current_user)
    entry = await crud.get_ability_entry(db, user_id, habit_id, today)
    if not entry:
        raise HTTPException(status_code=404, detail="No ability entry for today.")
    return entry

# --- Streak Freezer Endpoints (per user) ---
@router.get("/user/streak-freezers", response_model=schemas.UserStreakFreezers)
async def get_user_streak_freezers(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    count = await crud.get_streak_freezers_by_user(db=db, user_id=current_user.id)
    return {"streak_freezers": count}

@router.post("/user/use-streak-freezer", response_model=schemas.UserStreakFreezers)
async def use_user_streak_freezer(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    count = await crud.get_streak_freezers_by_user(db=db, user_id=current_user.id)
    if count <= 0:
        raise HTTPException(status_code=400, detail="No streak freezers available")
    await crud.decrement_streak_freezer_for_user(db=db, user_id=current_user.id)
    return {"streak_freezers": count - 1}

@router.post("/user/award-streak-freezer", response_model=schemas.UserStreakFreezers)
async def award_user_streak_freezer(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    count = await crud.get_streak_freezers_by_user(db=db, user_id=current_user.id)
    await crud.increment_streak_freezer_for_user(db=db, user_id=current_user.id)
    return {"streak_freezers": count + 1}