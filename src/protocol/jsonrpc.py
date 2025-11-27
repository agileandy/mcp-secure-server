"""JSON-RPC 2.0 message parsing and formatting.

Implements the JSON-RPC 2.0 specification for MCP protocol communication.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

# Standard JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Maximum message size (1 MB)
MAX_MESSAGE_SIZE = 1_048_576


class JsonRpcError(Exception):
    """JSON-RPC error with code and message."""

    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        """Initialize the error.

        Args:
            code: JSON-RPC error code.
            message: Human-readable error message.
            data: Optional additional error data.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


@dataclass
class JsonRpcRequest:
    """Represents a JSON-RPC request (has id)."""

    id: int | str
    method: str
    params: dict[str, Any] | None = None


@dataclass
class JsonRpcNotification:
    """Represents a JSON-RPC notification (no id)."""

    method: str
    params: dict[str, Any] | None = None


def parse_message(raw: str) -> JsonRpcRequest | JsonRpcNotification:
    """Parse a JSON-RPC message from a string.

    Args:
        raw: Raw JSON string.

    Returns:
        Parsed request or notification.

    Raises:
        JsonRpcError: If the message is invalid.
    """
    # Check message size before parsing to prevent DoS
    if len(raw) > MAX_MESSAGE_SIZE:
        raise JsonRpcError(
            PARSE_ERROR, f"Message too large: {len(raw)} bytes exceeds {MAX_MESSAGE_SIZE} limit"
        )

    # Parse JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise JsonRpcError(PARSE_ERROR, f"Parse error: {e}") from e

    # Must be an object
    if not isinstance(data, dict):
        raise JsonRpcError(INVALID_REQUEST, "Invalid Request: message must be an object")

    # Validate jsonrpc version
    if data.get("jsonrpc") != "2.0":
        raise JsonRpcError(INVALID_REQUEST, "Invalid Request: jsonrpc must be '2.0'")

    # Must have method
    method = data.get("method")
    if not isinstance(method, str):
        raise JsonRpcError(INVALID_REQUEST, "Invalid Request: method must be a string")

    # Get params (optional)
    params = data.get("params")
    if params is not None and not isinstance(params, dict):
        raise JsonRpcError(INVALID_REQUEST, "Invalid Request: params must be an object")

    # Check for id to distinguish request from notification
    if "id" in data:
        msg_id = data["id"]
        if not isinstance(msg_id, int | str):
            raise JsonRpcError(INVALID_REQUEST, "Invalid Request: id must be integer or string")
        return JsonRpcRequest(id=msg_id, method=method, params=params)
    else:
        return JsonRpcNotification(method=method, params=params)


def format_response(msg_id: int | str, result: Any) -> str:
    """Format a successful JSON-RPC response.

    Args:
        msg_id: Request ID to echo back.
        result: Result payload.

    Returns:
        JSON string.
    """
    response = {
        "jsonrpc": "2.0",
        "id": msg_id,
        "result": result,
    }
    return json.dumps(response)


def format_error(
    msg_id: int | str | None,
    code: int,
    message: str,
    data: Any | None = None,
) -> str:
    """Format a JSON-RPC error response.

    Args:
        msg_id: Request ID (or None for parse errors).
        code: Error code.
        message: Error message.
        data: Optional error data.

    Returns:
        JSON string.
    """
    error_obj: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if data is not None:
        error_obj["data"] = data

    response = {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": error_obj,
    }
    return json.dumps(response)


def format_notification(method: str, params: dict[str, Any] | None = None) -> str:
    """Format a JSON-RPC notification (server to client).

    Args:
        method: Notification method name.
        params: Optional parameters.

    Returns:
        JSON string.
    """
    notification: dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": method,
    }
    if params is not None:
        notification["params"] = params

    return json.dumps(notification)
