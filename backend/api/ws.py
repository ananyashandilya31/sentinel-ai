"""
WebSocket Router for Real-Time SOC Alerting — /ws/alerts & /api/v1/ws/alerts
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.ws.manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Real-Time WebSockets"])


async def handle_alert_websocket(websocket: WebSocket) -> None:
    """Handles an active WebSocket connection to the real-time SOC alerts stream."""
    await ws_manager.connect(websocket)

    # Initial handshake acknowledgment
    try:
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to SentinelAI SOC live alerts stream.",
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
async def alerts_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time incident and detection alerts."""
    await handle_alert_websocket(websocket)
