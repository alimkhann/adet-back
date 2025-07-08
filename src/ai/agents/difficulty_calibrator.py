import logging
from typing import List, Dict, Any
from datetime import datetime

from ..gemini_client import get_gemini_client
from ..schemas import DifficultyResponse, AIAgentResponse
from ..prompts.difficulty_prompts import get_difficulty_prompt, DIFFICULTY_PROMPTS

logger = logging.getLogger(__name__)

class DifficultyCalibratorAgent:
    """
    BJ Fogg's Difficulty Calibrator Agent
    Uses B=MAT formula to determine optimal task difficulty
    """

    def __init__(self):
        self.gemini_client = get_gemini_client()
        self.language = "en"  # Default language

    async def calibrate_difficulty(
        self,
        habit_name: str,
        base_difficulty: str,
        motivation_level: str,
        ability_level: str,
        recent_performance: List[Dict[str, Any]] = None,
        language: str = "en",
        streak: int = 0,
        recent_feedback: str = ""
    ) -> AIAgentResponse:
        """
        Calibrate task difficulty using BJ Fogg's B=MAT methodology
        Now also considers streak and recent feedback.
        """
        try:
            logger.info(f"Calibrating difficulty for habit: {habit_name}")

            # Generate prompt
            prompt = get_difficulty_prompt(
                habit_name=habit_name,
                base_difficulty=base_difficulty,
                motivation_level=motivation_level,
                ability_level=ability_level,
                recent_performance=recent_performance or [],
                language=language,
                streak=streak,
                recent_feedback=recent_feedback
            )

            # Get system prompt for language
            system_prompt = DIFFICULTY_PROMPTS.get(language, DIFFICULTY_PROMPTS["en"])["system"]

            # Generate structured response
            response = await self.gemini_client.generate_structured_response(
                prompt=prompt,
                response_schema=DifficultyResponse,
                temperature=0.3,  # Low temperature for consistent calibration
                system_prompt=system_prompt
            )

            logger.info(f"Difficulty calibrated: {response.difficulty} (confidence: {response.confidence})")

            return AIAgentResponse(
                success=True,
                data={
                    "difficulty": response.difficulty,
                    "reasoning": response.reasoning,
                    "confidence": response.confidence
                },
                metadata={
                    "agent": "difficulty_calibrator",
                    "habit_name": habit_name,
                    "base_difficulty": base_difficulty,
                    "motivation_level": motivation_level,
                    "ability_level": ability_level,
                    "streak": streak,
                    "recent_feedback": recent_feedback,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error calibrating difficulty: {str(e)}")
            return AIAgentResponse(
                success=False,
                error=f"Failed to calibrate difficulty: {str(e)}",
                metadata={
                    "agent": "difficulty_calibrator",
                    "habit_name": habit_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    async def get_difficulty_insights(
        self,
        habit_name: str,
        performance_history: List[Dict[str, Any]],
        language: str = "en"
    ) -> AIAgentResponse:
        """
        Analyze performance history to provide difficulty insights
        """
        try:
            if not performance_history:
                return AIAgentResponse(
                    success=True,
                    data={"insights": "No performance history available"},
                    metadata={"agent": "difficulty_calibrator"}
                )

            # Calculate success rates by difficulty
            difficulty_stats = {}
            for entry in performance_history:
                difficulty = entry.get("difficulty", 1.0)
                completed = entry.get("completed", False)

                if difficulty not in difficulty_stats:
                    difficulty_stats[difficulty] = {"total": 0, "completed": 0}

                difficulty_stats[difficulty]["total"] += 1
                if completed:
                    difficulty_stats[difficulty]["completed"] += 1

            # Generate insights
            insights = []
            for difficulty, stats in difficulty_stats.items():
                success_rate = stats["completed"] / stats["total"]
                if success_rate < 0.5:
                    insights.append(f"Difficulty {difficulty}: Low success rate ({success_rate:.1%}) - consider reducing")
                elif success_rate > 0.8:
                    insights.append(f"Difficulty {difficulty}: High success rate ({success_rate:.1%}) - can increase slightly")
                else:
                    insights.append(f"Difficulty {difficulty}: Good success rate ({success_rate:.1%}) - maintain level")

            return AIAgentResponse(
                success=True,
                data={"insights": insights},
                metadata={
                    "agent": "difficulty_calibrator",
                    "habit_name": habit_name,
                    "analysis_type": "performance_insights"
                }
            )

        except Exception as e:
            logger.error(f"Error analyzing performance: {str(e)}")
            return AIAgentResponse(
                success=False,
                error=f"Failed to analyze performance: {str(e)}",
                metadata={"agent": "difficulty_calibrator"}
            )

    def _calculate_bmat_score(
        self,
        motivation_level: str,
        ability_level: str,
        base_difficulty: str
    ) -> float:
        """
        Calculate B=MAT score (Behavior = Motivation × Ability × Trigger)
        """
        motivation_map = {"low": 0.3, "medium": 0.6, "high": 0.9}
        ability_map = {"hard": 0.3, "medium": 0.6, "easy": 0.9}
        difficulty_map = {"easy": 1.0, "medium": 1.5, "hard": 2.0}

        motivation = motivation_map.get(motivation_level, 0.6)
        ability = ability_map.get(ability_level, 0.6)
        trigger = difficulty_map.get(base_difficulty, 1.5)

        return motivation * ability * trigger