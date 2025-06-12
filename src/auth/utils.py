from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from .exceptions import InvalidTokenException, TokenExpiredException
from ..config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> str:
    """
    Decode JWT token and return email.
    Raises InvalidTokenException or TokenExpiredException.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise InvalidTokenException()
        return email
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException()
    except JWTError:
        raise InvalidTokenException()


def validate_token(token: str) -> bool:
    """Validate if token is valid without raising exceptions."""
    try:
        decode_access_token(token)
        return True
    except (InvalidTokenException, TokenExpiredException):
        return False