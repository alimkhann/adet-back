import logging
from typing import Optional, Dict, Any
from datetime import datetime

from ..gemini_client import get_gemini_client
from ..schemas import TaskValidationResult

logger = logging.getLogger(__name__)

class ProofValidatorAgent:
    """
    AI Agent for validating task proof submissions
    Uses Gemini to analyze proof content and determine if it validates the task completion
    """

    def __init__(self):
        self.gemini_client = get_gemini_client()

    async def validate_proof(
        self,
        task_description: str,
        proof_requirements: str,
        proof_type: str,
        proof_content: str,
        user_name: str = "User",
        habit_name: str = "",
        proof_file_data: Optional[bytes] = None
    ) -> TaskValidationResult:
        """
        Validate proof submission against task requirements

        Args:
            task_description: The task that was supposed to be completed
            proof_requirements: What proof was required
            proof_type: Type of proof (photo, video, audio, text)
            proof_content: Text content or description of proof
            user_name: Name of the user (for personalization)
            habit_name: Name of the habit (for context)
            proof_file_data: Binary data of uploaded file (if any)

        Returns:
            TaskValidationResult with validation outcome
        """
        try:
            logger.info(f"Validating {proof_type} proof for task: {task_description[:50]}...")

            # Create validation prompt
            prompt = self._create_validation_prompt(
                task_description=task_description,
                proof_requirements=proof_requirements,
                proof_type=proof_type,
                proof_content=proof_content,
                user_name=user_name,
                habit_name=habit_name
            )

            # Generate validation using structured response
            response = await self.gemini_client.generate_structured_response(
                prompt=prompt,
                response_schema=TaskValidationResult,
                temperature=0.3,  # Lower temperature for consistent validation
                system_prompt=self._get_validation_system_prompt()
            )

            logger.info(f"Proof validation completed: {'Valid' if response.is_valid else 'Invalid'} (confidence: {response.confidence:.2f})")

            return response

        except Exception as e:
            logger.error(f"Error validating proof: {str(e)}")
            # Return a fallback validation result
            return TaskValidationResult(
                is_valid=False,
                confidence=0.0,
                feedback=f"Unable to validate proof due to technical error: {str(e)}",
                suggestions=["Please try submitting your proof again", "Contact support if the issue persists"]
            )

    def _create_validation_prompt(
        self,
        task_description: str,
        proof_requirements: str,
        proof_type: str,
        proof_content: str,
        user_name: str,
        habit_name: str
    ) -> str:
        """Create the validation prompt for the AI"""

        return f"""
        You are validating a task completion proof for a habit tracking app.

        **Task Details:**
        - Habit: {habit_name}
        - Task: {task_description}
        - Required Proof: {proof_requirements}

        **Submitted Proof:**
        - Type: {proof_type}
        - Content: {proof_content}
        - User: {user_name}

        **Validation Instructions:**
        1. Determine if the submitted proof demonstrates completion of the task
        2. Check if the proof meets the specific requirements stated
        3. Be encouraging but honest in your assessment
        4. Consider the intent and effort, not just perfection
        5. For tiny habits, be more lenient as the goal is building consistency

        **Validation Criteria:**
        - Does the proof show the task was attempted/completed?
        - Does it match the proof requirements?
        - Is there clear evidence of the action described in the task?
        - For photo/video: Can you see the relevant action or result?
        - For audio: Can you hear the relevant activity or description?
        - For text: Does the description indicate task completion?

        **Response Guidelines:**
        - is_valid: true if proof demonstrates task completion, false otherwise
        - confidence: 0.0-1.0 based on clarity and completeness of proof
        - feedback: Encouraging message acknowledging effort and explaining validation
        - suggestions: Helpful tips for better proof next time (if needed)

        Be supportive and focus on progress, not perfection. The goal is to encourage habit formation.
        """

    def _get_validation_system_prompt(self) -> str:
        """Get the system prompt for validation"""
        return """
        You are an AI proof validator for a habit tracking app based on BJ Fogg's Tiny Habits methodology.

        Your role is to:
        1. Validate task completion proofs fairly and encouragingly
        2. Focus on effort and progress over perfection
        3. Provide constructive feedback that motivates continued habit building
        4. Be lenient with tiny habits as the goal is consistency, not perfection
        5. Acknowledge any genuine attempt at the task

        Remember: The goal is to help users build sustainable habits through positive reinforcement.
        """

    async def validate_photo_proof(
        self,
        task_description: str,
        proof_requirements: str,
        image_description: str,
        user_name: str = "User"
    ) -> TaskValidationResult:
        """Specialized validation for photo proofs"""

        prompt = f"""
        Validate this photo proof for task completion:

        Task: {task_description}
        Required: {proof_requirements}
        Photo shows: {image_description}
        User: {user_name}

        Analyze if the photo demonstrates task completion.
        Be encouraging and focus on effort shown.
        """

        try:
            response = await self.gemini_client.generate_structured_response(
                prompt=prompt,
                response_schema=TaskValidationResult,
                temperature=0.3
            )
            return response
        except Exception as e:
            logger.error(f"Error validating photo proof: {str(e)}")
            return TaskValidationResult(
                is_valid=True,  # Be lenient on errors
                confidence=0.5,
                feedback="Photo received! Keep up the great work with your habit.",
                suggestions=[]
            )

    async def validate_text_proof(
        self,
        task_description: str,
        proof_requirements: str,
        text_content: str,
        user_name: str = "User"
    ) -> TaskValidationResult:
        """Specialized validation for text proofs"""

        prompt = f"""
        Validate this text proof for task completion:

        Task: {task_description}
        Required: {proof_requirements}
        User wrote: "{text_content}"
        User: {user_name}

        Determine if the text indicates task completion.
        Be supportive and acknowledge effort.
        """

        try:
            response = await self.gemini_client.generate_structured_response(
                prompt=prompt,
                response_schema=TaskValidationResult,
                temperature=0.3
            )
            return response
        except Exception as e:
            logger.error(f"Error validating text proof: {str(e)}")
            return TaskValidationResult(
                is_valid=True,  # Be lenient on errors
                confidence=0.7,
                feedback=f"Thanks for sharing, {user_name}! Your effort is appreciated.",
                suggestions=[]
            )


# Convenience function for backward compatibility
async def validate_proof(
    task_description: str,
    proof_requirements: str,
    proof_type: str,
    proof_content: str,
    user_name: str = "User",
    habit_name: str = "",
    proof_file_data: Optional[bytes] = None
) -> TaskValidationResult:
    """
    Convenience function to validate proof using the ProofValidatorAgent
    """
    validator = ProofValidatorAgent()
    return await validator.validate_proof(
        task_description=task_description,
        proof_requirements=proof_requirements,
        proof_type=proof_type,
        proof_content=proof_content,
        user_name=user_name,
        habit_name=habit_name,
        proof_file_data=proof_file_data
    )