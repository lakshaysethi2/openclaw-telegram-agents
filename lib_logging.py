"""Structured logging helpers for setup and generation tools.

Future maintainers (including smaller AI agents) should use these helpers so
errors stay explicit, machine-readable, and free of secrets.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

SECRET_KEY_FRAGMENTS: tuple[str, ...] = (
    "token",
    "password",
    "secret",
    "api_key",
    "apikey",
    "authorization",
)


def _is_secret_key(key: str) -> bool:
    """Return True when a mapping key looks like a secret field name."""
    lowered = key.lower()
    return any(fragment in lowered for fragment in SECRET_KEY_FRAGMENTS)


def redact_value(key: str, value: Any) -> Any:
    """Redact values whose keys look secret-bearing.

    Args:
        key: Field name associated with the value.
        value: Arbitrary value to optionally redact.

    Returns:
        The original value, or the string ``***REDACTED***``.
    """
    if _is_secret_key(key):
        return "***REDACTED***"
    return value


def redact_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of ``data`` with secret-looking fields redacted.

    Args:
        data: Mapping that may contain secrets.

    Returns:
        New dict safe for logs and exception context.
    """
    return {str(k): redact_value(str(k), v) for k, v in data.items()}


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line for easy AI/log scraping."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a single-line JSON document."""
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, Mapping):
            payload["context"] = redact_mapping(extra)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure root-style app logger with JSON lines on stderr.

    Args:
        level: Logging level name such as ``INFO`` or ``DEBUG``.

    Returns:
        Logger named ``openclaw_multi``.
    """
    logger = logging.getLogger("openclaw_multi")
    logger.handlers.clear()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_error(
    logger: logging.Logger,
    message: str,
    *,
    code: str,
    hint: str,
    context: Mapping[str, Any] | None = None,
) -> None:
    """Log a structured error with an explicit recovery hint.

    Args:
        logger: Target logger.
        message: Human-readable error summary.
        code: Stable machine-oriented error code (for grepping).
        hint: Concrete next action for a maintainer or operator.
        context: Optional non-secret diagnostic fields.
    """
    fields: dict[str, Any] = {"error_code": code, "hint": hint}
    if context:
        fields.update(redact_mapping(context))
    logger.error(message, extra={"extra_fields": fields})
