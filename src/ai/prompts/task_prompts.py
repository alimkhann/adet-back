"""
BJ Fogg Style Prompts for Task Generator Agent
Creating specific, actionable tasks in Tiny Habits format
"""

# System prompt for Task Generator
TASK_GENERATOR_SYSTEM_PROMPT = """You are a practical habit task generator. Your mission is to create simple, actionable tasks that are easy to understand and complete.

Core Principles:
1. Make tasks direct and specific
2. Keep instructions concise and clear
3. Focus on the action, not complex methodology
4. Make tasks appropriately challenging based on difficulty level
5. Provide clear success criteria

Task Structure:
- Simple, direct action
- Clear completion criteria
- Appropriate for the difficulty level
- Matches the user's proof style preference
- Brief but encouraging completion message

Remember: Keep it simple, actionable, and achievable. No need for complex anchoring - just clear tasks."""

def get_task_generation_prompt(
    habit_name: str,
    habit_description: str,
    difficulty_level: float,
    proof_style: str,
    language: str = "en"
) -> str:
    """
    Generate simple, direct task creation prompt
    """

    # Difficulty-based guidance
    if difficulty_level <= 1.0:
        difficulty_guidance = "VERY EASY: Simple action taking 1-2 minutes max."
    elif difficulty_level <= 1.5:
        difficulty_guidance = "EASY: Straightforward task taking 2-5 minutes."
    elif difficulty_level <= 2.0:
        difficulty_guidance = "MEDIUM: Manageable task taking 5-10 minutes."
    elif difficulty_level <= 2.5:
        difficulty_guidance = "CHALLENGING: More involved task taking 10-15 minutes."
    else:
        difficulty_guidance = "HARD: Significant task requiring 15+ minutes of focused effort."

    # Proof style guidance
    proof_guidance = {
        "photo": "User will take a photo as proof. Task should be visually verifiable.",
        "video": "User will record a video. Task should be observable in a short clip.",
        "audio": "User will record audio. Task should be audible or describable.",
        "text": "User will write text description. Task should be clearly describable."
    }.get(proof_style, "User will provide text description.")

    prompt = f"""
Create a simple, direct task for this habit:

Habit: {habit_name}
Description: {habit_description}

Requirements:
- Difficulty Level: {difficulty_level} ({difficulty_guidance})
- Proof Style: {proof_style} ({proof_guidance})

Generate a task with these components:

1. Task Description: Clear, direct action (e.g., "Do 10 push-ups" or "Read for 5 minutes")
2. Difficulty Level: {difficulty_level} (keep this exact value)
3. Estimated Duration: Realistic time in minutes
4. Success Criteria: How to know it's complete
5. Celebration Message: Brief encouraging message (friendly, motivational tone)
6. Easier Alternative: Simpler version if this feels too hard
7. Harder Alternative: More challenging version if this feels too easy
8. Proof Requirements: Specific instructions on how to prove completion based on {proof_style} proof style

For Proof Requirements, be very specific:
- Photo: "Take a photo showing [specific visual evidence]"
- Video: "Record a video demonstrating [specific action/result]"
- Audio: "Record audio of [specific sound/narration]"
- Text: "Write a description including [specific details to mention]"

Examples of good proof requirements:
- Photo: "Take a photo of your workout setup with you in exercise position"
- Video: "Record a 30-second video showing you performing the exercise"
- Audio: "Record yourself reading aloud for 1 minute"
- Text: "Write 3-5 sentences describing what you learned or accomplished"

Keep the task description simple and direct. No complex "After I..." anchoring needed - just tell them what to do clearly and how to prove they did it.

Example formats:
- "Practice leetcode for 10 minutes"
- "Do 5 push-ups"
- "Read one chapter"
- "Write 100 words"
"""

    return prompt

# Language-specific task templates
TASK_TEMPLATES = {
    "en": {
        "system": TASK_GENERATOR_SYSTEM_PROMPT,
        "examples": {
            "exercise": [
                "Put on your workout clothes",
                "Do 2 push-ups",
                "Walk around the block once"
            ],
            "reading": [
                "Open your book and read one page",
                "Read one paragraph",
                "Read for 5 minutes"
            ],
            "meditation": [
                "Sit quietly for 30 seconds",
                "Take 3 deep breaths",
                "Close your eyes for 1 minute"
            ],
            "writing": [
                "Write one sentence",
                "Write 3 words",
                "Open a blank document and write one paragraph"
            ]
        },
        "celebrations": [
            "Great job! You did it!",
            "Nice work - that's progress!",
            "You're building momentum!",
            "Small win, big impact!",
            "Well done - keep it up!"
        ]
    },
    "ru": {
        "system": """Вы - генератор практических задач для привычек. Ваша миссия - создавать простые, выполнимые задачи, которые легко понять и выполнить.

Основные принципы:
1. Делайте задачи прямыми и конкретными
2. Держите инструкции краткими и ясными
3. Фокус на действии, а не сложной методологии
4. Делайте задачи соответствующими уровню сложности
5. Предоставляйте четкие критерии успеха

Структура задачи:
- Простое, прямое действие
- Четкие критерии завершения
- Соответствует уровню сложности
- Соответствует предпочтениям пользователя
- Краткое но воодушевляющее сообщение о завершении""",
        "examples": {
            "exercise": [
                "Надеть спортивную одежду",
                "Сделать 2 отжимания",
                "Пройтись вокруг квартала один раз"
            ],
            "reading": [
                "Открыть книгу и прочитать одну страницу",
                "Прочитать один абзац",
                "Читать 5 минут"
            ]
        },
        "celebrations": [
            "Отлично! Ты справился!",
            "Хорошая работа - это прогресс!",
            "Ты набираешь импульс!",
            "Маленькая победа, большой эффект!",
            "Молодец - продолжай!"
        ]
    }
}