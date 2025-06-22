from pydantic import BaseModel

class OnboardingAnswerBase(BaseModel):
    habit_name: str
    habit_description: str | None = None
    frequency: str
    validation_time: str
    difficulty: str
    proof_style: str

class OnboardingAnswerCreate(OnboardingAnswerBase):
    pass

class OnboardingAnswer(OnboardingAnswerBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True