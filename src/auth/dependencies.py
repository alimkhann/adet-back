import os
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import jwt
from .crud import UserDAO
from .models import User
from ..database import get_async_db
from ..config import settings
from dotenv import load_dotenv

load_dotenv()

CLERK_DOMAIN = os.getenv("CLERK_DOMAIN")

CLERK_JWKS_URL = f"https://clerk.{CLERK_DOMAIN}.com/.well-known/jwks.json"

bearer_scheme = HTTPBearer()

_jwks_cache = None

async def get_clerk_public_keys():
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(CLERK_JWKS_URL)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        return _jwks_cache

def get_email_from_clerk_claims(payload):
    # Clerk JWTs have 'email' or 'sub' (user id). Prefer email for user lookup.
    return payload.get('email') or payload.get('sub')

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    token = credentials.credentials
    jwks = await get_clerk_public_keys()
    try:
        payload = jwt.decode(token, jwks, algorithms=["RS256"], options={"verify_aud": False})
    except Exception:
        from .exceptions import InvalidTokenException, raise_http_exception
        raise_http_exception(InvalidTokenException())
    email = get_email_from_clerk_claims(payload)
    if not email:
        from .exceptions import InvalidTokenException, raise_http_exception
        raise_http_exception(InvalidTokenException())
    # Auto-provision user if not exists
    user = await UserDAO.get_user_by_email(email, db)
    if not user:
        from .models import User as UserModel
        user = UserModel(email=email, username=email.split('@')[0])
        user = await UserDAO.create_user(user, db)
    return user