from sqlalchemy.sql import func

from .database import Base

# Import all models to register them with SQLAlchemy Base
from .auth.models import User
from .onboarding.models import OnboardingAnswer
from .habits.models import (
    Habit,
    MotivationEntry,
    AbilityEntry,
    TaskEntry,
    TaskValidation
)

# All models are now imported and registered with Base.metadata

# User model moved to auth/models.py
# class User(Base):
#     __tablename__ = "users"

#     id = Column(Integer, primary_key=True, index=True)
#     email = Column(String, unique=True, index=True, nullable=False)
#     username = Column(String, nullable=False)
#     hashed_password = Column(String)
#     is_active = Column(Boolean, default=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
