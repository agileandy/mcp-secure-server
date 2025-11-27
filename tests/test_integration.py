"""Integration tests for the complete MCP server."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.plugins.websearch import WebSearchPlugin
from src.server import MCPServer

FULL_POLICY = """
version: "1.0"
network:
  allowed_ranges:
    - "127.0.0.0/8"
  allowed_endpoints:
    - host: "lite.duckduckgo.com"
      ports: [443]
  blocked_ports: []
  allow_dns: true
  dns_allowlist:
    - "lite.duckduckgo.com"
filesystem:
  allowed_paths:
    - "/tmp/**"
  denied_paths:
    - "**/.ssh/**"
tools:
  timeout: 30
  rate_limits:
    default: 60
    web_search: 20
"""


@pytest.fixture
def policy_file(tmp_path: Path) -> Path:
    """Create a full policy file for integration testing."""
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(FULL_POLICY)
    return policy_path


@pytest.fixture
def server_with_websearch(policy_file: Path) -> MCPServer:
    """Create a server with web search plugin."""
    server = MCPServer(policy_path=policy_file)
    server.register_plugin(WebSearchPlugin())
    return server


@pytest.fixture
def initialized_server(server_with_websearch: MCPServer) -> MCPServer:
    """Create an initialized server with web search."""
    server = server_with_websearch

    # Initialize
    init_request = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "clientInfo": {"name": "integration-test", "version": "1.0"},
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


class TestServerWithWebSearch:
    """Integration tests for server with web search plugin."""

    def test_full_initialization_flow(self, server_with_websearch: MCPServer):
        """Should complete full initialization handshake."""
        server = server_with_websearch

        # Initialize
        init_response = server.handle_message(
            json.dumps(
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
        )

        result = json.loads(init_response)
        assert result["id"] == 1
        assert "result" in result
        assert result["result"]["protocolVersion"] == "2025-11-25"
        assert "tools" in result["result"]["capabilities"]

    def test_tools_list_shows_websearch(self, initialized_server: MCPServer):
        """Should list web_search tool after initialization."""
        response = initialized_server.handle_message(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 10,
                    "method": "tools/list",
                }
            )
        )

        result = json.loads(response)
        assert "result" in result
        tools = result["result"]["tools"]
        assert len(tools) == 1
        assert tools[0]["name"] == "web_search"
        assert "query" in tools[0]["inputSchema"]["properties"]

    @patch("src.plugins.websearch.httpx")
    def test_tools_call_websearch(self, mock_httpx, initialized_server: MCPServer):
        """Should execute web search through the full stack."""
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            "<html><body>"
            '<a class="result__a" href="https://example.com">Example</a>'
            '<a class="result__snippet">Example snippet</a>'
            "</body></html>"
        )
        mock_httpx.get.return_value = mock_response

        response = initialized_server.handle_message(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 20,
                    "method": "tools/call",
                    "params": {
                        "name": "web_search",
                        "arguments": {"query": "test query"},
                    },
                }
            )
        )

        result = json.loads(response)
        assert "result" in result
        assert result["result"]["isError"] is False
        assert "content" in result["result"]
        content_text = result["result"]["content"][0]["text"]
        assert "test query" in content_text.lower()


class TestFullMessageFlow:
    """Tests for complete message sequences."""

    def test_complete_session_flow(self, policy_file: Path):
        """Should handle a complete session from init to tool call."""
        server = MCPServer(policy_path=policy_file)
        server.register_plugin(WebSearchPlugin())

        # Step 1: Initialize
        init_response = server.handle_message(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "clientInfo": {"name": "session-test", "version": "1.0"},
                        "capabilities": {},
                    },
                }
            )
        )
        init_result = json.loads(init_response)
        assert init_result["id"] == 1
        assert "result" in init_result

        # Step 2: Initialized notification
        notif_response = server.handle_message(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                }
            )
        )
        assert notif_response is None  # Notifications don't get responses

        # Step 3: List tools
        list_response = server.handle_message(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                }
            )
        )
        list_result = json.loads(list_response)
        assert list_result["id"] == 2
        assert len(list_result["result"]["tools"]) == 1

        # Step 4: Call a tool (mocked)
        with patch("src.plugins.websearch.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html><body></body></html>"
            mock_httpx.get.return_value = mock_response

            call_response = server.handle_message(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "web_search",
                            "arguments": {"query": "hello world"},
                        },
                    }
                )
            )
            call_result = json.loads(call_response)
            assert call_result["id"] == 3
            assert "result" in call_result

    def test_rejects_tools_before_init(self, server_with_websearch: MCPServer):
        """Should reject tool calls before initialization."""
        response = server_with_websearch.handle_message(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                }
            )
        )

        result = json.loads(response)
        assert "error" in result


class TestErrorHandling:
    """Tests for error scenarios in integration."""

    def test_handles_malformed_json(self, initialized_server: MCPServer):
        """Should return parse error for malformed JSON."""
        response = initialized_server.handle_message("not valid json {")
        result = json.loads(response)
        assert "error" in result

    def test_handles_missing_method(self, initialized_server: MCPServer):
        """Should return error for unknown method."""
        response = initialized_server.handle_message(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "unknown/method",
                }
            )
        )
        result = json.loads(response)
        assert "error" in result
        assert result["error"]["code"] == -32601

    def test_handles_unknown_tool(self, initialized_server: MCPServer):
        """Should return error result for unknown tool."""
        response = initialized_server.handle_message(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "nonexistent_tool",
                        "arguments": {},
                    },
                }
            )
        )
        result = json.loads(response)
        assert "result" in result
        assert result["result"]["isError"] is True

    def test_handles_network_error(self, initialized_server: MCPServer):
        """Should return error result when network fails."""
        # Get the websearch plugin from the tool map and mock its client
        from unittest.mock import MagicMock

        plugin = initialized_server._dispatcher._tool_map.get("web_search")
        if plugin:
            plugin._client.get = MagicMock(side_effect=Exception("Network timeout"))

        response = initialized_server.handle_message(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "web_search",
                        "arguments": {"query": "test"},
                    },
                }
            )
        )
        result = json.loads(response)
        assert "result" in result
        assert result["result"]["isError"] is True
        # Sanitized error message should contain "failed" but not expose internals
        assert "failed" in result["result"]["content"][0]["text"].lower()
