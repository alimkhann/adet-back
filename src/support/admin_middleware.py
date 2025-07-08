from fastapi import HTTPException, Depends
from typing import List
import os

from ..auth.dependencies import get_current_user
from ..models import User


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure user is an admin"""
    # For now, we'll use a simple environment variable approach
    # In production, you might want to store admin status in the database
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")

    if current_user.email in admin_emails:
        return current_user

    raise HTTPException(
        status_code=403,
        detail="Admin access required"
    )


def is_admin_user(current_user: User = Depends(get_current_user)) -> bool:
    """Check if current user is an admin"""
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    return current_user.email in admin_emails
from typing import List
import os

from ..auth.dependencies import get_current_user
from ..models import User


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure user is an admin"""
    # For now, we'll use a simple environment variable approach
    # In production, you might want to store admin status in the database
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")

    if current_user.email in admin_emails:
        return current_user

    raise HTTPException(
        status_code=403,
        detail="Admin access required"
    )


def is_admin_user(current_user: User = Depends(get_current_user)) -> bool:
    """Check if current user is an admin"""
    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    return current_user.email in admin_emails

