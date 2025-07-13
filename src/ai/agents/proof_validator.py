import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from ..gemini_client import get_gemini_client
from ..schemas import TaskValidationResult

# Robust logger config for ProofValidator
logger = logging.getLogger("proof_validator")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

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
        """
        import json
        try:
            logger.info(f"Validating {proof_type} proof for task: {task_description[:50]}...")
            # --- Use Gemini Vision for photo proofs ---
            if proof_type == "photo" and proof_file_data:
                import time
                # --- Concise, safe prompt for validation ---
                prompt = (
                    "You are an AI proof validator for a habit tracking app. "
                    "The user submitted this image as proof for the following task:\n"
                    f"{task_description}\n"
                    "Requirements: " + proof_requirements + "\n"
                    "Please answer:\n"
                    "1. Does the image clearly show the required action or object?\n"
                    "2. Is the image appropriate (not NSFW or offensive)?\n"
                    "Respond in JSON with: "
                    "is_valid (boolean), is_nsfw (boolean), confidence (float 0-1), feedback (string), reasoning (string, optional, max 2 sentences). "
                    "Be concise. Do not describe unrelated details."
                )
                logger.info(f"[ProofValidator] Starting Gemini Vision validation...")
                start_time = time.time()
                loop = asyncio.get_event_loop()
                try:
                    response_text = await asyncio.wait_for(
                        loop.run_in_executor(None, self.gemini_client.analyze_image, proof_file_data, prompt),
                        timeout=20.0
                    )
                    elapsed = time.time() - start_time
                    logger.info(f"[ProofValidator] Gemini Vision validation response: {response_text}")
                except asyncio.TimeoutError:
                    logger.warning("[ProofValidator] Gemini Vision validation timed out after 20s!")
                    return TaskValidationResult(
                        is_valid=False,
                        is_nsfw=False,
                        confidence=0.0,
                        feedback="AI validation timed out. Please try again or use a different image.",
                        reasoning="AI did not respond in time."
                    )
                try:
                    # Strip markdown code fences if present
                    cleaned_response = response_text.strip()
                    if cleaned_response.startswith("```json"):
                        cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()
                    elif cleaned_response.startswith("```"):
                        cleaned_response = cleaned_response.replace("```", "").strip()

                    result = json.loads(cleaned_response)
                    is_valid = bool(result.get("is_valid", False))
                    is_nsfw = bool(result.get("is_nsfw", False))
                    confidence = float(result.get("confidence", 0.0))
                    feedback = str(result.get("feedback", "No feedback provided."))
                    reasoning = result.get("reasoning")
                    suggestions = result.get("suggestions", [])
                    logger.info(f"[ProofValidator] Parsed validation result: valid={is_valid}, nsfw={is_nsfw}, confidence={confidence}")
                    return TaskValidationResult(
                        is_valid=is_valid,
                        is_nsfw=is_nsfw,
                        confidence=confidence,
                        feedback=feedback,
                        reasoning=reasoning,
                        suggestions=suggestions
                    )
                except Exception as e:
                    logger.error(f"Failed to parse Gemini Vision response: {e}\nRaw response: {response_text}")
                    return TaskValidationResult(
                        is_valid=False,
                        is_nsfw=False,
                        confidence=0.0,
                        feedback="Unable to validate proof image due to technical error.",
                        reasoning="AI response could not be parsed."
                    )
            # --- Fallback: text-only validation ---
            prompt = self._create_validation_prompt(
                task_description=task_description,
                proof_requirements=proof_requirements,
                proof_type=proof_type,
                proof_content=proof_content,
                user_name=user_name,
                habit_name=habit_name
            )

            response = await self.gemini_client.generate_structured_response(
                prompt=prompt,
                response_schema=TaskValidationResult,
                temperature=0.3,  # Lower temperature for consistent validation
                system_prompt=self._get_validation_system_prompt()
            )
            logger.info(f"Proof validation (text) completed: {'Valid' if response.is_valid else 'Invalid'} (confidence: {response.confidence:.2f})")
            return response

        except Exception as e:
            logger.error(f"Error validating proof: {e}")
            return TaskValidationResult(
                is_valid=False,
                is_nsfw=False,
                confidence=0.0,
                feedback=f"Unable to validate proof due to technical error: {e}",
                reasoning="Internal error."
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
You are an AI proof validator for a habit tracking app.\n\nTask Details:\n- Habit: {habit_name}\n- Task: {task_description}\n- Required Proof: {proof_requirements}\n\nSubmitted Proof:\n- Type: {proof_type}\n- Content: {proof_content}\n- User: {user_name}\n\nValidation Instructions:\n1. Determine if the submitted proof demonstrates completion of the task\n2. Check if the proof meets the specific requirements stated\n3. Be encouraging but honest in your assessment\n4. Consider the intent and effort, not just perfection\n5. For tiny habits, be more lenient as the goal is building consistency\n6. If the proof is inappropriate (NSFW), set is_nsfw to true.\n\nResponse Guidelines:\n- is_valid: true if proof demonstrates task completion, false otherwise\n- is_nsfw: true if the proof is inappropriate (NSFW), false otherwise\n- confidence: 0.0-1.0 based on clarity and completeness of proof\n- feedback: Encouraging message acknowledging effort and explaining validation\n- reasoning: Short explanation for the validation result (max 2 sentences)\n- suggestions: Helpful tips for better proof next time (if needed)\n\nRespond ONLY with a JSON object. Be concise."
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