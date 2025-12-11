"""MCP Server - main entry point.

Integrates all components into a complete MCP server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp_secure_server.plugins.base import PluginBase
from mcp_secure_server.plugins.discovery import ToolDiscoveryPlugin
from mcp_secure_server.plugins.dispatcher import ToolDispatcher
from mcp_secure_server.protocol.jsonrpc import (
    INTERNAL_ERROR,
    METHOD_NOT_FOUND,
    JsonRpcError,
    JsonRpcNotification,
    JsonRpcRequest,
    format_error,
    format_response,
    parse_message,
)
from mcp_secure_server.protocol.lifecycle import LifecycleManager, ProtocolError
from mcp_secure_server.protocol.tools import ToolsHandler
from mcp_secure_server.security.engine import RateLimitExceeded, SecurityEngine
from mcp_secure_server.security.policy import SecurityPolicy, load_policy


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
        self._security_engine = SecurityEngine(self._policy)

        # Auto-register discovery plugin (provides search_tools, list_categories)
        self._dispatcher.register_plugin(ToolDiscoveryPlugin(self._dispatcher))

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

            # Check rate limit before execution
            try:
                self._security_engine.check_rate_limit(name)
            except RateLimitExceeded:
                return format_error(msg_id, INTERNAL_ERROR, f"Rate limit exceeded for tool: {name}")

            result = self._tools_handler.handle_call(name, arguments)
            return format_response(msg_id, result.to_dict())

        else:
            return format_error(msg_id, METHOD_NOT_FOUND, f"Unknown method: {method}")

    def close(self) -> None:
        """Close the server and clean up resources."""
        self._dispatcher.cleanup()
        self._security_engine.close()

    def __enter__(self) -> MCPServer:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
