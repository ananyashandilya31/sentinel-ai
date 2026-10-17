"""
FastAPI authentication dependencies (Phase 8).

Provides:
    get_current_user       — resolves the caller from the Bearer token
    get_current_admin      — additionally requires the ADMIN role
    require_auth_if_enabled — gates enforcement behind settings.AUTH_ENABLED

`AUTH_ENABLED` exists so the SOC console still boots in demo mode with
no credentials configured, while production deployments get full
enforcement by flipping one environment variable.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.user import User
from backend.schemas.user import Role
from backend.security import decode_access_token

logger = logging.getLogger(__name__)

# auto_error=False so we can return our own 401 JSON shape
bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated. Provide a valid Bearer token.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _extract_username(credentials: Optional[HTTPAuthorizationCredentials]) -> str:
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise CREDENTIALS_ERROR

    subject = payload.get("sub")
    if not subject:
        raise CREDENTIALS_ERROR

    return subject


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the authenticated user from the Authorization header.

    Raises 401 when the token is missing, expired or invalid.
    """
    username = _extract_username(credentials)
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise CREDENTIALS_ERROR
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is deactivated.",
        )

    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the ADMIN role (e.g. creating other users)."""
    if current_user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required.",
        )
    return current_user


def require_auth_if_enabled(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Role gate used on protected write routes.

    When AUTH_ENABLED is true (production default) a valid token is
    required. When false, the route stays open so the SOC demo can run
    without credentials — the returned user is None in that case.

    Note: this deliberately does NOT depend on `get_current_user`.
    That dependency raises 401 when no token is present, which would
    defeat the AUTH_ENABLED=False escape hatch before this function
    ever runs.
    """
    if not settings.AUTH_ENABLED:
        return None

    username = _extract_username(credentials)
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise CREDENTIALS_ERROR
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is deactivated.",
        )

    return user