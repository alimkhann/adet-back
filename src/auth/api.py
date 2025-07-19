from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse, FileResponse
import mimetypes
import httpx
import os
import uuid
from urllib.parse import urlparse, urlunparse

from src.auth.dependencies import get_current_user
from src.auth.exceptions import UserNotFoundException
from src.auth.models import User as UserModel
from src.auth.schema import UserSchema, UsernameUpdateSchema, ProfileImageUpdateSchema, ProfileUpdateSchema
from src.auth.service import AuthService
from src.database import get_async_db
from src.config import settings
from src.services.azure_storage import azure_storage
from src.services.file_upload import file_upload_service
from src.posts.crud import PostCRUD

router = APIRouter()


def get_base_blob_url(url):
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


@router.get("/me", response_model=UserSchema, summary="Get Current User Profile")
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
    """
    Retrieves the profile information for the currently authenticated user based on their Clerk JWT.
    """
    # Generate a permanent signed URL for the profile image if it exists
    if current_user.profile_image_url:
        base_url = get_base_blob_url(current_user.profile_image_url)
        signed_url = file_upload_service.generate_permanent_signed_url(base_url, container=file_upload_service.pfp_container_name)
        current_user.profile_image_url = signed_url
    return current_user


@router.post("/me/sync", response_model=UserSchema, summary="Sync Current User Profile")
async def sync_user_profile(current_user: UserModel = Depends(get_current_user)):
    if current_user.profile_image_url:
        base_url = get_base_blob_url(current_user.profile_image_url)
        signed_url = file_upload_service.generate_permanent_signed_url(base_url, container=file_upload_service.pfp_container_name)
        current_user.profile_image_url = signed_url
    return current_user


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


@router.patch("/me/profile", response_model=UserSchema, summary="Update User Profile")
async def update_profile(
    profile_update: ProfileUpdateSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Updates the user's profile information (name, username, bio).
    """
    try:
        updated_user = await AuthService.update_user_profile(
            user_id=current_user.id,
            db=db,
            name=profile_update.name,
            username=profile_update.username,
            bio=profile_update.bio
        )
        return updated_user
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        # Handle username already taken or validation errors
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.post("/me/profile-image", response_model=UserSchema, summary="Upload Profile Image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    # Read file data
    file_data = await file.read()
    # Delete old profile image if it exists
    if current_user.profile_image_url:
        await file_upload_service.delete_proof_file(current_user.profile_image_url, container=file_upload_service.pfp_container_name)
    # Upload to Azure (use pfp container)
    success, file_url, error = await file_upload_service.upload_pfp_file(
        file_data=file_data,
        filename=file.filename or "profile_image.jpg",
        content_type=file.content_type or "image/jpeg",
        user_id=current_user.clerk_id
    )
    if not success:
        raise HTTPException(status_code=400, detail=f"File upload failed: {error}")
    # Update user profile image URL
    updated_user = await AuthService.update_profile_image(
        user_id=current_user.id,
        profile_image_url=file_url,
        db=db
    )
    # Generate a permanent signed URL for the profile image
    if updated_user.profile_image_url:
        signed_url = file_upload_service.generate_permanent_signed_url(updated_user.profile_image_url, container=file_upload_service.pfp_container_name)
        updated_user.profile_image_url = signed_url
    return updated_user


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

@router.get("/me/post-count", response_model=dict)
async def get_my_post_count(
    db: AsyncSession = Depends(get_async_db),
    current_user = Depends(get_current_user)
):
    count = await PostCRUD.get_user_post_count(db, current_user.id)
    return {"post_count": count}