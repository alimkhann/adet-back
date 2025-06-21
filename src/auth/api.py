from fastapi import APIRouter, Body, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from .dependencies import get_current_user
from .exceptions import UserNotFoundException, UserAlreadyExistsException
from .schema import User, UsernameUpdate
from .service import AuthService
from ..database import get_async_db

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get(
    "/me",
    response_model=User,
    summary="Get Current User Profile",
    description="Retrieves the profile information for the currently authenticated user based on their Clerk JWT."
)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put(
    "/me",
    response_model=User,
    summary="Update Current User Profile (Username Only)",
    description="Updates the username for the currently authenticated user."
)
async def update_users_me(
    user_update: UsernameUpdate = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        return await AuthService.update_username(
            user_id=current_user.id,
            username=user_update.username,
            db=db
        )
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserAlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Current User Account",
    description="Deletes the account of the currently authenticated user."
)
async def delete_current_user_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        await AuthService.delete_user_account(current_user.id, db)
        return
    except UserNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))