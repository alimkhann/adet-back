import os
from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from .crud import UserDAO
from .models import User
from ..database import get_async_db
from ..config import settings
from dotenv import load_dotenv

load_dotenv()

CLERK_DOMAIN = os.getenv("CLERK_DOMAIN")

# Correctly construct the Clerk JWKS URL and issuer
if not CLERK_DOMAIN:
    raise ValueError("CLERK_DOMAIN environment variable not set")

CLERK_JWKS_URL = f"https://{CLERK_DOMAIN}/.well-known/jwks.json"
CLERK_ISSUER = f"https://{CLERK_DOMAIN}"

bearer_scheme = HTTPBearer()

_jwks_cache = None

async def get_clerk_public_keys():
    """
    Retrieves and caches Clerk's JWKS public keys.
    The JWKS URL is derived from the Clerk domain in your settings.
    """
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache

    jwks_url = CLERK_JWKS_URL

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()["keys"]
            return _jwks_cache
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not connect to Clerk JWKS endpoint: {exc}",
            )
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error fetching Clerk JWKS: {exc.response.text}",
            )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Decodes the Clerk JWT, verifies it, and retrieves or creates the user
    in the local database.
    """
    token = credentials.credentials
    jwks = await get_clerk_public_keys()

    try:
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header"
            )

        payload = jwt.decode(
            token, rsa_key, algorithms=["RS256"], issuer=CLERK_ISSUER
        )

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}"
        )

    clerk_id = payload.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: no sub claim"
        )

    # Extract email and username from Clerk JWT
    # Email might not be in JWT by default, so we'll make it optional for now
    email = payload.get("email")
    username = payload.get("username")

    # If email is not in JWT, we'll use a placeholder and update it later
    if not email:
        email = f"user_{clerk_id[:8]}@placeholder.com"  # Temporary placeholder

    # This DAO method will be implemented in the next step.
    # It finds a user by clerk_id or creates one if they don't exist.
    user = await UserDAO.get_or_create_user_by_clerk_id(
        db=db, clerk_id=clerk_id, email=email, username=username
    )

    if not user:
        # This case should not be reached if the DAO method is correct
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve or create user.",
        )

    return user