"""
AI Module for Adet Habit Tracking App
BJ Fogg's Tiny Habits methodology implementation with Vertex AI
"""

from .orchestrator import get_ai_orchestrator, AIOrchestrator
from .vertex_client import get_vertex_client, VertexAIClient
from .schemas import (
    AIAgentResponse,
    TaskGenerationContext,
    GeneratedTask,
    DifficultyResponse,
    MotivationalResponse,
    ContextAnalysis,
    TaskValidationResult
)
from .agents.difficulty_calibrator import DifficultyCalibratorAgent
from .agents.task_generator import TaskGeneratorAgent

__all__ = [
    # Main orchestrator
    "get_ai_orchestrator",
    "AIOrchestrator",

    # Vertex AI client
    "get_vertex_client",
    "VertexAIClient",

    # Schemas
    "AIAgentResponse",
    "TaskGenerationContext",
    "GeneratedTask",
    "DifficultyResponse",
    "MotivationalResponse",
    "ContextAnalysis",
    "TaskValidationResult",

    # Agents
    "DifficultyCalibratorAgent",
    "TaskGeneratorAgent"
]