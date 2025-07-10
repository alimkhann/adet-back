from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
import json
from typing import Optional
from ..ai.agents.proof_validator import validate_proof
from ..services.file_upload import file_upload_service
import logging
from ..database import get_db, get_current_user
from ..models import TaskEntry, Habit, TaskValidation
from sqlalchemy.orm import Session
from datetime import datetime

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

@router.post("/tasks/{task_id}/submit-proof")
async def submit_task_proof(
    task_id: int,
    proof_type: str = Form(...),
    proof_content: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Submit proof for a task and get AI validation"""
    try:
        # Get the task
        task = db.query(TaskEntry).filter(
            TaskEntry.id == task_id,
            TaskEntry.user_id == current_user.id
        ).first()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        if task.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is not pending"
            )

        # Get the habit for context
        habit = db.query(Habit).filter(Habit.id == task.habit_id).first()
        if not habit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Habit not found"
            )

        file_url = None
        file_data = None

        # Handle file upload if provided
        if file:
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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File upload failed: {error}"
                )

        # Validate the proof using AI
        try:
            validation_result = await validate_proof(
                task_description=task.task_description,
                proof_requirements=task.proof_requirements,
                proof_type=proof_type,
                proof_content=proof_content,
                user_name=current_user.username or "User",
                habit_name=habit.name,
                proof_file_data=file_data
            )
        except Exception as e:
            logger.error(f"AI validation error: {e}")
            # Continue with manual validation flag
            validation_result = None

        # Update task with proof and validation result
        task.proof_type = proof_type
        task.proof_content = file_url or proof_content

        if validation_result:
            task.proof_validation_result = validation_result.is_valid
            task.proof_validation_confidence = validation_result.confidence
            task.proof_feedback = validation_result.feedback

            # --- ENFORCE: Always set to completed if valid and confident ---
            if validation_result.is_valid and validation_result.confidence >= 0.7:
                task.status = "completed"
                task.completed_at = datetime.now()
                # Do NOT increment habit streak here. Streak is only updated on share.
            else:
                task.status = "failed"
        else:
            # Fallback: mark as needing manual review instead of auto-success
            task.proof_validation_result = None
            task.proof_validation_confidence = 0.5
            task.proof_feedback = "Proof submitted. AI validation temporarily unavailable - manual review required."
            task.status = "pending_review"  # Don't auto-complete without validation

        # --- ENFORCE: Commit after status update ---
        db.commit()
        db.refresh(task)

        # Create validation record
        if validation_result:
            validation_record = TaskValidation(
                task_entry_id=task.id,
                is_valid=validation_result.is_valid,
                confidence=validation_result.confidence,
                feedback=validation_result.feedback,
                suggestions=json.dumps(validation_result.suggestions),
                validation_model="gemini-1.5-pro",
                validation_prompt="AI proof validation",
                validation_response=json.dumps({
                    "reasoning": validation_result.reasoning,
                    "confidence": validation_result.confidence
                })
            )
            db.add(validation_record)

        db.commit()
        db.refresh(task)

        # Prepare response
        response_data = {
            "success": task.status == "completed",
            "task": {
                "id": task.id,
                "status": task.status,
                "proof_type": task.proof_type,
                "proof_content": task.proof_content,
                "proof_validation_result": task.proof_validation_result,
                "proof_validation_confidence": task.proof_validation_confidence,
                "proof_feedback": task.proof_feedback,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "celebration_message": task.celebration_message if task.status == "completed" else None
            },
            "file_url": file_url,
            "validation": {
                "is_valid": validation_result.is_valid if validation_result else None,
                "confidence": validation_result.confidence if validation_result else task.proof_validation_confidence,
                "feedback": validation_result.feedback if validation_result else task.proof_feedback,
                "suggestions": validation_result.suggestions if validation_result else []
            },
            "message": _get_response_message(task.status, validation_result)
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting proof: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit proof: {str(e)}"
        )

@router.get("/tasks/{task_id}/validation")
async def get_task_validation(
    task_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get validation details for a task"""
    try:
        # Get the task
        task = db.query(TaskEntry).filter(
            TaskEntry.id == task_id,
            TaskEntry.user_id == current_user.id
        ).first()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Get validation records
        validations = db.query(TaskValidation).filter(
            TaskValidation.task_entry_id == task_id
        ).order_by(TaskValidation.created_at.desc()).all()

        validation_data = []
        for validation in validations:
            validation_data.append({
                "id": validation.id,
                "is_valid": validation.is_valid,
                "confidence": validation.confidence,
                "feedback": validation.feedback,
                "suggestions": json.loads(validation.suggestions) if validation.suggestions else [],
                "created_at": validation.created_at.isoformat(),
                "validation_model": validation.validation_model
            })

        return {
            "task_id": task.id,
            "task_status": task.status,
            "proof_type": task.proof_type,
            "proof_content": task.proof_content,
            "proof_validation_result": task.proof_validation_result,
            "proof_validation_confidence": task.proof_validation_confidence,
            "proof_feedback": task.proof_feedback,
            "validations": validation_data
        }

    except Exception as e:
        logger.error(f"Error getting task validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get validation: {str(e)}"
        )