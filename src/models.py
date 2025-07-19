from sqlalchemy.sql import func

from src.database import Base

# Import all models to register them with SQLAlchemy Base
from src.auth.models import User
from src.onboarding.models import OnboardingAnswer
from src.habits.models import (
    Habit,
    MotivationEntry,
    AbilityEntry,
    TaskEntry,
    TaskValidation
)
from src.friends.models import Friendship, FriendRequest, CloseFriend, BlockedUser, UserReport
from src.chats.models import Conversation, Message, ConversationParticipant
from src.posts.models import Post, PostComment, PostLike, PostView, PostReport
from src.support.models import SupportRequest, BugReport, SupportResponse

