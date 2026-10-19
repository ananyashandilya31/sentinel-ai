"""
Tests for the real-time WebSocket alerting (Phase 7/8).

Covers:
  - JWT authentication on the WebSocket handshake
      · valid token            -> connected
      · missing token          -> rejected (close code 1008)
      · tampered/invalid token -> rejected
      · expired token          -> rejected
      · token for a deactivated user -> rejected
      · demo mode (AUTH_ENABLED=false) allows a token-less connection,
        but a bad token is still refused
  - Connection handshake (CONNECTION_ESTABLISHED) and heartbeat (PONG)
  - Live NEW_INCIDENT broadcast when attack logs are ingested
  - INCIDENT_UPDATED broadcast on status change
  - ConnectionManager unit behaviour (broadcast, stale cleanup, disconnect)
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import WebSocketDisconnect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import settings
from backend.models.user import User
from backend.security import create_access_token, hash_password
from backend.ws.manager import ConnectionManager, ws_manager

WS_POLICY_VIOLATION = 1008


def _url(token: str | None = None) -> str:
    """Build the WebSocket URL, optionally with a token."""
    return "/ws/alerts" if not token else f"/ws/alerts?token={token}"


def _assert_rejected(ws) -> None:
    """The server must close the socket with 1008 (policy violation)."""
    with pytest.raises(WebSocketDisconnect) as exc:
        ws.receive_json()
    assert exc.value.code == WS_POLICY_VIOLATION


# ── Authentication ──────────────────────────────────────────────

def test_ws_with_valid_token_connects(auth_client, admin_token):
    """A valid JWT opens the stream and gets the handshake."""
    with auth_client.websocket_connect(_url(admin_token)) as ws:
        handshake = ws.receive_json()
        assert handshake["type"] == "CONNECTION_ESTABLISHED"
        assert handshake["user"] == "admin"


def test_ws_without_token_is_rejected(auth_client):
    """AUTH_ENABLED is on, so a tokenless connection must be refused."""
    with auth_client.websocket_connect(_url()) as ws:
        _assert_rejected(ws)


def test_ws_with_invalid_token_is_rejected(auth_client):
    """A garbage token must not open the stream."""
    with auth_client.websocket_connect(_url("not-a-real-jwt")) as ws:
        _assert_rejected(ws)


def test_ws_with_tampered_token_is_rejected(auth_client, admin_token):
    """A token signed with the wrong secret must be refused."""
    from jose import jwt

    forged = jwt.encode({"sub": "admin", "role": "ADMIN"}, "wrong_secret", algorithm="HS256")
    with auth_client.websocket_connect(_url(forged)) as ws:
        _assert_rejected(ws)


def test_ws_with_expired_token_is_rejected(auth_client):
    """An expired token must be refused even though it is well-formed."""
    from jose import jwt

    expired = jwt.encode(
        {
            "sub": "admin",
            "role": "ADMIN",
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    with auth_client.websocket_connect(_url(expired)) as ws:
        _assert_rejected(ws)


def test_ws_with_deactivated_user_token_is_rejected(auth_client, db_session):
    """A token for a user who was deactivated must be refused."""
    user = User(
        username="disabled_analyst",
        password_hash=hash_password("analyst12345"),
        role="ANALYST",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token("disabled_analyst", "ANALYST")
    with auth_client.websocket_connect(_url(token)) as ws:
        _assert_rejected(ws)


def test_ws_with_unknown_user_token_is_rejected(auth_client):
    """A validly-signed token for a user that does not exist is refused."""
    token = create_access_token("ghost_user", "ANALYST")
    with auth_client.websocket_connect(_url(token)) as ws:
        _assert_rejected(ws)


def test_ws_demo_mode_allows_tokenless_connection(auth_client):
    """With AUTH_ENABLED off, the console can connect without a token."""
    previous = settings.AUTH_ENABLED
    settings.AUTH_ENABLED = False
    try:
        with auth_client.websocket_connect(_url()) as ws:
            handshake = ws.receive_json()
            assert handshake["type"] == "CONNECTION_ESTABLISHED"
    finally:
        settings.AUTH_ENABLED = previous


def test_ws_demo_mode_still_rejects_a_bad_token(auth_client):
    """Relaxing auth must not mean a supplied token is ignored."""
    previous = settings.AUTH_ENABLED
    settings.AUTH_ENABLED = False
    try:
        with auth_client.websocket_connect(_url("garbage.token.here")) as ws:
            _assert_rejected(ws)
    finally:
        settings.AUTH_ENABLED = previous


# ── Handshake & heartbeat ────────────────────────────────────────

def test_ws_handshake_and_heartbeat(auth_client, admin_token):
    """Connecting yields a handshake; ping gets PONG."""
    with auth_client.websocket_connect(_url(admin_token)) as ws:
        handshake = ws.receive_json()
        assert handshake["type"] == "CONNECTION_ESTABLISHED"
        assert "message" in handshake
        assert "timestamp" in handshake

        ws.send_text("ping")
        pong = ws.receive_json()
        assert pong["type"] == "PONG"
        assert "timestamp" in pong


# ── Live broadcast ───────────────────────────────────────────────

def test_ws_receives_live_incident_broadcast(auth_client, admin_token):
    """
    Ingesting attack logs while a dashboard is connected must push a
    NEW_INCIDENT message over the WebSocket — the core Phase 7 flow.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    with auth_client.websocket_connect(_url(admin_token)) as ws:
        handshake = ws.receive_json()
        assert handshake["type"] == "CONNECTION_ESTABLISHED"

        # Fire a brute-force burst through the ingestion pipeline
        now = datetime.now(timezone.utc)
        logs = [
            {
                "user": "admin",
                "ip": "185.220.101.5",
                "event_type": "LOGIN_FAILED",
                "port": 443,
                "session_id": f"s-ws-{i}",
                "timestamp": (now + timedelta(seconds=i * 5)).isoformat(),
            }
            for i in range(10)
        ]
        res = auth_client.post("/api/v1/logs/bulk", json={"logs": logs}, headers=headers)
        assert res.status_code == 201

        # The broadcast must arrive without any polling
        message = ws.receive_json()
        assert message["type"] == "NEW_INCIDENT"
        assert message["incident"]["type"] == "BRUTE_FORCE"
        assert message["incident"]["severity"] == "HIGH"
        assert message["incident"]["status"] == "OPEN"
        assert "timestamp" in message


def test_ws_broadcast_incident_update(auth_client, admin_token):
    """PATCHing an incident status broadcasts INCIDENT_UPDATED."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    with auth_client.websocket_connect(_url(admin_token)) as ws:
        ws.receive_json()  # handshake

        # Create an incident first
        now = datetime.now(timezone.utc)
        logs = [
            {
                "user": "admin",
                "ip": "185.220.101.5",
                "event_type": "LOGIN_FAILED",
                "port": 443,
                "session_id": f"s-ws-upd-{i}",
                "timestamp": (now + timedelta(seconds=i * 5)).isoformat(),
            }
            for i in range(10)
        ]
        auth_client.post("/api/v1/logs/bulk", json={"logs": logs}, headers=headers)
        ws.receive_json()  # NEW_INCIDENT

        incident_id = auth_client.get("/api/v1/incidents", headers=headers).json()["items"][0]["id"]
        patch_res = auth_client.patch(
            f"/api/v1/incidents/{incident_id}",
            json={"status": "INVESTIGATING"},
            headers=headers,
        )
        assert patch_res.status_code == 200

        message = ws.receive_json()
        assert message["type"] == "INCIDENT_UPDATED"
        assert message["incident_id"] == incident_id
        assert message["status"] == "INVESTIGATING"


def test_ws_rejected_socket_receives_no_alerts(auth_client, admin_token):
    """A rejected client must never see incident data."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    with auth_client.websocket_connect(_url("bad.token.value")) as ws:
        # The very first frame is the close frame — no data is delivered
        _assert_rejected(ws)


# ── Unit: ConnectionManager ──────────────────────────────────────

def test_manager_broadcast_to_all():
    """broadcast() sends the message to every connected client."""
    async def scenario():
        manager = ConnectionManager()
        mock_a, mock_b = AsyncMock(), AsyncMock()
        mock_a.send_json = AsyncMock()
        mock_b.send_json = AsyncMock()

        await manager.connect(mock_a)
        await manager.connect(mock_b)

        delivered = await manager.broadcast({"type": "TEST"})
        assert delivered == 2
        mock_a.send_json.assert_awaited_once_with({"type": "TEST"})
        mock_b.send_json.assert_awaited_once_with({"type": "TEST"})

    asyncio.run(scenario())


def test_manager_removes_stale_connections():
    """Clients that fail mid-broadcast are dropped from the pool."""
    async def scenario():
        manager = ConnectionManager()
        mock_good, mock_dead = AsyncMock(), AsyncMock()
        mock_good.send_json = AsyncMock()
        mock_dead.send_json = AsyncMock(side_effect=RuntimeError("socket closed"))

        await manager.connect(mock_good)
        await manager.connect(mock_dead)

        delivered = await manager.broadcast({"type": "TEST"})
        assert delivered == 1
        assert mock_good in manager.active_connections
        assert mock_dead not in manager.active_connections

    asyncio.run(scenario())


def test_manager_disconnect():
    """disconnect() removes the client from the active pool."""
    async def scenario():
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        await manager.connect(mock_ws)
        assert len(manager.active_connections) == 1

        await manager.disconnect(mock_ws)
        assert len(manager.active_connections) == 0

    asyncio.run(scenario())


def test_singleton_manager_exists():
    """The module exposes a process-wide ws_manager singleton."""
    assert isinstance(ws_manager, ConnectionManager)