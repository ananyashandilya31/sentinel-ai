"""
Logging helpers for SentinelAI.

The WebSocket handshake carries the JWT in the query string
(`/ws/alerts?token=…`), and uvicorn logs the full request line — which
would write live tokens to disk on every connection.

The formatters here strip query strings from any logged URL, so access
logs stay useful without leaking credentials.

Why a custom formatter is needed
--------------------------------
uvicorn emits the request line in two different places:

  * HTTP      → ``uvicorn.access`` logger, args
                ``(client_addr, method, full_path, http_version, status_code)``
  * WebSocket → ``uvicorn.error`` logger (!), args
                ``(client_addr, path_with_query_string)``

The WebSocket line is logged through the *error* logger, so the
redaction has to be applied to every formatter, not just the access one.

Implementation note
-------------------
``logging.Formatter.format()`` renders ``record.message`` from
``record.getMessage()`` *before* calling ``formatMessage()``. Mutating
``record.args`` inside ``formatMessage()`` is therefore too late — the
sanitising has to happen in ``format()``.
"""
from __future__ import annotations

import logging
from copy import copy

try:  # uvicorn is optional at import time (e.g. during unit tests)
    from uvicorn.logging import AccessFormatter, DefaultFormatter
except Exception:  # pragma: no cover
    class DefaultFormatter(logging.Formatter):  # type: ignore[no-redef]
        """Fallback so the module imports without uvicorn installed."""

        def format(self, record: logging.LogRecord) -> str:
            return super().format(record)

    class AccessFormatter(DefaultFormatter):  # type: ignore[no-redef]
        """Fallback so the module imports without uvicorn installed."""


def strip_query_string(value: str) -> str:
    """
    Remove the query string from a URL-ish string.

    '/ws/alerts?token=abc'  -> '/ws/alerts'
    'GET /x?y=1 HTTP/1.1'   -> 'GET /x HTTP/1.1'

    Only strings that look like a path with a query are touched, so
    ordinary log messages containing a question mark are left alone.
    """
    if not value or "?" not in value:
        return value
    if "/" not in value:
        return value
    head, _, tail = value.partition("?")
    parts = tail.split(" ", 1)
    remainder = f" {parts[1]}" if len(parts) > 1 else ""
    return f"{head}{remainder}"


def _sanitize_args(args):
    """Strip query strings from every string in a log record's args."""
    if isinstance(args, dict):
        return {
            k: (strip_query_string(v) if isinstance(v, str) else v)
            for k, v in args.items()
        }
    if isinstance(args, tuple):
        return tuple(strip_query_string(a) if isinstance(a, str) else a for a in args)
    return args


class _QueryStringStripperMixin:
    """Mixin that removes query strings from a record before rendering."""

    def format(self, record: logging.LogRecord) -> str:
        if record.args:
            safe_record = copy(record)
            safe_record.args = _sanitize_args(record.args)
            record = safe_record
        return super().format(record)


class SafeDefaultFormatter(_QueryStringStripperMixin, DefaultFormatter):
    """Formatter for uvicorn.error (and the WebSocket access lines)."""


class SafeAccessFormatter(_QueryStringStripperMixin, AccessFormatter):
    """Formatter for uvicorn.access (HTTP request lines)."""
