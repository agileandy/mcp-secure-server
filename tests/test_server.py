"""Tests for main server entry point."""

import json
from pathlib import Path

import pytest

from mcp_secure_server.plugins.base import PluginBase, ToolDefinition, ToolResult
from mcp_secure_server.server import MCPServer

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
                "protocolVersion": "2024-11-05",
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
        # 2 discovery tools auto-registered + 1 mock plugin tool
        assert len(tools) == 3
        tool_names = {t["name"] for t in tools}
        assert "echo" in tool_names

    def test_handles_initialize(self, server: MCPServer):
        """Should handle initialize request."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test", "version": "1.0"},
                "capabilities": {},
            },
        }

        response = server.handle_message(json.dumps(request))
        result = json.loads(response)

        assert result["id"] == 1
        assert "result" in result
        assert result["result"]["protocolVersion"] == "2024-11-05"

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
        # 2 discovery tools auto-registered + 1 mock plugin tool
        assert len(result["result"]["tools"]) == 3

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


RATE_LIMITED_POLICY = """
version: "1.0"
network:
  mode: deny_all
  allowed_endpoints: []
filesystem:
  allowed_paths: []
  denied_paths: []
tools:
  allowed: ["echo"]
  timeout: 30
  rate_limits:
    echo: 2
"""


class TestMCPServerSecurityIntegration:
    """Tests for SecurityEngine integration [D1]."""

    @pytest.fixture
    def rate_limited_policy_file(self, tmp_path: Path) -> Path:
        """Create a policy with rate limiting."""
        policy_path = tmp_path / "policy.yaml"
        policy_path.write_text(RATE_LIMITED_POLICY)
        return policy_path

    @pytest.fixture
    def rate_limited_server(self, rate_limited_policy_file: Path) -> MCPServer:
        """Create a server with rate limiting enabled."""
        server = MCPServer(policy_path=rate_limited_policy_file)
        server.register_plugin(MockPlugin())
        # Initialize the server
        init_request = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "test", "version": "1.0"},
                    "capabilities": {},
                },
            }
        )
        server.handle_message(init_request)
        server.handle_message(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        return server

    def test_rate_limiting_enforced(self, rate_limited_server: MCPServer):
        """Should enforce rate limits on tool calls."""
        call_request = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "echo",
                    "arguments": {"message": "test"},
                },
            }
        )

        # First two calls should succeed (rate limit is 2)
        response1 = rate_limited_server.handle_message(call_request)
        result1 = json.loads(response1)
        assert "error" not in result1

        response2 = rate_limited_server.handle_message(call_request)
        result2 = json.loads(response2)
        assert "error" not in result2

        # Third call should be rate limited
        response3 = rate_limited_server.handle_message(call_request)
        result3 = json.loads(response3)
        assert "error" in result3
        assert "rate" in result3["error"]["message"].lower()

    def test_uses_context_manager(self, rate_limited_policy_file: Path):
        """Should support context manager for cleanup."""
        with MCPServer(policy_path=rate_limited_policy_file) as server:
            assert server is not None
        # Should not raise after exiting context


class TestServerPluginCleanup:
    """Tests for plugin cleanup during server shutdown [A5]."""

    def test_close_calls_plugin_cleanup(self, tmp_path: Path):
        """Server.close() should call cleanup on all registered plugins."""
        # Create policy file
        policy = tmp_path / "policy.yaml"
        policy.write_text(MINIMAL_POLICY)

        # Create a mock plugin that tracks cleanup calls
        cleanup_called = []

        class CleanupTrackingPlugin(PluginBase):
            @property
            def name(self) -> str:
                return "cleanup_tracker"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return []

            def execute(self, tool_name: str, arguments: dict) -> ToolResult:
                return ToolResult(content=[], is_error=True)

            def cleanup(self) -> None:
                cleanup_called.append(True)

        server = MCPServer(policy_path=policy)
        server.register_plugin(CleanupTrackingPlugin())

        # Close should trigger cleanup
        server.close()

        assert len(cleanup_called) == 1

    def test_close_calls_cleanup_on_multiple_plugins(self, tmp_path: Path):
        """Server.close() should call cleanup on all plugins."""
        policy = tmp_path / "policy.yaml"
        policy.write_text(MINIMAL_POLICY)

        cleanup_log = []

        class Plugin1(PluginBase):
            @property
            def name(self) -> str:
                return "plugin1"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return []

            def execute(self, tool_name: str, arguments: dict) -> ToolResult:
                return ToolResult(content=[], is_error=True)

            def cleanup(self) -> None:
                cleanup_log.append("plugin1")

        class Plugin2(PluginBase):
            @property
            def name(self) -> str:
                return "plugin2"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return []

            def execute(self, tool_name: str, arguments: dict) -> ToolResult:
                return ToolResult(content=[], is_error=True)

            def cleanup(self) -> None:
                cleanup_log.append("plugin2")

        server = MCPServer(policy_path=policy)
        server.register_plugin(Plugin1())
        server.register_plugin(Plugin2())

        server.close()

        assert "plugin1" in cleanup_log
        assert "plugin2" in cleanup_log

    def test_plugins_without_cleanup_are_skipped(self, tmp_path: Path):
        """Plugins that don't override cleanup should not cause errors."""
        policy = tmp_path / "policy.yaml"
        policy.write_text(MINIMAL_POLICY)

        # Use MockPlugin which doesn't define cleanup
        server = MCPServer(policy_path=policy)
        server.register_plugin(MockPlugin())

        # Should not raise
        server.close()
