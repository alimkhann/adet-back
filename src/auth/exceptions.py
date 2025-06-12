"""
Custom exceptions for the auth module.
"""
from fastapi import HTTPException, status


class AuthException(Exception):
    """Base exception for auth-related errors."""
    pass


class UserAlreadyExistsException(AuthException):
    """Raised when trying to create a user that already exists."""
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"User with email '{email}' already exists")


class UserNotFoundException(AuthException):
    """Raised when a user is not found."""
    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"User '{identifier}' not found")


class InvalidCredentialsException(AuthException):
    """Raised when credentials are invalid."""
    def __init__(self):
        super().__init__("Invalid email or password")


class InvalidTokenException(AuthException):
    """Raised when JWT token is invalid or expired."""
    def __init__(self):
        super().__init__("Invalid or expired token")


class TokenExpiredException(AuthException):
    """Raised when JWT token is expired."""
    def __init__(self):
        super().__init__("Token has expired")


class InsufficientPermissionsException(AuthException):
    """Raised when user doesn't have required permissions."""
    def __init__(self, required_permission: str = None):
        if required_permission:
            message = (
                f"Insufficient permissions. Required: {required_permission}"
            )
            super().__init__(message)
        else:
            super().__init__("Insufficient permissions")


class DatabaseException(AuthException):
    """Raised when database operations fail."""
    def __init__(self, operation: str):
        self.operation = operation
        super().__init__(f"Database operation failed: {operation}")


def raise_http_exception(exception: AuthException) -> HTTPException:
    """Convert custom auth exceptions to FastAPI HTTPExceptions."""
    if isinstance(exception, UserAlreadyExistsException):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception)
        )
    elif isinstance(exception, UserNotFoundException):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exception)
        )
    elif isinstance(exception, InvalidCredentialsException):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exception),
            headers={"WWW-Authenticate": "Bearer"}
        )
    elif isinstance(exception, (InvalidTokenException, TokenExpiredException)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exception),
            headers={"WWW-Authenticate": "Bearer"}
        )
    elif isinstance(exception, InsufficientPermissionsException):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exception)
        )
    elif isinstance(exception, DatabaseException):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )