"""
WebSocket Router for Real-Time SOC Alerting — /ws/alerts & /api/v1/ws/alerts

Authentication
--------------
Browsers cannot set headers on a WebSocket handshake, so the JWT is
passed as a `?token=` query parameter (the standard approach).

Rules:
  * AUTH_ENABLED=True  → a valid token is REQUIRED
  * AUTH_ENABLED=False → token optional (local demo mode), but if one IS
    supplied it must still be valid — a bad token is never accepted
  * An invalid, expired or deactivated-user token is rejected with
    WebSocket close code 1008 (policy violation)

The connection is accepted and then immediately closed on failure so the
client can read the close code and distinguish "your token is bad"
(stop retrying) from "the network blipped" (reconnect with backoff).
No alert data is ever sent to a rejected socket.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.user import User
from backend.security import decode_access_token
from backend.ws.manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Real-Time WebSockets"])

# Close code meaning "policy violation" — used for auth failures so the
# client can tell an auth rejection apart from a network drop.
WS_POLICY_VIOLATION = status.WS_1008_POLICY_VIOLATION


def _extract_token(websocket: WebSocket) -> Optional[str]:
    """Pull the JWT out of the `token` query parameter."""
    token = websocket.query_params.get("token")
    if not token:
        return None
    token = token.strip()
    return token or None


def _resolve_user(token: Optional[str], db: Session) -> Optional[User]:
    """
    Resolve the token to an active user.

    Returns None when the token is missing, invalid, expired, or belongs
    to a user that no longer exists or has been deactivated.
    """
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    username = payload.get("sub")
    if not username:
        return None

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        return None

    return user


async def _reject(websocket: WebSocket, reason: str) -> None:
    """
    Accept then immediately close with 1008 so the client can read the
    close code. No data is ever delivered on this socket.
    """
    try:
        await websocket.accept()
        await websocket.close(code=WS_POLICY_VIOLATION, reason=reason)
    except Exception as exc:
        logger.debug("Failed to close rejected WebSocket: %s", exc)
    logger.warning("Rejected WebSocket connection: %s", reason)


async def handle_alert_websocket(websocket: WebSocket, db: Session) -> None:
    """Handles an active WebSocket connection to the real-time SOC alerts stream."""
    token = _extract_token(websocket)

    try:
        user = _resolve_user(token, db)
    finally:
        # Release the DB session immediately. A WebSocket can stay open for
        # hours; holding a pooled connection (and, on SQLite, a file lock)
        # that long would block every other writer in the app.
        db.close()

    # A supplied token must always be valid, even in demo mode.
    # A missing token is only tolerated when auth is switched off.
    if user is None:
        if token is None and not settings.AUTH_ENABLED:
            logger.info("WebSocket connected without token (AUTH_ENABLED=false)")
        else:
            await _reject(websocket, "Invalid or missing token")
            return

    await ws_manager.connect(websocket)

    # Initial handshake acknowledgment
    try:
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to SentinelAI SOC live alerts stream.",
            "user": user.username if user else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.debug("Failed sending handshake to client: %s", exc)

    try:
        while True:
            # Receive client heartbeats or messages
            message = await websocket.receive_text()

            # Respond to heartbeat pings
            if "ping" in message.lower():
                await websocket.send_json({
                    "type": "PONG",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.debug("WebSocket connection error: %s", exc)
        await ws_manager.disconnect(websocket)


@router.websocket("/alerts")
async def alerts_websocket_endpoint(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """WebSocket endpoint for real-time incident and detection alerts."""
    await handle_alert_websocket(websocket, db)