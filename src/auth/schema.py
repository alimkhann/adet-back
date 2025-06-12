from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class UserCredentials(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None