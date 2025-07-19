from pydantic import BaseModel, Field

class OnboardingAnswerBase(BaseModel):
    habit_name: str
    habit_description: str
    frequency: str
    validation_time: str
    difficulty: str
    proof_style: str = Field(..., alias="proofStyle")

    class Config:
        allow_population_by_field_name = True

class OnboardingAnswerCreate(OnboardingAnswerBase):
    pass

class OnboardingAnswer(OnboardingAnswerBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True