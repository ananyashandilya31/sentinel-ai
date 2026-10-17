"""
Tests for authentication and authorization (Phase 8).

Covers:
  - Password hashing (bcrypt) and verification
  - JWT creation / decoding / expiry / tampering
  - POST /auth/login success + failure paths
  - Login rate limiting (429 after repeated failures)
  - GET /auth/me requires a valid token
  - POST /auth/register is admin-only (403 for analysts)
  - Protected write endpoints reject missing/invalid tokens
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.security import (
    PasswordTooLongError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# ── Password hashing ─────────────────────────────────────────────

def test_hash_password_is_bcrypt_and_not_plaintext():
    hashed = hash_password("supersecret123")
    assert hashed.startswith("$2")
    assert "supersecret123" not in hashed


def test_verify_password_accepts_correct_password():
    hashed = hash_password("supersecret123")
    assert verify_password("supersecret123", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("supersecret123")
    assert verify_password("wrongpassword", hashed) is False


def test_same_password_hashes_differently_each_time():
    """bcrypt salts every hash — identical passwords must not collide."""
    assert hash_password("samepass123") != hash_password("samepass123")


def test_password_over_72_bytes_is_rejected():
    """Truncation would make two distinct passwords equivalent."""
    with pytest.raises(PasswordTooLongError):
        hash_password("x" * 73)


# ── JWT ──────────────────────────────────────────────────────────

def test_create_and_decode_token():
    token = create_access_token("alice", "ANALYST")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "alice"
    assert payload["role"] == "ANALYST"


def test_token_signed_with_wrong_secret_is_rejected():
    from jose import jwt

    forged = jwt.encode({"sub": "admin", "role": "ADMIN"}, "not_the_secret", algorithm="HS256")
    assert decode_access_token(forged) is None


def test_expired_token_is_rejected():
    from jose import jwt

    from backend.config import settings

    expired = jwt.encode(
        {
            "sub": "admin",
            "role": "ADMIN",
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert decode_access_token(expired) is None


def test_garbage_token_returns_none():
    assert decode_access_token("not-a-real-token") is None


# ── /auth/login ──────────────────────────────────────────────────

def test_login_success_returns_token_and_user(auth_client):
    auth_client.post("/api/v1/auth/seed")
    res = auth_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin12345"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert len(data["access_token"]) > 20
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "ADMIN"
    # Password hash must never leak
    assert "password_hash" not in data["user"]


def test_login_with_wrong_password_returns_401(auth_client):
    auth_client.post("/api/v1/auth/seed")
    res = auth_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrongpassword"},
    )
    assert res.status_code == 401


def test_login_unknown_user_gives_generic_error(auth_client):
    """Same message as a bad password — don't leak which usernames exist."""
    auth_client.post("/api/v1/auth/seed")
    res = auth_client.post(
        "/api/v1/auth/login",
        json={"username": "ghost_user", "password": "whatever123"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Incorrect username or password."


def test_login_rate_limited_after_repeated_failures(auth_client):
    """Repeated failures from one IP are throttled with 429."""
    from backend.config import settings

    auth_client.post("/api/v1/auth/seed")

    for _ in range(settings.LOGIN_MAX_ATTEMPTS):
        auth_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "badpassword"},
        )

    res = auth_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "badpassword"},
    )
    assert res.status_code == 429

    # Clear the throttle so it doesn't leak into other tests
    from backend.api.auth import _attempts

    _attempts.clear()


# ── /auth/me ─────────────────────────────────────────────────────

def test_me_requires_token(auth_client):
    res = auth_client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_me_returns_current_user(auth_client, auth_headers):
    res = auth_client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["username"] == "admin"
    assert res.json()["role"] == "ADMIN"


def test_me_rejects_invalid_token(auth_client):
    res = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer totally.invalid.token"},
    )
    assert res.status_code == 401


# ── /auth/register (admin only) ───────────────────────────────────

def test_register_requires_auth(auth_client):
    res = auth_client.post(
        "/api/v1/auth/register",
        json={"username": "analyst1", "password": "analyst12345"},
    )
    assert res.status_code == 401


def test_admin_can_register_analyst(auth_client, auth_headers):
    res = auth_client.post(
        "/api/v1/auth/register",
        json={"username": "analyst1", "password": "analyst12345", "role": "ANALYST"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    assert res.json()["role"] == "ANALYST"
    assert "password_hash" not in res.json()


def test_analyst_cannot_register_users(auth_client, auth_headers):
    """Role-based access control: only ADMIN may provision accounts."""
    auth_client.post(
        "/api/v1/auth/register",
        json={"username": "analyst1", "password": "analyst12345", "role": "ANALYST"},
        headers=auth_headers,
    )
    analyst_login = auth_client.post(
        "/api/v1/auth/login",
        json={"username": "analyst1", "password": "analyst12345"},
    )
    assert analyst_login.status_code == 200
    analyst_headers = {"Authorization": f"Bearer {analyst_login.json()['access_token']}"}

    res = auth_client.post(
        "/api/v1/auth/register",
        json={"username": "analyst2", "password": "analyst12345", "role": "ANALYST"},
        headers=analyst_headers,
    )
    assert res.status_code == 403


def test_register_duplicate_username_returns_409(auth_client, auth_headers):
    auth_client.post(
        "/api/v1/auth/register",
        json={"username": "analyst1", "password": "analyst12345"},
        headers=auth_headers,
    )
    res = auth_client.post(
        "/api/v1/auth/register",
        json={"username": "analyst1", "password": "different12345"},
        headers=auth_headers,
    )
    assert res.status_code == 409


def test_register_rejects_short_password(auth_client, auth_headers):
    res = auth_client.post(
        "/api/v1/auth/register",
        json={"username": "shorty", "password": "abc"},
        headers=auth_headers,
    )
    assert res.status_code == 422


# ── Protected endpoints ──────────────────────────────────────────

def test_write_endpoints_reject_missing_token(auth_client):
    """Ingesting logs without a token is refused when AUTH_ENABLED."""
    res = auth_client.post(
        "/api/v1/logs",
        json={
            "user": "alice",
            "ip": "10.0.0.5",
            "event_type": "LOGIN_SUCCESS",
            "session_id": "s-noauth-test",
        },
    )
    assert res.status_code == 401


def test_write_endpoint_accepts_valid_token(auth_client, auth_headers):
    res = auth_client.post(
        "/api/v1/logs",
        json={
            "user": "alice",
            "ip": "10.0.0.5",
            "event_type": "LOGIN_SUCCESS",
            "session_id": "s-auth-test",
        },
        headers=auth_headers,
    )
    assert res.status_code == 201


def test_read_endpoints_remain_open_for_monitoring(auth_client):
    """Health and list endpoints stay reachable for dashboards/monitoring."""
    assert auth_client.get("/api/v1/health").status_code == 200
    assert auth_client.get("/api/v1/incidents").status_code == 200
    assert auth_client.get("/api/v1/logs").status_code == 200


def test_seed_endpoint_requires_token(auth_client):
    res = auth_client.post("/api/v1/logs/seed?limit=20")
    assert res.status_code == 401


def test_health_endpoint_never_requires_auth(auth_client):
    """The health probe must work without credentials (load balancers)."""
    assert auth_client.get("/api/v1/health").status_code == 200
    assert auth_client.get("/").status_code == 200