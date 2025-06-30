from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse, FileResponse
import mimetypes
import httpx
import os
import uuid

from src.auth.dependencies import get_current_user
from src.auth.exceptions import UserNotFoundException
from src.auth.models import User as UserModel
from src.auth.schema import UserSchema, UsernameUpdateSchema, ProfileImageUpdateSchema, ProfileUpdateSchema
from src.auth.service import AuthService
from src.database import get_async_db
from src.config import settings
from src.services.azure_storage import azure_storage

router = APIRouter()


@router.get("/me", response_model=UserSchema, summary="Get Current User Profile")
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
    """
    Retrieves the profile information for the currently authenticated user based on their Clerk JWT.
    """
    return current_user


@router.post("/me/sync", response_model=UserSchema, summary="Sync User Data from Clerk")
async def sync_user_from_clerk(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Syncs user data from Clerk to update email and other profile information.
    """
    try:
        # Get the user's Clerk ID
        clerk_id = current_user.clerk_id

        # Fetch user data from Clerk API
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                "Authorization": f"Bearer {settings.clerk_secret_key}",
                "Content-Type": "application/json"
            }

            response = await client.get(
                f"https://api.clerk.com/v1/users/{clerk_id}",
                headers=headers
            )

            if response.status_code == 200:
                clerk_user_data = response.json()

                # Extract email and username from Clerk data
                email = None
                username = None

                # Get primary email
                if "email_addresses" in clerk_user_data:
                    for email_data in clerk_user_data["email_addresses"]:
                        if email_data.get("id") == clerk_user_data.get("primary_email_address_id"):
                            email = email_data.get("email_address")
                            break

                # Get username
                username = clerk_user_data.get("username")

                # Update user in database
                updated = False
                if email and email != current_user.email:
                    current_user.email = email
                    updated = True
                if username and username != current_user.username:
                    current_user.username = username
                    updated = True

                if updated:
                    await db.commit()
                    await db.refresh(current_user)

                return current_user
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch user data from Clerk"
                )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout while syncing user data from Clerk"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing user data: {str(e)}"
        )


@router.patch("/me/username", status_code=status.HTTP_204_NO_CONTENT, summary="Update Username")
async def update_username(
    username_update: UsernameUpdateSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Updates the username for the currently authenticated user.
    """
    try:
        await AuthService.update_username(
            user_id=current_user.id, username=username_update.username, db=db
        )
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update username: {str(e)}"
        )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Delete User Account")
async def delete_account(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Deletes the currently authenticated user's account.
    This will remove all user data from the database.
    The user should also delete their account from Clerk separately.
    """
    try:
        # Delete user from database
        await AuthService.delete_user_account(
            user_id=current_user.id, db=db
        )

        # Note: User should delete their Clerk account separately
        # We could potentially call Clerk API here to delete the user,
        # but that would require additional permissions and error handling

    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )