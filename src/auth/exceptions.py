"""
Custom exceptions for the auth module.
"""

class AuthException(Exception):
    """Base exception for auth-related errors."""
    pass


class UserAlreadyExistsException(AuthException):
    """Raised when trying to create a user that already exists."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class UserNotFoundException(AuthException):
    """Raised when a user is not found."""
    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"User '{identifier}' not found")


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