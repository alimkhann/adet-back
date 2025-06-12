from fastapi import HTTPException, status

class OnboardingException(Exception):
    """Base exception for onboarding-related errors."""
    pass

class OnboardingProgressNotFound(OnboardingException):
    """Raised when onboarding progress for a user is not found."""
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"Onboarding progress for user ID {user_id} not found.")

def raise_onboarding_http_exception(exception: OnboardingException) -> HTTPException:
    """Converts custom onboarding exceptions to FastAPI HTTPExceptions."""
    if isinstance(exception, OnboardingProgressNotFound):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exception)
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during onboarding."
        )