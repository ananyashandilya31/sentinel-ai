"""
Pydantic schemas for authentication endpoints (Phase 8).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class Role(str, Enum):
    """Access roles used for role-based access control."""

    ADMIN = "ADMIN"
    ANALYST = "ANALYST"


class UserCreate(BaseModel):
    """Payload for registering a new user (admin-only endpoint)."""

    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=8, max_length=128)
    role: Role = Role.ANALYST

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").replace(".", "").isalnum():
            raise ValueError(
                "username may only contain letters, digits, dot, dash and underscore"
            )
        return v


class UserLogin(BaseModel):
    """Payload for POST /auth/login."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Safe user representation — never includes the password hash."""

    id: str
    username: str
    email: Optional[str] = None
    role: Role
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT response returned on successful login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifetime in seconds")
    user: UserResponse


class TokenPayload(BaseModel):
    """Decoded JWT claims."""

    sub: str
    role: str
    exp: int