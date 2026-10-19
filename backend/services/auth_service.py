"""
Authentication service — user creation, login, and seeding.

Keeps credential handling in one place so the API layer stays thin.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.user import User
from backend.schemas.user import Role, UserCreate
from backend.security import hash_password, verify_password

logger = logging.getLogger(__name__)

# The literal development defaults, used only to detect that the
# environment has not overridden them.
_DEV_DEFAULT_USERNAME = "admin"
_DEV_DEFAULT_PASSWORD = "admin12345"


def _admin_username() -> str:
    """Bootstrap admin username (ADMIN_USERNAME env var)."""
    return settings.ADMIN_USERNAME


def _admin_password() -> str:
    """Bootstrap admin password (ADMIN_PASSWORD env var)."""
    return settings.ADMIN_PASSWORD


def _admin_email() -> str:
    """Bootstrap admin email (ADMIN_EMAIL env var)."""
    return settings.ADMIN_EMAIL


def _using_default_credentials() -> bool:
    """True when the bootstrap admin still uses the shipped dev defaults."""
    return (
        settings.ADMIN_USERNAME == _DEV_DEFAULT_USERNAME
        and settings.ADMIN_PASSWORD == _DEV_DEFAULT_PASSWORD
    )


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Fetch a user by username (case-insensitive)."""
    if not username:
        return None
    return (
        db.query(User)
        .filter(User.username.ilike(username.strip()))
        .first()
    )


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Fetch a user by primary key."""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, payload: UserCreate) -> User:
    """
    Create a new user with a bcrypt-hashed password.

    Raises
    ------
    ValueError if the username or email is already taken
    """
    username = payload.username.strip()

    if get_user_by_username(db, username):
        raise ValueError(f"Username '{username}' is already registered.")

    if payload.email:
        existing_email = db.query(User).filter(User.email == payload.email).first()
        if existing_email:
            raise ValueError(f"Email '{payload.email}' is already registered.")

    user = User(
        username=username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role.value if isinstance(payload.role, Role) else str(payload.role),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Created user '%s' with role %s", user.username, user.role)
    return user


def authenticate(db: Session, username: str, password: str) -> Tuple[Optional[User], str]:
    """
    Verify credentials.

    Returns (user, error_message). Exactly one of the two is set.
    Uses the same generic message for unknown users and bad passwords
    so the endpoint doesn't leak which usernames exist.
    """
    user = get_user_by_username(db, username)

    if user is None:
        # Constant-ish work even when the user does not exist
        hash_password(password)
        return None, "Incorrect username or password."

    if not user.is_active:
        return None, "This account is deactivated."

    if not verify_password(password, user.password_hash):
        return None, "Incorrect username or password."

    return user, ""


def record_login(db: Session, user: User) -> None:
    """Stamp the user's last login timestamp."""
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)


def count_users(db: Session) -> int:
    """Number of registered users — used to decide whether to seed."""
    return db.query(User).count()


def ensure_default_admin(db: Session, force: bool = False) -> Optional[User]:
    """
    Create the bootstrap admin account if no users exist (or if force=True).

    Idempotent: a second call is a no-op unless `force` is set, in which
    case the default admin password is reset.

    The credentials come from ADMIN_USERNAME / ADMIN_PASSWORD. The
    built-in defaults are fine for local development but must be
    overridden in a deployed environment, so we warn loudly if they are
    still in use outside development.
    """
    if _using_default_credentials():
        logger.warning(
            "SECURITY WARNING: bootstrap admin '%s' is using the built-in default "
            "password. Set ADMIN_USERNAME and ADMIN_PASSWORD in your environment.",
            _admin_username(),
        )

    username = _admin_username()
    password = _admin_password()

    existing = get_user_by_username(db, username)

    if existing and not force:
        return existing

    if existing and force:
        existing.password_hash = hash_password(password)
        existing.role = Role.ADMIN.value
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        logger.info("Reset default admin credentials")
        return existing

    if count_users(db) > 0 and not force:
        return None

    admin = User(
        username=username,
        email=_admin_email(),
        password_hash=hash_password(password),
        role=Role.ADMIN.value,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    logger.info("Seeded default admin user '%s'", admin.username)
    return admin