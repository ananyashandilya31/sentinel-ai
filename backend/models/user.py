"""
SQLAlchemy ORM model for SOC console users (Phase 8 — authentication).

A security tool must be secure itself, so this table exists to support
JWT authentication and role-based access control (admin / analyst).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship

from backend.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    """
    A console user.

    Roles
    -----
    ADMIN   full access, including creating other users
    ANALYST triage access: read incidents, update status, assign, investigate
    """

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(120), nullable=True, unique=True)
    # bcrypt hash — never the plaintext password
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="ANALYST", index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Optional link to incidents this analyst owns (assigned_to stores username)
    def __repr__(self) -> str:
        return f"<User username={self.username} role={self.role} active={self.is_active}>"