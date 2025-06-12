from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .crud import UserDAO
from .exceptions import (InvalidTokenException, TokenExpiredException,
                             UserNotFoundException, raise_http_exception)
from .models import User
from .utils import decode_access_token
from ..database import get_async_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    try:
        email = decode_access_token(token)
        db_user = await UserDAO.get_user_by_email_or_raise(email, db)
        return User(
            id=db_user.id,
            email=db_user.email,
            username=db_user.username # Assuming username is part of the User model
        )
    except (
        InvalidTokenException,
        TokenExpiredException,
        UserNotFoundException
    ) as e:
        raise_http_exception(e)