"""
Tests for the log sanitising helpers (Phase 8).

The WebSocket JWT travels in the query string, so the access log must
never write it to disk.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.logging_config import (
    SafeAccessFormatter,
    SafeDefaultFormatter,
    strip_query_string,
)


# ── strip_query_string ───────────────────────────────────────────

def test_strip_query_string_removes_token():
    assert strip_query_string("/ws/alerts?token=abc.def.ghi") == "/ws/alerts"


def test_strip_query_string_keeps_path_without_query():
    assert strip_query_string("/api/v1/health") == "/api/v1/health"


def test_strip_query_string_keeps_http_version():
    assert strip_query_string("GET /x?y=1 HTTP/1.1") == "GET /x HTTP/1.1"


def test_strip_query_string_leaves_prose_alone():
    """A message with a question mark but no path is not a URL."""
    assert strip_query_string("is this ok?") == "is this ok?"
    assert strip_query_string("") == ""


# ── Formatters ───────────────────────────────────────────────────

def test_default_formatter_redacts_websocket_line():
    """uvicorn logs WebSocket handshakes through the error logger."""
    formatter = SafeDefaultFormatter(fmt="%(levelprefix)s %(message)s", use_colors=None)
    record = logging.LogRecord(
        "uvicorn.error", logging.INFO, "", 0,
        '%s - "WebSocket %s" [accepted]',
        ("127.0.0.1", "/ws/alerts?token=SECRET_TOKEN"),
        None,
    )
    out = formatter.format(record)
    assert "SECRET_TOKEN" not in out
    assert "/ws/alerts" in out
    assert "token=" not in out


def test_access_formatter_redacts_http_line():
    formatter = SafeAccessFormatter(
        fmt='%(client_addr)s - "%(request_line)s" %(status_code)s', use_colors=None
    )
    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, "", 0,
        '%s - "%s %s HTTP/%s" %d',
        ("1.2.3.4", "GET", "/api/v1/logs?token=SECRET_TOKEN", "1.1", 200),
        None,
    )
    out = formatter.format(record)
    assert "SECRET_TOKEN" not in out
    assert "/api/v1/logs" in out
    assert "200 OK" in out


def test_default_formatter_keeps_ordinary_messages():
    formatter = SafeDefaultFormatter(fmt="%(levelprefix)s %(message)s", use_colors=None)
    record = logging.LogRecord(
        "uvicorn.error", logging.WARNING, "", 0,
        "Rejected WebSocket connection: Invalid or missing token",
        None,
        None,
    )
    out = formatter.format(record)
    assert "Rejected WebSocket connection" in out
    assert "Invalid or missing token" in out
