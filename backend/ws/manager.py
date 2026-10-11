from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from typing import List, Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections to the SOC live alerts stream (/ws/alerts).
    Supports client registration, graceful disconnection, and broadcast distribution.

    Threading model
    ---------------
    WebSocket handlers run on the asyncio event loop, while API endpoints
    (sync `def` routes) run in a threadpool with NO running loop. Broadcasts
    therefore go through `broadcast_sync`, which:

      * on the event loop thread  -> asyncio.create_task(...)
      * from a worker thread      -> asyncio.run_coroutine_threadsafe(...)
        onto the loop captured when a client connected
    """

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts and stores an active WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        self._capture_loop()
        logger.info("WebSocket client connected. Total active: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Removes a disconnected WebSocket client."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total active: %d", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]) -> int:
        """
        Broadcasts a JSON-serializable message dictionary to all active clients.
        Removes any stale or disconnected sockets automatically.
        Returns the number of clients successfully notified.
        """
        async with self._lock:
            stale_connections: List[WebSocket] = []
            successful_count = 0

            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                    successful_count += 1
                except Exception as exc:
                    logger.debug("Failed sending message to WebSocket client: %s", exc)
                    stale_connections.append(connection)

            for stale in stale_connections:
                if stale in self.active_connections:
                    self.active_connections.remove(stale)

            return successful_count

    def broadcast_sync(self, message: Dict[str, Any]) -> None:
        """
        Thread-safe helper to broadcast from synchronous routes or detection
        service functions without blocking.
        """
        try:
            # Called on the event loop thread (e.g. from async code)
            loop = asyncio.get_running_loop()
            self._capture_loop(loop)
            asyncio.create_task(self.broadcast(message))
            return
        except RuntimeError:
            pass

        # Called from a worker thread (sync API endpoint in threadpool) —
        # schedule the broadcast onto the loop that owns the sockets
        target_loop = self._loop
        if target_loop is not None and target_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self.broadcast(message), target_loop)
            future.add_done_callback(self._log_broadcast_errors)
            return

        # Last resort: no known loop (offline worker) — run a temporary one
        try:
            asyncio.run(self.broadcast(message))
        except Exception as exc:
            logger.debug("Could not dispatch broadcast_sync: %s", exc)

    # ── Internals ────────────────────────────────────────────────

    def _capture_loop(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Remember the event loop that owns the WebSocket connections."""
        if self._loop is None:
            self._loop = loop or asyncio.get_event_loop()

    @staticmethod
    def _log_broadcast_errors(future: concurrent.futures.Future) -> None:
        exc = future.exception()
        if exc is not None:
            logger.debug("Broadcast dispatch failed: %s", exc)


# Global singleton manager instance
ws_manager = ConnectionManager()
