"""Structured JSON logging with secret redaction.

No third-party logging dependency is used. Every log line is a JSON object so sync
failures can be filtered by run, provider, event, or error code.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
sync_run_id_var: ContextVar[int | None] = ContextVar("sync_run_id", default=None)

_SENSITIVE_KEY_MARKERS = (
    "token",
    "secret",
    "password",
    "authorization",
    "api_key",
    "apikey",
    "cookie",
    "x-auth-token",
)

# Matches common inline credential forms in free-text messages.
_INLINE_SECRET_PATTERNS = (
    re.compile(r"(?i)(x-auth-token\s*[:=]\s*)[^\s,;\"']+"),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;\"']+"),
    re.compile(r"(?i)((?:api[_-]?key|token|secret|password)\s*[=:]\s*)[^\s,;\"']+"),
)

_REDACTED = "[REDACTED]"
_MAX_MESSAGE_LENGTH = 4000


def redact_text(value: str) -> str:
    """Remove likely credentials from free text and bound its length."""

    redacted = value
    for pattern in _INLINE_SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: match.group(1) + _REDACTED, redacted)
    if len(redacted) > _MAX_MESSAGE_LENGTH:
        return redacted[:_MAX_MESSAGE_LENGTH] + "…[truncated]"
    return redacted


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS)


def redact_mapping(value: Any) -> Any:
    """Recursively redact a mapping/list while preserving structure and types."""

    if isinstance(value, dict):
        return {
            key: (
                _REDACTED
                if is_sensitive_key(str(key))
                else redact_mapping(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_mapping(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


class JsonFormatter(logging.Formatter):
    """Format log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }

        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id

        run_id = sync_run_id_var.get()
        if run_id is not None:
            payload["sync_run_id"] = run_id

        for key in (
            "event",
            "component",
            "provider",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "job_type",
            "records_fetched",
            "records_created",
            "records_updated",
            "records_rejected",
            "error_code",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = redact_mapping(value)

        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))

        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", *, stream: Any = None) -> None:
    """Configure the root logger once, without duplicating handlers.

    ``stream`` defaults to stdout for the API/worker. The operator CLI passes stderr so
    machine-readable command output on stdout is never mixed with log lines.
    """

    handler = logging.StreamHandler(stream=stream or sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Uvicorn installs its own handlers; route its records through ours.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "apscheduler"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
