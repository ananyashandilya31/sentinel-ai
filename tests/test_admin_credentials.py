"""
Tests for the environment-driven bootstrap admin (Phase 8).

ADMIN_USERNAME / ADMIN_PASSWORD must control the seeded account, so a
deployment never has to ship the hardcoded development password.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import settings
from backend.services import auth_service
from backend.security import verify_password


@pytest.fixture
def custom_admin(monkeypatch):
    """Point the bootstrap credentials at non-default values."""
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "soc_operator")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "Str0ng-Passw0rd!")
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "soc@example.org")
    yield


def test_admin_uses_environment_username(custom_admin, db_session):
    user = auth_service.ensure_default_admin(db_session)
    assert user is not None
    assert user.username == "soc_operator"
    assert user.email == "soc@example.org"
    assert user.role == "ADMIN"


def test_admin_uses_environment_password(custom_admin, db_session):
    user = auth_service.ensure_default_admin(db_session)
    assert verify_password("Str0ng-Passw0rd!", user.password_hash) is True
    assert verify_password("admin12345", user.password_hash) is False


def test_default_credentials_still_work_for_local_dev(db_session):
    """Without env overrides the local development defaults are used."""
    user = auth_service.ensure_default_admin(db_session)
    assert user.username == "admin"
    assert verify_password("admin12345", user.password_hash) is True


def test_seed_is_idempotent(custom_admin, db_session):
    """Calling it twice must not create a second admin."""
    first = auth_service.ensure_default_admin(db_session)
    second = auth_service.ensure_default_admin(db_session)
    assert first.id == second.id
    assert auth_service.count_users(db_session) == 1


def test_default_credentials_are_flagged(custom_admin, db_session, caplog):
    """Using the shipped defaults in a custom env is still the dev default set."""
    import logging

    with caplog.at_level(logging.WARNING):
        auth_service.ensure_default_admin(db_session)
    # custom_admin changed the values, so no warning should fire
    assert "SECURITY WARNING" not in caplog.text


def test_warning_emitted_when_defaults_are_used(db_session, caplog):
    """The dev defaults should nag so they are not used in production."""
    import logging

    with caplog.at_level(logging.WARNING):
        auth_service.ensure_default_admin(db_session)
    assert "SECURITY WARNING" in caplog.text
