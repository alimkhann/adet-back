import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..vertex_client import get_vertex_client
from ..schemas import GeneratedTask, AIAgentResponse, TaskGenerationContext
from ..prompts.task_prompts import get_task_generation_prompt, TASK_TEMPLATES

logger = logging.getLogger(__name__)

class TaskGeneratorAgent:
    """
    BJ Fogg's Task Generator Agent
    Creates specific, actionable tasks in Tiny Habits format
    """

    def __init__(self):
        self.vertex_client = get_vertex_client()
        self.language = "en"  # Default language

    async def generate_task(
        self,
        context: TaskGenerationContext,
        calibrated_difficulty: float
    ) -> AIAgentResponse:
        """
        Generate a specific, actionable task using BJ Fogg's Tiny Habits methodology

        Args:
            context: Task generation context with habit and user info
            calibrated_difficulty: Difficulty level from calibrator agent

        Returns:
            AIAgentResponse with generated task
        """
        try:
            logger.info(f"Generating task for habit: {context.habit_name}")

            # Generate prompt
            prompt = get_task_generation_prompt(
                habit_name=context.habit_name,
                habit_description=context.habit_description,
                difficulty_level=calibrated_difficulty,
                proof_style=context.proof_style,
                language=context.user_language
            )

            # Get system prompt for language
            system_prompt = TASK_TEMPLATES.get(context.user_language, TASK_TEMPLATES["en"])["system"]

            # Generate structured response
            response = await self.vertex_client.generate_structured_response(
                prompt=prompt,
                response_schema=GeneratedTask,
                temperature=0.7,  # Higher temperature for creativity
                system_prompt=system_prompt
            )

            logger.info(f"Task generated: {response.task_description[:50]}...")

            return AIAgentResponse(
                success=True,
                data={
                    "task_description": response.task_description,
                    "difficulty_level": response.difficulty_level,
                    "estimated_duration": response.estimated_duration,
                    "success_criteria": response.success_criteria,
                    "celebration_message": response.celebration_message,
                    "easier_alternative": response.easier_alternative,
                    "harder_alternative": response.harder_alternative,
                    "anchor_suggestion": response.anchor_suggestion,
                    "proof_requirements": response.proof_requirements
                },
                metadata={
                    "agent": "task_generator",
                    "habit_name": context.habit_name,
                    "difficulty": calibrated_difficulty,
                    "proof_style": context.proof_style,
                    "language": context.user_language,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error generating task: {str(e)}")
            return AIAgentResponse(
                success=False,
                error=f"Failed to generate task: {str(e)}",
                metadata={
                    "agent": "task_generator",
                    "habit_name": context.habit_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    async def generate_quick_task(
        self,
        habit_name: str,
        difficulty_level: float,
        proof_style: str,
        language: str = "en"
    ) -> AIAgentResponse:
        """
        Generate a quick task without full context (fallback method)
        """
        try:
            # Use template-based generation for quick tasks
            templates = TASK_TEMPLATES.get(language, TASK_TEMPLATES["en"])

            # Simple task generation based on difficulty
            if difficulty_level <= 1.0:
                task_template = "After I [anchor], I will [tiny action]"
                duration = 1
            elif difficulty_level <= 1.5:
                task_template = "After I [anchor], I will [small action]"
                duration = 2
            elif difficulty_level <= 2.0:
                task_template = "After I [anchor], I will [medium action]"
                duration = 5
            else:
                task_template = "After I [anchor], I will [larger action]"
                duration = 10

            # Generate celebration message
            celebrations = templates.get("celebrations", ["Great job!"])
            celebration = celebrations[0] if celebrations else "You did it!"

            return AIAgentResponse(
                success=True,
                data={
                    "task_description": f"Complete your {habit_name} habit",
                    "difficulty_level": difficulty_level,
                    "estimated_duration": duration,
                    "success_criteria": f"Complete the {habit_name} task",
                    "celebration_message": celebration,
                    "easier_alternative": None,
                    "harder_alternative": None,
                    "anchor_suggestion": "After I [choose your anchor]",
                    "proof_requirements": f"Provide {proof_style} proof of completion"
                },
                metadata={
                    "agent": "task_generator",
                    "method": "quick_template",
                    "habit_name": habit_name
                }
            )

        except Exception as e:
            logger.error(f"Error generating quick task: {str(e)}")
            return AIAgentResponse(
                success=False,
                error=f"Failed to generate quick task: {str(e)}",
                metadata={"agent": "task_generator"}
            )

    async def suggest_anchor_habits(
        self,
        habit_name: str,
        user_context: Dict[str, Any],
        language: str = "en"
    ) -> AIAgentResponse:
        """
        Suggest anchor habits for the given habit
        """
        try:
            prompt = f"""
            Suggest 3-5 anchor habits for: {habit_name}

            User context: {user_context}

            Format each anchor as: "After I [specific trigger], I will [tiny behavior]"

            Examples:
            - After I wake up, I will put on my workout clothes
            - After I finish dinner, I will do 2 push-ups
            - After I get home, I will walk around the block once

            Make anchors specific, actionable, and relevant to the habit.
            """

            response = await self.vertex_client.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=300
            )

            return AIAgentResponse(
                success=True,
                data={"anchor_suggestions": response},
                metadata={
                    "agent": "task_generator",
                    "method": "anchor_suggestions",
                    "habit_name": habit_name
                }
            )

        except Exception as e:
            logger.error(f"Error suggesting anchors: {str(e)}")
            return AIAgentResponse(
                success=False,
                error=f"Failed to suggest anchors: {str(e)}",
                metadata={"agent": "task_generator"}
            )

    def _validate_task_quality(
        self,
        task_description: str,
        difficulty_level: float,
        estimated_duration: int
    ) -> Dict[str, Any]:
        """
        Validate task quality based on BJ Fogg principles
        """
        issues = []
        suggestions = []

        # Check if task is specific
        if "will" not in task_description.lower():
            issues.append("Task should use 'will' format")
            suggestions.append("Use format: 'After I [anchor], I will [specific action]'")

        # Check duration vs difficulty
        if difficulty_level <= 1.0 and estimated_duration > 2:
            issues.append("Ultra-tiny tasks should be under 2 minutes")
            suggestions.append("Reduce duration or increase difficulty")

        if difficulty_level <= 1.5 and estimated_duration > 5:
            issues.append("Tiny tasks should be under 5 minutes")
            suggestions.append("Consider breaking into smaller tasks")

        # Check for vague language
        vague_words = ["try", "maybe", "might", "could", "should"]
        if any(word in task_description.lower() for word in vague_words):
            issues.append("Task contains vague language")
            suggestions.append("Use specific, actionable language")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "quality_score": max(0, 10 - len(issues) * 2) / 10
        }