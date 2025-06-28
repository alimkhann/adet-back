import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from .gemini_client import get_gemini_client
from .schemas import (
    AIAgentResponse,
    TaskGenerationContext,
    GeneratedTask,
    DifficultyResponse
)
from .agents.difficulty_calibrator import DifficultyCalibratorAgent
from .agents.task_generator import TaskGeneratorAgent

logger = logging.getLogger(__name__)

class AIOrchestrator:
    """
    Orchestrates AI agents for task generation and management
    Coordinates Difficulty Calibrator and Task Generator agents
    """

    def __init__(self):
        self.difficulty_agent = DifficultyCalibratorAgent()
        self.task_agent = TaskGeneratorAgent()
        self.gemini_client = get_gemini_client()

    async def generate_personalized_task(
        self,
        context: TaskGenerationContext,
        recent_performance: List[Dict[str, Any]] = None
    ) -> AIAgentResponse:
        """
        Generate a personalized task using the full AI pipeline

        Args:
            context: Task generation context
            recent_performance: Recent task completion history

        Returns:
            AIAgentResponse with generated task and metadata
        """
        try:
            logger.info(f"Starting personalized task generation for habit: {context.habit_name}")

            # Step 1: Calibrate difficulty using B=MAT
            difficulty_response = await self.difficulty_agent.calibrate_difficulty(
                habit_name=context.habit_name,
                base_difficulty=context.base_difficulty,
                motivation_level=context.motivation_level,
                ability_level=context.ability_level,
                recent_performance=recent_performance,
                language=context.user_language
            )

            if not difficulty_response.success:
                logger.error(f"Difficulty calibration failed: {difficulty_response.error}")
                return difficulty_response

            calibrated_difficulty = difficulty_response.data["difficulty"]
            logger.info(f"Difficulty calibrated to: {calibrated_difficulty}")

            # Step 2: Generate task with calibrated difficulty
            task_response = await self.task_agent.generate_task(
                context=context,
                calibrated_difficulty=calibrated_difficulty
            )

            if not task_response.success:
                logger.error(f"Task generation failed: {task_response.error}")
                return task_response

            # Step 3: Combine responses and add orchestration metadata
            combined_data = {
                **task_response.data,
                "calibration_metadata": {
                    "original_difficulty": context.base_difficulty,
                    "calibrated_difficulty": calibrated_difficulty,
                    "calibration_reasoning": difficulty_response.data["reasoning"],
                    "calibration_confidence": difficulty_response.data["confidence"]
                }
            }

            return AIAgentResponse(
                success=True,
                data=combined_data,
                metadata={
                    "orchestrator": "ai_orchestrator",
                    "pipeline_steps": ["difficulty_calibration", "task_generation"],
                    "habit_name": context.habit_name,
                    "final_difficulty": calibrated_difficulty,
                    "timestamp": datetime.utcnow().isoformat(),
                    "agents_used": ["difficulty_calibrator", "task_generator"]
                }
            )

        except Exception as e:
            logger.error(f"Error in AI orchestration: {str(e)}")
            return AIAgentResponse(
                success=False,
                error=f"AI orchestration failed: {str(e)}",
                metadata={
                    "orchestrator": "ai_orchestrator",
                    "habit_name": context.habit_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    async def generate_quick_task(
        self,
        habit_name: str,
        base_difficulty: str,
        proof_style: str,
        language: str = "en"
    ) -> AIAgentResponse:
        """
        Generate a quick task without full context (fallback method)
        """
        try:
            logger.info(f"Generating quick task for habit: {habit_name}")

            # Use simple difficulty mapping
            difficulty_map = {"easy": 1.0, "medium": 1.5, "hard": 2.0}
            difficulty_level = difficulty_map.get(base_difficulty, 1.5)

            # Generate quick task
            response = await self.task_agent.generate_quick_task(
                habit_name=habit_name,
                difficulty_level=difficulty_level,
                proof_style=proof_style,
                language=language
            )

            if response.success:
                response.metadata["orchestrator"] = "ai_orchestrator"
                response.metadata["method"] = "quick_generation"

            return response

        except Exception as e:
            logger.error(f"Error generating quick task: {str(e)}")
            return AIAgentResponse(
                success=False,
                error=f"Quick task generation failed: {str(e)}",
                metadata={"orchestrator": "ai_orchestrator"}
            )

    async def analyze_performance_trends(
        self,
        habit_name: str,
        performance_history: List[Dict[str, Any]],
        language: str = "en"
    ) -> AIAgentResponse:
        """
        Analyze performance trends and provide insights
        """
        try:
            logger.info(f"Analyzing performance trends for habit: {habit_name}")

            # Get difficulty insights
            difficulty_insights = await self.difficulty_agent.get_difficulty_insights(
                habit_name=habit_name,
                performance_history=performance_history,
                language=language
            )

            # Generate performance summary
            if performance_history:
                total_tasks = len(performance_history)
                completed_tasks = sum(1 for p in performance_history if p.get("completed", False))
                success_rate = completed_tasks / total_tasks

                # Calculate streak
                current_streak = 0
                for entry in reversed(performance_history):
                    if entry.get("completed", False):
                        current_streak += 1
                    else:
                        break

                summary = {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "success_rate": success_rate,
                    "current_streak": current_streak,
                    "difficulty_insights": difficulty_insights.data.get("insights", []) if difficulty_insights.success else []
                }
            else:
                summary = {
                    "total_tasks": 0,
                    "completed_tasks": 0,
                    "success_rate": 0.0,
                    "current_streak": 0,
                    "difficulty_insights": ["No performance history available"]
                }

            return AIAgentResponse(
                success=True,
                data=summary,
                metadata={
                    "orchestrator": "ai_orchestrator",
                    "analysis_type": "performance_trends",
                    "habit_name": habit_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error analyzing performance trends: {str(e)}")
            return AIAgentResponse(
                success=False,
                error=f"Performance analysis failed: {str(e)}",
                metadata={"orchestrator": "ai_orchestrator"}
            )

    async def suggest_habit_improvements(
        self,
        habit_name: str,
        habit_description: str,
        performance_history: List[Dict[str, Any]],
        language: str = "en"
    ) -> AIAgentResponse:
        """
        Suggest improvements for habit based on performance
        """
        try:
            logger.info(f"Generating improvement suggestions for habit: {habit_name}")

            # Analyze performance
            performance_analysis = await self.analyze_performance_trends(
                habit_name=habit_name,
                performance_history=performance_history,
                language=language
            )

            if not performance_analysis.success:
                return performance_analysis

            # Generate improvement suggestions
            prompt = f"""
            Based on this performance data for the habit "{habit_name}":
            {performance_analysis.data}

            Provide 3-5 specific, actionable suggestions to improve this habit using BJ Fogg's Tiny Habits methodology.

            Focus on:
            1. Making the habit smaller/easier if success rate is low
            2. Better anchor habits
            3. Timing optimization
            4. Environment design
            5. Celebration and motivation

            Format as a list of specific suggestions.
            """

            suggestions_response = await self.gemini_client.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=3000
            )

            return AIAgentResponse(
                success=True,
                data={
                    "performance_summary": performance_analysis.data,
                    "improvement_suggestions": suggestions_response
                },
                metadata={
                    "orchestrator": "ai_orchestrator",
                    "analysis_type": "habit_improvements",
                    "habit_name": habit_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error generating improvement suggestions: {str(e)}")
            return AIAgentResponse(
                success=False,
                error=f"Improvement suggestions failed: {str(e)}",
                metadata={"orchestrator": "ai_orchestrator"}
            )

# Global orchestrator instance
ai_orchestrator: Optional[AIOrchestrator] = None

def get_ai_orchestrator() -> AIOrchestrator:
    """Get or create AI orchestrator instance"""
    global ai_orchestrator
    if ai_orchestrator is None:
        ai_orchestrator = AIOrchestrator()
    return ai_orchestrator