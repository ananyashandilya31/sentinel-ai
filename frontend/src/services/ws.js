/**
 * WebSocket Service for SentinelAI real-time SOC alerting.
 *
 * Connects to the backend live alerts stream (GET /ws/alerts) and
 * distributes incoming JSON messages to subscribed listeners.
 *
 * Features:
 *   - JWT auth: the stored token is sent as a `?token=` query parameter
 *     (browsers cannot set headers on a WebSocket handshake)
 *   - Automatic reconnection with exponential backoff (1s → 30s max)
 *   - Stops retrying when the server rejects the token (close code 1008)
 *   - Heartbeat (client "ping" → server "PONG") to detect dead sockets
 *   - Multiple subscribers per connection (pub/sub pattern)
 *   - Connection state tracking for UI indicators
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const TOKEN_KEY = 'sentinelai_token';

/** Close code the server uses to reject a bad/missing token. */
const WS_POLICY_VIOLATION = 1008;

/** Convert an http(s) base URL to its ws(s) equivalent. */
function toWsUrl(base) {
  const url = `${base}/ws/alerts`;
  return url.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
}

/** Build the connection URL, attaching the stored JWT if we have one. */
function buildUrl() {
  const url = toWsUrl(API_BASE_URL);
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return url;
  return `${url}?token=${encodeURIComponent(token)}`;
}

export const WS_STATE = {
  CONNECTING: 'CONNECTING',
  OPEN: 'OPEN',
  RECONNECTING: 'RECONNECTING',
  CLOSED: 'CLOSED',
  UNAUTHORIZED: 'UNAUTHORIZED',
};

const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_DELAY_MS = 30000;
const HEARTBEAT_INTERVAL_MS = 30000;

class LiveAlertsSocket {
  constructor() {
    this.url = toWsUrl(API_BASE_URL);
    this.socket = null;
    this.state = WS_STATE.CLOSED;
    this.listeners = new Set();
    this.reconnectAttempts = 0;
    this.reconnectTimer = null;
    this.heartbeatTimer = null;
    this.shouldRun = false; // user-intent flag: true between connect() and disconnect()
    this.lastMessageAt = null;
  }

  /** Open the connection and keep it alive until disconnect(). */
  connect() {
    this.shouldRun = true;
    // Idempotent: never open a second socket while one is live
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }
    this._open();
  }

  /** Close the connection and stop auto-reconnect. */
  disconnect() {
    this.shouldRun = false;
    this._clearTimers();
    if (this.socket) {
      this.socket.onopen = null;
      this.socket.onmessage = null;
      this.socket.onclose = null;
      this.socket.onerror = null;
      this.socket.close();
      this.socket = null;
    }
    this._setState(WS_STATE.CLOSED);
  }

  /**
   * Subscribe to live alert messages.
   * @param {(message: object) => void} listener
   * @returns {() => void} unsubscribe function
   */
  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /** Send a text message (used for heartbeat pings). */
  send(text) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(text);
    }
  }

  // ── Internals ────────────────────────────────────────────────────────

  _open() {
    this._clearTimers();
    this._setState(
      this.reconnectAttempts > 0 ? WS_STATE.RECONNECTING : WS_STATE.CONNECTING
    );

    let socket;
    try {
      // Rebuild the URL each time so a refreshed token is picked up
      socket = new WebSocket(buildUrl());
    } catch (err) {
      console.error('WebSocket constructor failed:', err);
      this._scheduleReconnect();
      return;
    }
    this.socket = socket;

    socket.onopen = () => {
      this.reconnectAttempts = 0;
      this._setState(WS_STATE.OPEN);
      this._startHeartbeat();
    };

    socket.onmessage = (event) => {
      this.lastMessageAt = Date.now();
      let message = event.data;
      try {
        message = JSON.parse(event.data);
      } catch {
        // Non-JSON text — deliver raw
      }
      this.listeners.forEach((listener) => {
        try {
          listener(message);
        } catch (err) {
          console.error('Live alert listener error:', err);
        }
      });
    };

    socket.onclose = (event) => {
      this._clearTimers();

      // 1008 = policy violation → the server rejected our token.
      // Retrying with the same token would just loop, so stop here and
      // let the user sign in again.
      if (event && event.code === WS_POLICY_VIOLATION) {
        this.shouldRun = false;
        this._setState(WS_STATE.UNAUTHORIZED);
        console.warn('Live alert stream rejected the token — sign in again.');
        return;
      }

      if (this.shouldRun) {
        this._setState(WS_STATE.RECONNECTING);
        this._scheduleReconnect();
      } else {
        this._setState(WS_STATE.CLOSED);
      }
    };

    socket.onerror = () => {
      // onclose always fires after onerror — reconnection is handled there
    };
  }

  _scheduleReconnect() {
    if (!this.shouldRun) return;
    const delay = Math.min(
      RECONNECT_BASE_DELAY_MS * 2 ** this.reconnectAttempts,
      RECONNECT_MAX_DELAY_MS
    );
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => this._open(), delay);
  }

  _startHeartbeat() {
    this._clearTimers();
    this.heartbeatTimer = setInterval(() => {
      this.send('ping');
    }, HEARTBEAT_INTERVAL_MS);
  }

  _clearTimers() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  _setState(state) {
    if (this.state !== state) {
      this.state = state;
      // Notify subscribers of connection-state changes with a meta message
      this.listeners.forEach((listener) => {
        try {
          listener({ type: 'CONNECTION_STATE', state });
        } catch (err) {
          console.error('Live alert listener error:', err);
        }
      });
    }
  }
}

/** Process-wide singleton shared by all components. */
export const liveAlertsSocket = new LiveAlertsSocket();
