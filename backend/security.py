"""
Security primitives for SentinelAI (Phase 8).

Password hashing uses **bcrypt** directly (no passlib indirection) and
JWTs are signed with HS256 via python-jose.

Design notes
------------
* bcrypt truncates at 72 bytes, so long passwords are rejected rather
  than silently truncated (avoids a "two passwords authenticate the
  same" class of bug).
* Tokens carry only `sub` (username) and `role` — no secrets or
  excessive personal data.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from backend.config import settings

logger = logging.getLogger(__name__)

# bcrypt's hard input limit
_BCRYPT_MAX_BYTES = 72

# bcrypt work factor — 12 is a sensible 2020s default (~250ms per hash)
BCRYPT_ROUNDS = 12


class PasswordTooLongError(ValueError):
    """Raised when a password exceeds bcrypt's 72-byte input limit."""


def hash_password(password: str) -> str:
    """
    Hash a plaintext password with bcrypt.

    Raises
    ------
    PasswordTooLongError
        If the password exceeds bcrypt's 72-byte limit. Truncation would
        make two distinct passwords equivalent, so we refuse instead.
    """
    raw = password.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_BYTES:
        raise PasswordTooLongError(
            f"Password must not exceed {_BCRYPT_MAX_BYTES} bytes when UTF-8 encoded."
        )
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Constant-time verification of a plaintext password against a bcrypt hash."""
    if not password_hash:
        return False
    raw = plain_password.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(raw, password_hash.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        logger.debug("Password verification error: %s", exc)
        return False


def create_access_token(
    subject: str,
    role: str,
    expires_minutes: Optional[int] = None,
) -> str:
    """
    Create a signed JWT for the given user.

    Parameters
    ----------
    subject : username stored in the `sub` claim
    role    : role stored in the `role` claim
    expires_minutes : override for settings.JWT_EXPIRE_MINUTES
    """
    minutes = expires_minutes if expires_minutes is not None else settings.JWT_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and verify a JWT.

    Returns the claims dict on success, or None if the token is
    invalid, expired or signed with the wrong key.
    """
    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        logger.debug("JWT decode failed: %s", exc)
        return None


def token_lifetime_seconds() -> int:
    """Token lifetime in seconds, for the login response."""
    return settings.JWT_EXPIRE_MINUTES * 60