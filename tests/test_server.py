"""Tests for main server entry point."""

import json
from pathlib import Path

import pytest

from src.plugins.base import PluginBase, ToolDefinition, ToolResult
from src.server import MCPServer

MINIMAL_POLICY = """
version: "1.0"
network:
  mode: deny_all
  allowed_endpoints: []
filesystem:
  allowed_paths: []
  denied_paths: []
tools:
  allowed: []
  timeout: 30
  rate_limits: {}
"""


class MockPlugin(PluginBase):
    """Mock plugin for testing."""

    @property
    def name(self) -> str:
        return "mock"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="echo",
                description="Echoes input",
                input_schema={
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                    "required": ["message"],
                },
            )
        ]

    def execute(self, tool_name: str, arguments: dict) -> ToolResult:
        if tool_name == "echo":
            return ToolResult(content=[{"type": "text", "text": arguments["message"]}])
        return ToolResult(
            content=[{"type": "text", "text": "Unknown tool"}],
            is_error=True,
        )


@pytest.fixture
def policy_file(tmp_path: Path) -> Path:
    """Create a minimal policy file for testing."""
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(MINIMAL_POLICY)
    return policy_path


@pytest.fixture
def server(policy_file: Path) -> MCPServer:
    """Create a server with minimal policy."""
    return MCPServer(policy_path=policy_file)


@pytest.fixture
def initialized_server(server: MCPServer) -> MCPServer:
    """Create an initialized server."""
    init_request = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "clientInfo": {"name": "test", "version": "1.0"},
                "capabilities": {},
            },
        }
    )
    server.handle_message(init_request)
    server.handle_message(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
        )
    )
    return server


class TestMCPServer:
    """Tests for MCPServer class."""

    def test_creates_server(self, server: MCPServer):
        """Should create server with default config."""
        assert server is not None

    def test_registers_plugin(self, server: MCPServer):
        """Should register plugins."""
        server.register_plugin(MockPlugin())

        tools = server.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "echo"

    def test_handles_initialize(self, server: MCPServer):
        """Should handle initialize request."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "clientInfo": {"name": "test", "version": "1.0"},
                "capabilities": {},
            },
        }

        response = server.handle_message(json.dumps(request))
        result = json.loads(response)

        assert result["id"] == 1
        assert "result" in result
        assert result["result"]["protocolVersion"] == "2025-11-25"

    def test_handles_tools_list(self, initialized_server: MCPServer):
        """Should handle tools/list after initialization."""
        initialized_server.register_plugin(MockPlugin())

        list_request = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
            }
        )
        response = initialized_server.handle_message(list_request)
        result = json.loads(response)

        assert result["id"] == 2
        assert "result" in result
        assert "tools" in result["result"]
        assert len(result["result"]["tools"]) == 1

    def test_handles_tools_call(self, initialized_server: MCPServer):
        """Should handle tools/call after initialization."""
        initialized_server.register_plugin(MockPlugin())

        call_request = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "echo",
                    "arguments": {"message": "Hello World"},
                },
            }
        )
        response = initialized_server.handle_message(call_request)
        result = json.loads(response)

        assert result["id"] == 3
        assert "result" in result
        assert result["result"]["content"][0]["text"] == "Hello World"

    def test_rejects_request_before_init(self, server: MCPServer):
        """Should reject requests before initialization."""
        request = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
            }
        )
        response = server.handle_message(request)
        result = json.loads(response)

        assert "error" in result

    def test_handles_unknown_method(self, initialized_server: MCPServer):
        """Should return error for unknown methods."""
        request = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "unknown/method",
            }
        )
        response = initialized_server.handle_message(request)
        result = json.loads(response)

        assert "error" in result
        assert result["error"]["code"] == -32601  # Method not found

    def test_creates_server_without_policy(self):
        """Should create server with no policy path."""
        server = MCPServer()
        assert server is not None

    def test_handles_invalid_json(self, server: MCPServer):
        """Should return error for invalid JSON."""
        response = server.handle_message("not valid json")
        result = json.loads(response)

        assert "error" in result

    def test_handles_initialized_notification_before_init(self, server: MCPServer):
        """Should ignore initialized notification before initialize."""
        notification = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
        )
        # Should not raise, just ignore
        result = server.handle_message(notification)
        assert result is None

    def test_handles_other_notifications(self, initialized_server: MCPServer):
        """Should silently ignore unknown notifications."""
        notification = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "notifications/unknown",
            }
        )
        result = initialized_server.handle_message(notification)
        assert result is None
