"""Audit logging for MCP server operations.

Provides immutable, append-only audit logging with JSON Lines format
for all tool executions and security events.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Patterns for sensitive argument keys
SENSITIVE_PATTERNS = [
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"auth", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
]


def _is_sensitive_key(key: str) -> bool:
    """Check if a key name indicates sensitive data."""
    return any(pattern.search(key) for pattern in SENSITIVE_PATTERNS)


def _sanitize_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """Sanitize arguments by redacting sensitive values.

    Args:
        arguments: Original arguments dictionary.

    Returns:
        New dictionary with sensitive values redacted.
    """
    sanitized = {}
    for key, value in arguments.items():
        if _is_sensitive_key(key):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_arguments(value)
        else:
            sanitized[key] = value
    return sanitized


def _get_timestamp() -> str:
    """Get current UTC timestamp in ISO 8601 format."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class AuditEvent:
    """Represents a tool execution audit event."""

    timestamp: str
    request_id: str
    tool_name: str
    arguments: dict[str, Any]
    result_status: str
    execution_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result_status": self.result_status,
            "execution_time_ms": self.execution_time_ms,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class SecurityEvent:
    """Represents a security-related event."""

    timestamp: str
    event_type: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "details": self.details,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """Append-only audit logger with JSON Lines format.

    All operations are logged with timestamps, and the log file is
    flushed after each write for durability.
    """

    def __init__(self, log_path: Path) -> None:
        """Initialize the audit logger.

        Args:
            log_path: Path to the audit log file.
        """
        self._log_path = log_path
        self._ensure_directory()
        self._file = open(log_path, "a", encoding="utf-8")  # noqa: SIM115

    def _ensure_directory(self) -> None:
        """Create log directory if it doesn't exist."""
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_line(self, data: dict[str, Any]) -> None:
        """Write a JSON line to the log file and flush."""
        line = json.dumps(data)
        self._file.write(line + "\n")
        self._file.flush()

    def log_request(self, request_id: str, tool_name: str, arguments: dict[str, Any]) -> None:
        """Log an incoming tool request.

        Args:
            request_id: Unique identifier for this request.
            tool_name: Name of the tool being invoked.
            arguments: Tool arguments (will be sanitized).
        """
        sanitized_args = _sanitize_arguments(arguments)
        event = {
            "type": "request",
            "timestamp": _get_timestamp(),
            "request_id": request_id,
            "tool_name": tool_name,
            "arguments": sanitized_args,
        }
        self._write_line(event)

    def log_response(self, request_id: str, status: str, duration_ms: float) -> None:
        """Log a tool response.

        Args:
            request_id: Request identifier to correlate with.
            status: Result status (success/error).
            duration_ms: Execution time in milliseconds.
        """
        event = {
            "type": "response",
            "timestamp": _get_timestamp(),
            "request_id": request_id,
            "result_status": status,
            "execution_time_ms": duration_ms,
        }
        self._write_line(event)

    def log_security_event(self, event_type: str, details: dict[str, Any]) -> None:
        """Log a security-related event.

        Args:
            event_type: Type of security event (blocked, violation, etc.).
            details: Additional details about the event.
        """
        event = {
            "type": "security",
            "timestamp": _get_timestamp(),
            "event_type": event_type,
            "details": details,
        }
        self._write_line(event)

    def close(self) -> None:
        """Close the log file."""
        if self._file and not self._file.closed:
            self._file.close()

    def __enter__(self) -> AuditLogger:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
