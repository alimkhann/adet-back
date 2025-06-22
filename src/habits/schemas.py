from pydantic import BaseModel

class HabitBase(BaseModel):
    name: str

class HabitCreate(HabitBase):
    pass

class Habit(HabitBase):
    id: int
    user_id: int
    streak: int

    class Config:
        from_attributes = True