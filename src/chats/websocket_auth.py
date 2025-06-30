import logging
from typing import Optional
from fastapi import WebSocket, status
from fastapi.exceptions import WebSocketException

from ..auth.dependencies import get_clerk_public_keys
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError

logger = logging.getLogger(__name__)


async def authenticate_websocket(websocket: WebSocket, token: str) -> Optional[int]:
    """
    Authenticate WebSocket connection using Clerk JWT token.
    Returns user_id if valid, None if invalid.
    """
    try:
        if not token:
            logger.warning("WebSocket authentication failed: No token provided")
            return None

        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        # Verify the Clerk JWT token using the same logic as REST endpoints
        from ..auth.dependencies import CLERK_ISSUER

        jwks = await get_clerk_public_keys()

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
            logger.warning("WebSocket authentication failed: Invalid token header")
            return None

        payload = jwt.decode(
            token, rsa_key, algorithms=["RS256"], issuer=CLERK_ISSUER
        )

        clerk_id = payload.get('sub')
        if not clerk_id:
            logger.warning("WebSocket authentication failed: No sub claim in token")
            return None

        # Get user_id from database using clerk_id
        from ..auth.crud import UserDAO
        from ..database import async_session_maker

        async with async_session_maker() as db:
            user = await UserDAO.get_user_by_clerk_id(db, clerk_id)
            if not user:
                logger.warning(f"WebSocket authentication failed: No user found for clerk_id {clerk_id}")
                return None

            logger.info(f"WebSocket authenticated successfully for user {user.id}")
            return user.id

    except ExpiredSignatureError:
        logger.warning("WebSocket authentication failed: Token has expired")
        return None
    except JWTError as e:
        logger.warning(f"WebSocket authentication failed: Invalid token - {e}")
        return None
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None


async def websocket_auth_required(websocket: WebSocket, token: str) -> int:
    """
    Authenticate WebSocket connection or raise WebSocketException.
    Returns user_id if valid, raises exception if invalid.
    """
    user_id = await authenticate_websocket(websocket, token)

    if not user_id:
        logger.warning("WebSocket connection rejected: Authentication failed")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Authentication failed"
        )

    return user_id


def extract_token_from_query(websocket: WebSocket) -> Optional[str]:
    """
    Extract authentication token from WebSocket query parameters.
    Supports both 'token' and 'authorization' query parameters.
    """
    query_params = websocket.query_params

    # Try 'token' parameter first
    token = query_params.get('token')
    if token:
        return token

    # Try 'authorization' parameter
    auth_header = query_params.get('authorization')
    if auth_header:
        return auth_header

    # Try 'Authorization' parameter (case-sensitive)
    auth_header = query_params.get('Authorization')
    if auth_header:
        return auth_header

    return None