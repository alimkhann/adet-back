from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import os
import uuid

from src.auth.dependencies import get_current_user
from src.auth.exceptions import UserNotFoundException
from src.auth.models import User as UserModel
from src.auth.schema import UserSchema, UsernameUpdateSchema, ProfileImageUpdateSchema
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


@router.post("/me/profile-image", response_model=UserSchema, summary="Upload Profile Image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Uploads a profile image for the currently authenticated user.
    Accepts image files (jpg, jpeg, png, webp) up to 5MB.
    Uses Azure Blob Storage if configured, falls back to local storage.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed."
        )

    # Validate file size (5MB limit)
    max_size = 5 * 1024 * 1024  # 5MB in bytes
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size too large. Maximum size is 5MB."
        )

    try:
        profile_image_url = None

        # Try Azure Storage first
        if azure_storage.is_available():
            profile_image_url = await azure_storage.upload_file(
                file_data=file_content,
                file_name=file.filename or "profile.jpg",
                content_type=file.content_type
            )

        # Fallback to local storage if Azure fails or isn't configured
        if not profile_image_url:
            # Create uploads directory if it doesn't exist
            upload_dir = "uploads/profile_images"
            os.makedirs(upload_dir, exist_ok=True)

            # Generate unique filename
            file_extension = file.filename.split('.')[-1] if file.filename and '.' in file.filename else 'jpg'
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = os.path.join(upload_dir, unique_filename)

            # Save file locally
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)

            # Create URL for local storage
            profile_image_url = f"http://localhost:8000/uploads/profile_images/{unique_filename}"

        if not profile_image_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload profile image to any storage provider"
            )

        # Delete old profile image if it exists
        if current_user.profile_image_url:
            await _delete_old_profile_image(current_user.profile_image_url)

        # Update user profile image
        updated_user = await AuthService.update_profile_image(
            user_id=current_user.id,
            profile_image_url=profile_image_url,
            db=db
        )

        return updated_user

    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload profile image: {str(e)}"
        )

async def _delete_old_profile_image(image_url: str):
    """Helper function to delete old profile images"""
    try:
        # Try Azure Storage first
        if azure_storage.is_available() and "blob.core.windows.net" in image_url:
            await azure_storage.delete_file(image_url)
        # Handle local storage cleanup
        elif image_url.startswith("http://localhost:8000/uploads/"):
            file_path = image_url.replace("http://localhost:8000/", "")
            if os.path.exists(file_path):
                os.remove(file_path)
    except Exception as e:
        # Log but don't fail the upload if old image deletion fails
        print(f"Failed to delete old profile image: {e}")


@router.patch("/me/profile-image", response_model=UserSchema, summary="Update Profile Image URL")
async def update_profile_image_url(
    profile_image_update: ProfileImageUpdateSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Updates the profile image URL for the currently authenticated user.
    This can be used to set an external image URL (e.g., from Clerk or other providers).
    """
    try:
        updated_user = await AuthService.update_profile_image(
            user_id=current_user.id,
            profile_image_url=profile_image_update.profile_image_url,
            db=db
        )
        return updated_user
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile image: {str(e)}"
        )


@router.delete("/me/profile-image", response_model=UserSchema, summary="Delete Profile Image")
async def delete_profile_image(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Deletes the profile image for the currently authenticated user.
    Handles both Azure Blob Storage and local storage.
    """
    try:
        # Delete the actual file if user has a profile image
        if current_user.profile_image_url:
            await _delete_old_profile_image(current_user.profile_image_url)

        updated_user = await AuthService.delete_profile_image(
            user_id=current_user.id,
            db=db
        )
        return updated_user
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete profile image: {str(e)}"
        )

@router.get("/me/profile-image/raw", summary="Get Raw Profile Image (Proxy)")
async def get_profile_image_raw(current_user: UserModel = Depends(get_current_user)):
    """
    Streams the user's profile image securely from Azure Blob Storage or local storage.
    Only accessible to the authenticated user.
    """
    from fastapi.responses import StreamingResponse, FileResponse
    import aiofiles
    import mimetypes
    import httpx

    image_url = current_user.profile_image_url
    if not image_url:
        raise HTTPException(status_code=404, detail="No profile image set.")

    # Azure Blob Storage
    if azure_storage.is_available() and "blob.core.windows.net" in image_url:
        try:
            # Download the blob as a stream using Azure SDK
            from azure.storage.blob import BlobClient
            blob_name = image_url.split("/")[-1]
            blob_client = azure_storage.blob_service_client.get_blob_client(
                container=azure_storage.container_name,
                blob=blob_name
            )
            stream = blob_client.download_blob()
            content_type = stream.properties.get("content_settings").content_type or "application/octet-stream"
            return StreamingResponse(stream.chunks(), media_type=content_type)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch image from Azure: {e}")

    # Local storage fallback
    if image_url.startswith("http://localhost:8000/uploads/"):
        file_path = image_url.replace("http://localhost:8000/", "")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Profile image not found on server.")
        mime_type, _ = mimetypes.guess_type(file_path)
        return FileResponse(file_path, media_type=mime_type or "application/octet-stream")

    # External URL fallback (should not happen, but handle gracefully)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(image_url)
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "application/octet-stream")
                return StreamingResponse(iter([resp.content]), media_type=content_type)
            else:
                raise HTTPException(status_code=404, detail="Profile image not found at external URL.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch image from external URL: {e}")