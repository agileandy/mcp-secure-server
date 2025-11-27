"""MCP Server - main entry point.

Integrates all components into a complete MCP server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.plugins.base import PluginBase
from src.plugins.dispatcher import ToolDispatcher
from src.protocol.jsonrpc import (
    JsonRpcError,
    JsonRpcNotification,
    JsonRpcRequest,
    format_error,
    format_response,
    parse_message,
)
from src.protocol.lifecycle import LifecycleManager, ProtocolError
from src.protocol.tools import ToolsHandler
from src.security.policy import SecurityPolicy, load_policy

# JSON-RPC error codes
METHOD_NOT_FOUND = -32601
INTERNAL_ERROR = -32603


class MCPServer:
    """MCP Server implementation.

    Provides a complete MCP server that handles:
    - Lifecycle management (initialize/initialized)
    - Tool listing and execution
    - Security policy enforcement
    """

    def __init__(self, policy_path: Path | None = None) -> None:
        """Initialize the server.

        Args:
            policy_path: Path to security policy YAML file.
        """
        # Load security policy
        if policy_path:
            self._policy = load_policy(policy_path)
        else:
            # Default minimal policy
            self._policy = SecurityPolicy.from_dict(
                {
                    "network": {"mode": "deny_all", "allowed_endpoints": []},
                    "filesystem": {"allowed_paths": [], "denied_paths": []},
                    "tools": {"allowed": [], "timeout": 30, "rate_limits": {}},
                }
            )

        # Initialize components
        self._lifecycle = LifecycleManager()
        self._dispatcher = ToolDispatcher()
        self._tools_handler = ToolsHandler(self._dispatcher)

    def register_plugin(self, plugin: PluginBase) -> None:
        """Register a plugin.

        Args:
            plugin: Plugin to register.
        """
        self._dispatcher.register_plugin(plugin)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools.

        Returns:
            List of tool definitions.
        """
        return self._dispatcher.list_tools()

    def handle_message(self, raw_message: str) -> str | None:
        """Handle an incoming JSON-RPC message.

        Args:
            raw_message: Raw JSON-RPC message string.

        Returns:
            Response string or None for notifications.
        """
        try:
            message = parse_message(raw_message)
        except JsonRpcError as e:
            return format_error(None, e.code, str(e))

        if isinstance(message, JsonRpcNotification):
            return self._handle_notification(message)
        else:
            return self._handle_request(message)

    def _handle_notification(self, notification: JsonRpcNotification) -> None:
        """Handle a notification (no response).

        Args:
            notification: The notification to handle.
        """
        if notification.method == "notifications/initialized":
            try:
                self._lifecycle.handle_initialized()
            except ProtocolError:
                pass  # Ignore protocol errors on notifications
        # Other notifications are silently ignored
        return None

    def _handle_request(self, request: JsonRpcRequest) -> str:
        """Handle a request and return response.

        Args:
            request: The request to handle.

        Returns:
            JSON-RPC response string.
        """
        method = request.method
        params = request.params or {}
        msg_id = request.id

        # Initialize is special - allowed before ready
        if method == "initialize":
            try:
                result = self._lifecycle.handle_initialize(params)
                return format_response(msg_id, result)
            except ProtocolError as e:
                return format_error(msg_id, INTERNAL_ERROR, str(e))

        # All other methods require ready state
        try:
            self._lifecycle.require_ready()
        except ProtocolError as e:
            return format_error(msg_id, INTERNAL_ERROR, str(e))

        # Route to appropriate handler
        if method == "tools/list":
            result = self._tools_handler.handle_list()
            return format_response(msg_id, result.to_dict())

        elif method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = self._tools_handler.handle_call(name, arguments)
            return format_response(msg_id, result.to_dict())

        else:
            return format_error(msg_id, METHOD_NOT_FOUND, f"Unknown method: {method}")
