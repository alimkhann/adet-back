from fastapi import APIRouter, Body, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from .dependencies import get_current_user
from .exceptions import (InvalidCredentialsException,
                             UserAlreadyExistsException, raise_http_exception,
                             InvalidTokenException, UserNotFoundException)
from .schema import Token, User, UserCredentials, UserUpdate, PasswordUpdate, UsernameUpdate
from .service import AuthService
from ..database import get_async_db


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/token",
    response_model=Token,
    summary="User Login",
    description="Authenticates a user by email and password, returning an access token upon successful login."
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        return await AuthService.authenticate_user(
            email=form_data.username,
            password=form_data.password,
            db=db
        )
    except InvalidCredentialsException as e:
        raise_http_exception(e)


@router.post(
    "/register",
    response_model=Token,
    summary="User Registration",
    description="Registers a new user with an email, username, and password, then returns an access token."
)
async def register_user(
    credentials: UserCredentials = Body(...),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        token_response = await AuthService.register_user(credentials, db)
        return token_response
    except UserAlreadyExistsException as e:
        raise_http_exception(e)


@router.get(
    "/me",
    response_model=User,
    summary="Get Current User Profile",
    description="Retrieves the profile information for the currently authenticated user based on their access token."
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
        updated_user = await AuthService.update_username(
            user_id=current_user.id,
            username=user_update.username,
            db=db
        )
        return updated_user
    except (UserNotFoundException, InvalidTokenException, UserAlreadyExistsException) as e:
        raise_http_exception(e)


@router.put(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update Current User Password",
    description="Allows the currently authenticated user to change their password."
)
async def update_current_user_password(
    password_update: PasswordUpdate = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    try:
        await AuthService.update_user_password(
            user_id=current_user.id,
            current_password=password_update.current_password,
            new_password=password_update.new_password,
            db=db
        )
        return {"message": "Password updated successfully"}
    except (UserNotFoundException, InvalidTokenException, InvalidCredentialsException) as e:
        raise_http_exception(e)


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
        return {"message": "User account deleted successfully"}
    except (UserNotFoundException, InvalidTokenException) as e:
        raise_http_exception(e)