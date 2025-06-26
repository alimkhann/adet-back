"""
BJ Fogg Style Prompts for Task Generator Agent
Creating specific, actionable tasks in Tiny Habits format
"""

# System prompt for Task Generator
TASK_GENERATOR_SYSTEM_PROMPT = """You are Dr. BJ Fogg's Tiny Habits task generator. Your mission is to create specific, actionable tasks that feel almost too small to fail.

Core Principles:
1. "After I [anchor], I will [tiny behavior]"
2. Make it specific and actionable
3. Focus on behavior, not outcome
4. Keep it under 30 seconds when possible
5. Make it so small it's almost silly not to do
6. Celebrate every completion

Task Structure:
- Clear, specific action
- Measurable completion criteria
- Appropriate for the difficulty level
- Matches the user's proof style preference
- Includes celebration moment

Remember: The goal is completion, not perfection. Every tiny win builds momentum."""

def get_task_generation_prompt(
    habit_name: str,
    habit_description: str,
    difficulty_level: float,
    proof_style: str,
    anchor_suggestion: str = None,
    language: str = "en"
) -> str:
    """
    Generate task creation prompt in BJ Fogg style
    """

    # Difficulty-based guidance
    if difficulty_level <= 1.0:
        difficulty_guidance = "ULTRA-TINY: Make this so small it's almost automatic. Think 10-30 seconds."
    elif difficulty_level <= 1.5:
        difficulty_guidance = "TINY: BJ Fogg's sweet spot. 30 seconds to 2 minutes. Specific and doable."
    elif difficulty_level <= 2.0:
        difficulty_guidance = "SMALL: Slightly more involved, but still very achievable. 2-5 minutes."
    elif difficulty_level <= 2.5:
        difficulty_guidance = "MEDIUM: More substantial but manageable. 5-15 minutes."
    else:
        difficulty_guidance = "HARD: Significant challenge. Only use when motivation and ability are high."

    # Proof style guidance
    proof_guidance = {
        "photo": "User will take a photo as proof. Task should be visually verifiable.",
        "video": "User will record a video. Task should be observable and brief.",
        "audio": "User will record audio. Task should be audible or describable.",
        "text": "User will write text description. Task should be clearly describable."
    }.get(proof_style, "User will provide text description.")

    # Anchor guidance
    anchor_text = ""
    if anchor_suggestion:
        anchor_text = f"Suggested anchor: '{anchor_suggestion}'"
    else:
        anchor_text = "Consider suggesting an anchor habit (e.g., 'After I wake up', 'After I finish dinner')"

    prompt = f"""
Habit: {habit_name}
Description: {habit_description}

Task Requirements:
- Difficulty Level: {difficulty_level} ({difficulty_guidance})
- Proof Style: {proof_style} ({proof_guidance})
- {anchor_text}

Your Task:
Create a specific, actionable task using BJ Fogg's Tiny Habits methodology.

Requirements:
1. Task Description: Clear, specific action that can be completed
2. Difficulty Level: {difficulty_level} (0.5-3.0 scale)
3. Estimated Duration: Realistic time estimate in minutes
4. Success Criteria: How to know the task is complete
5. Celebration Message: Encouraging message for completion
6. Easier Alternative: If this feels too hard
7. Harder Alternative: If this feels too easy
8. Anchor Suggestion: "After I [anchor], I will [tiny behavior]"
9. Proof Requirements: What proof is needed for {proof_style}

Example Format:
- Task: "After I sit down at my desk, I will open my book to page 1"
- Duration: 30 seconds
- Success: Book is open to page 1
- Celebration: "Hell yeah! You opened that book - momentum started!"

Remember:
- Be specific and actionable
- Make it small enough to guarantee success
- Focus on the behavior, not the outcome
- Include celebration moment
- Provide alternatives for flexibility
"""

    return prompt

# Language-specific task templates
TASK_TEMPLATES = {
    "en": {
        "system": TASK_GENERATOR_SYSTEM_PROMPT,
        "examples": {
            "exercise": [
                "After I wake up, I will put on my workout clothes",
                "After I finish dinner, I will do 2 push-ups",
                "After I get home, I will walk around the block once"
            ],
            "reading": [
                "After I sit down, I will open my book to page 1",
                "After I finish coffee, I will read one paragraph",
                "After I get in bed, I will read one page"
            ],
            "meditation": [
                "After I wake up, I will sit quietly for 30 seconds",
                "After I finish lunch, I will take 3 deep breaths",
                "After I get home, I will close my eyes for 1 minute"
            ],
            "writing": [
                "After I open my laptop, I will write one sentence",
                "After I finish breakfast, I will write 3 words",
                "After I sit at my desk, I will open a blank document"
            ]
        },
        "celebrations": [
            "Hell yeah! You crushed it!",
            "Damn, that's better than yesterday!",
            "You're building momentum, champ!",
            "Small win, big impact!",
            "You're too badass to stop here!"
        ]
    },
    "ru": {
        "system": """Вы - генератор задач Tiny Habits доктора Б.Дж. Фогга. Ваша миссия - создавать конкретные, выполнимые задачи, которые кажутся почти слишком маленькими, чтобы потерпеть неудачу.

Основные принципы:
1. "После того как я [якорь], я буду [крошечное поведение]"
2. Делайте конкретным и выполнимым
3. Фокус на поведении, а не результате
4. Держите под 30 секунд когда возможно
5. Делайте настолько маленьким, что почти глупо не сделать
6. Празднуйте каждое завершение

Структура задачи:
- Четкое, конкретное действие
- Измеримые критерии завершения
- Соответствует уровню сложности
- Соответствует предпочтениям пользователя
- Включает момент празднования""",
        "examples": {
            "exercise": [
                "После того как я проснусь, я надену спортивную одежду",
                "После того как я поужинаю, я сделаю 2 отжимания",
                "После того как я приду домой, я пройдусь вокруг квартала один раз"
            ],
            "reading": [
                "После того как я сяду, я открою книгу на первой странице",
                "После того как я допью кофе, я прочитаю один абзац",
                "После того как я лягу в постель, я прочитаю одну страницу"
            ]
        },
        "celebrations": [
            "Отлично! Ты справился!",
            "Черт, это лучше чем вчера!",
            "Ты набираешь импульс, чемпион!",
            "Маленькая победа, большой эффект!",
            "Ты слишком крут, чтобы остановиться!"
        ]
    }
}