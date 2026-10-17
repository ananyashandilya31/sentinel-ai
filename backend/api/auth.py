"""
Authentication API router — /api/v1/auth/*

Endpoints:
    POST /auth/login     Exchange credentials for a JWT
    POST /auth/register  Create a user (admin only)
    GET  /auth/me        Current user profile
    POST /auth/seed      Ensure the bootstrap admin exists (idempotent)
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.dependencies import get_current_admin, get_current_user
from backend.models.user import User
from backend.schemas.user import Token, UserCreate, UserLogin, UserResponse
from backend.security import create_access_token, token_lifetime_seconds
from backend.services import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── In-memory login throttling ────────────────────────────────────
# A security tool should protect its own front door. This is a simple
# sliding window per client IP: after LOGIN_MAX_ATTEMPTS failures
# within LOGIN_ATTEMPT_WINDOW_SECONDS, further logins are refused.

_attempts: Dict[str, Deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    window = settings.LOGIN_ATTEMPT_WINDOW_SECONDS

    attempts = _attempts[ip]
    while attempts and now - attempts[0] > window:
        attempts.popleft()

    return len(attempts) >= settings.LOGIN_MAX_ATTEMPTS


def _record_failure(ip: str) -> None:
    _attempts[ip].append(time.monotonic())


def _clear_failures(ip: str) -> None:
    _attempts.pop(ip, None)


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/login", response_model=Token, summary="Log in and receive a JWT")
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> Token:
    """
    Validate credentials and return a signed JWT.

    - 401 on bad credentials (same message for unknown user and bad
      password, so usernames can't be enumerated)
    - 429 after too many failed attempts from the same client
    """
    ip = _client_ip(request)

    if _is_rate_limited(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Too many failed login attempts. "
                f"Try again in {settings.LOGIN_ATTEMPT_WINDOW_SECONDS} seconds."
            ),
        )

    user, error = auth_service.authenticate(db, payload.username, payload.password)

    if user is None:
        _record_failure(ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error or "Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _clear_failures(ip)
    auth_service.record_login(db, user)

    token = create_access_token(subject=user.username, role=user.role)
    logger.info("User '%s' logged in", user.username)

    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=token_lifetime_seconds(),
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user (admin only)",
)
def register(
    payload: UserCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Provision a new analyst or admin account. Requires an admin token."""
    try:
        user = auth_service.create_user(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse, summary="Current user profile")
def read_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the profile of the authenticated caller."""
    return UserResponse.model_validate(current_user)


@router.post("/seed", response_model=UserResponse, summary="Ensure the bootstrap admin exists")
def seed_admin(
    reset: bool = False,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Idempotently create the default admin account (admin / admin12345).

    Only performs work when no users exist, or when `reset=true`
    explicitly restores the default admin credentials.
    """
    user = auth_service.ensure_default_admin(db, force=reset)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Users already exist. Pass reset=true to restore default admin.",
        )
    return UserResponse.model_validate(user)