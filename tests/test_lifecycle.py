"""Tests for STDIO transport and MCP lifecycle management."""

import io

import pytest

from mcp_secure_server.protocol.lifecycle import (
    MCP_PROTOCOL_VERSION,
    LifecycleManager,
    LifecycleState,
    ProtocolError,
)
from mcp_secure_server.protocol.transport import StdioTransport


class TestStdioTransport:
    """Tests for STDIO transport layer."""

    def test_reads_line_from_stdin(self):
        """Should read a line from stdin."""
        mock_stdin = io.StringIO('{"jsonrpc":"2.0","id":1,"method":"test"}\n')
        transport = StdioTransport(stdin=mock_stdin, stdout=io.StringIO())

        line = transport.read_message()
        assert line == '{"jsonrpc":"2.0","id":1,"method":"test"}'

    def test_writes_line_to_stdout(self):
        """Should write a line to stdout with newline."""
        mock_stdout = io.StringIO()
        transport = StdioTransport(stdin=io.StringIO(), stdout=mock_stdout)

        transport.write_message('{"jsonrpc":"2.0","id":1,"result":{}}')

        mock_stdout.seek(0)
        assert mock_stdout.read() == '{"jsonrpc":"2.0","id":1,"result":{}}\n'

    def test_returns_none_on_eof(self):
        """Should return None when stdin is exhausted."""
        mock_stdin = io.StringIO("")
        transport = StdioTransport(stdin=mock_stdin, stdout=io.StringIO())

        line = transport.read_message()
        assert line is None

    def test_strips_whitespace(self):
        """Should strip leading/trailing whitespace from messages."""
        mock_stdin = io.StringIO('  {"test": true}  \n')
        transport = StdioTransport(stdin=mock_stdin, stdout=io.StringIO())

        line = transport.read_message()
        assert line == '{"test": true}'

    def test_skips_empty_lines(self):
        """Should skip empty lines."""
        mock_stdin = io.StringIO('\n\n{"valid": true}\n\n')
        transport = StdioTransport(stdin=mock_stdin, stdout=io.StringIO())

        line = transport.read_message()
        assert line == '{"valid": true}'

    def test_logs_to_stderr(self):
        """Should write logs to stderr."""
        mock_stderr = io.StringIO()
        transport = StdioTransport(
            stdin=io.StringIO(),
            stdout=io.StringIO(),
            stderr=mock_stderr,
        )

        transport.log("Test message")

        mock_stderr.seek(0)
        assert "Test message" in mock_stderr.read()

    def test_returns_none_on_read_exception(self):
        """Should return None when read raises an exception."""
        from unittest.mock import MagicMock

        mock_stdin = MagicMock()
        mock_stdin.readline.side_effect = OSError("Pipe broken")

        transport = StdioTransport(stdin=mock_stdin, stdout=io.StringIO())

        # Should return None, not raise
        result = transport.read_message()
        assert result is None


class TestLifecycleManager:
    """Tests for MCP lifecycle management."""

    def test_starts_in_uninitialized_state(self):
        """Should start in UNINITIALIZED state."""
        manager = LifecycleManager()
        assert manager.state == LifecycleState.UNINITIALIZED

    def test_handles_initialize_request(self):
        """Should handle initialize request correctly."""
        manager = LifecycleManager()

        result = manager.handle_initialize(
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
            }
        )

        assert manager.state == LifecycleState.INITIALIZING
        assert result["protocolVersion"] == MCP_PROTOCOL_VERSION
        assert "capabilities" in result
        assert "serverInfo" in result

    def test_rejects_initialize_when_already_initialized(self):
        """Should reject initialize if already initialized."""
        manager = LifecycleManager()
        manager.handle_initialize(
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            }
        )
        manager.handle_initialized()

        with pytest.raises(ProtocolError, match="already initialized"):
            manager.handle_initialize(
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"},
                }
            )

    def test_handles_initialized_notification(self):
        """Should transition to READY on initialized notification."""
        manager = LifecycleManager()
        manager.handle_initialize(
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            }
        )

        manager.handle_initialized()
        assert manager.state == LifecycleState.READY

    def test_rejects_initialized_before_initialize(self):
        """Should reject initialized if initialize not called."""
        manager = LifecycleManager()

        with pytest.raises(ProtocolError, match="not initializing"):
            manager.handle_initialized()

    def test_accepts_any_protocol_version(self):
        """Should accept any protocol version and echo it back."""
        manager = LifecycleManager()

        result = manager.handle_initialize(
            {
                "protocolVersion": "1999-01-01",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            }
        )

        assert result["protocolVersion"] == "1999-01-01"

    def test_stores_client_info(self):
        """Should store client info from initialize."""
        manager = LifecycleManager()
        manager.handle_initialize(
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "2.0"},
            }
        )

        assert manager.client_info == {"name": "test-client", "version": "2.0"}
        assert manager.client_capabilities == {"tools": {}}

    def test_connected_client_property(self):
        """Should expose client info via connected_client property."""
        manager = LifecycleManager()
        assert manager.connected_client is None

        manager.handle_initialize(
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "my-client", "version": "3.0"},
            }
        )

        assert manager.connected_client == {"name": "my-client", "version": "3.0"}

    def test_client_caps_property(self):
        """Should expose client capabilities via client_caps property."""
        manager = LifecycleManager()
        assert manager.client_caps == {}

        manager.handle_initialize(
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": True}},
                "clientInfo": {"name": "test", "version": "1.0"},
            }
        )

        assert manager.client_caps == {"tools": {"listChanged": True}}

    def test_returns_server_capabilities(self):
        """Should return server capabilities in initialize response."""
        manager = LifecycleManager(
            server_info={"name": "test-server", "version": "1.0"},
            capabilities={"tools": {"listChanged": True}},
        )

        result = manager.handle_initialize(
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            }
        )

        assert result["serverInfo"]["name"] == "test-server"
        assert result["capabilities"]["tools"]["listChanged"] is True

    def test_is_ready_property(self):
        """Should report ready state correctly."""
        manager = LifecycleManager()
        assert manager.is_ready is False

        manager.handle_initialize(
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            }
        )
        assert manager.is_ready is False

        manager.handle_initialized()
        assert manager.is_ready is True

    def test_requires_ready_for_operations(self):
        """Should reject operations before ready."""
        manager = LifecycleManager()

        with pytest.raises(ProtocolError, match="not ready"):
            manager.require_ready()

        manager.handle_initialize(
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            }
        )
        manager.handle_initialized()

        # Should not raise
        manager.require_ready()


class TestLifecycleShutdown:
    """Tests for shutdown handling."""

    def test_handles_shutdown(self):
        """Should transition to SHUTDOWN state."""
        manager = LifecycleManager()
        manager.handle_initialize(
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            }
        )
        manager.handle_initialized()

        manager.handle_shutdown()
        assert manager.state == LifecycleState.SHUTDOWN

    def test_rejects_operations_after_shutdown(self):
        """Should reject operations after shutdown."""
        manager = LifecycleManager()
        manager.handle_initialize(
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            }
        )
        manager.handle_initialized()
        manager.handle_shutdown()

        with pytest.raises(ProtocolError, match="shutdown"):
            manager.require_ready()
