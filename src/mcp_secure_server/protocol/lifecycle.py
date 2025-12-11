"""MCP lifecycle management.

Handles the initialize/initialized handshake and tracks connection state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Supported MCP protocol versions (newest first)
SUPPORTED_PROTOCOL_VERSIONS = ["2024-11-05", "2025-03-26"]
# Default version to advertise
MCP_PROTOCOL_VERSION = "2024-11-05"


class LifecycleState(Enum):
    """MCP connection lifecycle states."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    SHUTDOWN = "shutdown"


class ProtocolError(Exception):
    """Raised when protocol constraints are violated."""

    pass


@dataclass
class LifecycleManager:
    """Manages MCP connection lifecycle.

    Handles the initialization handshake and tracks connection state
    per MCP specification.
    """

    server_info: dict[str, str] = field(
        default_factory=lambda: {"name": "mcp-secure-local", "version": "1.0.0"}
    )
    capabilities: dict[str, Any] = field(default_factory=lambda: {"tools": {"listChanged": True}})
    state: LifecycleState = LifecycleState.UNINITIALIZED
    client_info: dict[str, str] | None = None
    client_capabilities: dict[str, Any] | None = None

    @property
    def is_ready(self) -> bool:
        """Check if the connection is ready for operations."""
        return self.state == LifecycleState.READY

    @property
    def connected_client(self) -> dict[str, str] | None:
        """Get information about the connected client.

        Returns:
            Client info dict with 'name' and 'version', or None if not initialized.
        """
        return self.client_info

    @property
    def client_caps(self) -> dict[str, Any]:
        """Get the connected client's capabilities.

        Returns:
            Client capabilities dict, or empty dict if not initialized.
        """
        return self.client_capabilities or {}

    def require_ready(self) -> None:
        """Assert that the connection is ready.

        Raises:
            ProtocolError: If not ready for operations.
        """
        if self.state == LifecycleState.SHUTDOWN:
            raise ProtocolError("Connection is shutdown")
        if self.state != LifecycleState.READY:
            raise ProtocolError("Connection is not ready")

    def handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request.

        Args:
            params: Initialize request parameters.

        Returns:
            Initialize response result.

        Raises:
            ProtocolError: If already initialized or version unsupported.
        """
        if self.state not in (LifecycleState.UNINITIALIZED,):
            raise ProtocolError("Server already initialized")

        # Accept any protocol version the client sends
        requested_version = params.get("protocolVersion", "2024-11-05")

        # Use the client's requested version for the response
        negotiated_version = requested_version

        # Store client info
        self.client_info = params.get("clientInfo")
        self.client_capabilities = params.get("capabilities", {})

        # Transition state
        self.state = LifecycleState.INITIALIZING

        # Return server capabilities
        return {
            "protocolVersion": negotiated_version,
            "capabilities": self.capabilities,
            "serverInfo": self.server_info,
        }

    def handle_initialized(self) -> None:
        """Handle initialized notification.

        Raises:
            ProtocolError: If not in initializing state.
        """
        if self.state != LifecycleState.INITIALIZING:
            raise ProtocolError("Server not initializing")

        self.state = LifecycleState.READY

    def handle_shutdown(self) -> None:
        """Handle shutdown request."""
        self.state = LifecycleState.SHUTDOWN
