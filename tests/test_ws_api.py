"""
Tests for the real-time WebSocket alerting (Phase 7).

Covers:
  - Connection handshake (CONNECTION_ESTABLISHED)
  - Heartbeat ping → PONG
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.ws.manager import ConnectionManager, ws_manager


# ── Integration: /ws/alerts endpoint ─────────────────────────────

def test_ws_handshake_and_heartbeat(client):
    """Connecting to /ws/alerts yields a handshake; ping gets PONG."""
    with client.websocket_connect("/ws/alerts") as ws:
        handshake = ws.receive_json()
        assert handshake["type"] == "CONNECTION_ESTABLISHED"
        assert "message" in handshake
        assert "timestamp" in handshake

        ws.send_text("ping")
        pong = ws.receive_json()
        assert pong["type"] == "PONG"
        assert "timestamp" in pong


def test_ws_receives_live_incident_broadcast(client):
    """
    Ingesting attack logs while a dashboard is connected must push a
    NEW_INCIDENT message over the WebSocket — the core Phase 7 flow.
    """
    with client.websocket_connect("/ws/alerts") as ws:
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
        res = client.post("/api/v1/logs/bulk", json={"logs": logs})
        assert res.status_code == 201

        # The broadcast must arrive without any polling
        message = ws.receive_json()
        assert message["type"] == "NEW_INCIDENT"
        assert message["incident"]["type"] == "BRUTE_FORCE"
        assert message["incident"]["severity"] == "HIGH"
        assert message["incident"]["status"] == "OPEN"
        assert "timestamp" in message


def test_ws_broadcast_incident_update(client):
    """PATCHing an incident status broadcasts INCIDENT_UPDATED."""
    with client.websocket_connect("/ws/alerts") as ws:
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
        client.post("/api/v1/logs/bulk", json={"logs": logs})
        ws.receive_json()  # NEW_INCIDENT

        incident_id = client.get("/api/v1/incidents").json()["items"][0]["id"]
        patch_res = client.patch(
            f"/api/v1/incidents/{incident_id}",
            json={"status": "INVESTIGATING"},
        )
        assert patch_res.status_code == 200

        message = ws.receive_json()
        assert message["type"] == "INCIDENT_UPDATED"
        assert message["incident_id"] == incident_id
        assert message["status"] == "INVESTIGATING"


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
