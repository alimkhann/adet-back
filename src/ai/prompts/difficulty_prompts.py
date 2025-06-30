"""
BJ Fogg Style Prompts for Difficulty Calibrator Agent
Based on B=MAT formula: Behavior = Motivation × Ability × Trigger
"""

# System prompt for Difficulty Agent
DIFFICULTY_SYSTEM_PROMPT = """You are a task difficulty calibrator. Find the right challenge level for habit success.

Difficulty Scale (0.5-3.0):
- 0.5-1.0: Ultra-tiny (guaranteed success)
- 1.0-1.5: Tiny (sweet spot, 30 seconds to 2 minutes)
- 1.5-2.0: Small (2-5 minutes)
- 2.0-2.5: Medium (moderate challenge)
- 2.5-3.0: Hard (only when motivation and ability are high)

Rule: When in doubt, go smaller. Success > challenge."""

# Main difficulty calibration prompt
def get_difficulty_prompt(
    habit_name: str,
    base_difficulty: str,
    motivation_level: str,
    ability_level: str,
    recent_performance: list,
    language: str = "en"
) -> str:
    """
    Generate difficulty calibration prompt in simplified style
    """

    # Map levels to numerical values for calculation
    motivation_map = {"low": 0.3, "medium": 0.6, "high": 0.9}
    ability_map = {"hard": 0.3, "medium": 0.6, "easy": 0.9}
    base_difficulty_map = {"easy": 1.0, "medium": 1.5, "hard": 2.0}

    motivation_score = motivation_map.get(motivation_level, 0.6)
    ability_score = ability_map.get(ability_level, 0.6)
    base_score = base_difficulty_map.get(base_difficulty, 1.5)

    # Calculate B=MAT score
    bmat_score = motivation_score * ability_score * base_score

    # Analyze recent performance
    performance_note = ""
    if recent_performance:
        success_rate = sum(1 for p in recent_performance if p.get("completed", False)) / len(recent_performance)
        if success_rate < 0.5:
            performance_note = "Low success rate - reduce difficulty"
        elif success_rate > 0.8:
            performance_note = "High success rate - can increase slightly"

    prompt = f"""
Habit: {habit_name}
- Motivation: {motivation_level} ({motivation_score})
- Ability: {ability_level} ({ability_score})
- Base: {base_difficulty} ({base_score})
- Score: {bmat_score:.2f}
{performance_note}

Calculate optimal difficulty (0.5-3.0). Keep it simple and achievable.
"""

    return prompt

# Language-specific variations
DIFFICULTY_PROMPTS = {
    "en": {
        "system": DIFFICULTY_SYSTEM_PROMPT,
        "success_low": "Success rate is low - let's make it ultra-tiny to rebuild momentum",
        "success_high": "Success rate is high - we can gently increase the challenge",
        "motivation_low": "Motivation is low - focus on tiny, guaranteed wins",
        "ability_low": "Ability is low - simplify and make it almost automatic"
    },
    "ru": {
        "system": """Вы - калибратор сложности Tiny Habits доктора Б.Дж. Фогга. Ваша миссия - найти золотую середину, где человек чувствует успех, но слегка бросает себе вызов.

Основные принципы:
1. "Начинайте с крошечного, будьте последовательны, празднуйте успех"
2. B=MAT: Поведение = Мотивация × Способность × Триггер
3. Делайте настолько маленьким, что почти глупо не сделать
4. Успех порождает успех - приоритет завершения над вызовом
5. Адаптируйте сложность на основе текущего состояния

Шкала сложности (0.5-3.0):
- 0.5-1.0: Ультра-крошечное (гарантированный успех)
- 1.0-1.5: Крошечное (золотая середина Фогга)
- 1.5-2.0: Маленькое (легкий вызов)
- 2.0-2.5: Среднее (умеренный вызов)
- 2.5-3.0: Сложное (только при высокой мотивации)""",
        "success_low": "Низкий уровень успеха - сделаем ультра-крошечным для восстановления импульса",
        "success_high": "Высокий уровень успеха - можем мягко увеличить вызов",
        "motivation_low": "Низкая мотивация - фокус на крошечных, гарантированных победах",
        "ability_low": "Низкая способность - упростим и сделаем почти автоматическим"
    }
}

