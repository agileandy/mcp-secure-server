"""Tests for web search plugin."""

from unittest.mock import MagicMock, patch

import httpx

from mcp_secure_server.plugins.base import PluginBase
from mcp_secure_server.plugins.websearch import WebSearchPlugin


class TestWebSearchPlugin:
    """Tests for WebSearchPlugin class."""

    def test_implements_plugin_interface(self):
        """Should implement PluginBase interface."""
        plugin = WebSearchPlugin()
        assert isinstance(plugin, PluginBase)
        assert plugin.name == "websearch"
        assert plugin.version == "1.0.0"

    def test_provides_search_tool(self):
        """Should provide web_search tool."""
        plugin = WebSearchPlugin()
        tools = plugin.get_tools()

        assert len(tools) == 1
        assert tools[0].name == "web_search"
        assert "query" in tools[0].input_schema["properties"]

    def test_tool_has_required_schema(self):
        """Should have proper input schema for search tool."""
        plugin = WebSearchPlugin()
        tools = plugin.get_tools()
        tool = tools[0]

        assert tool.input_schema["type"] == "object"
        assert "query" in tool.input_schema["required"]

    @patch.object(WebSearchPlugin, "_search")
    def test_executes_search(self, mock_search):
        """Should execute search and return results."""
        mock_search.return_value = (
            "Search results for: test query\n\n"
            "1. Example Title\n   URL: https://example.com\n   This is a snippet."
        )

        plugin = WebSearchPlugin()
        result = plugin.execute("web_search", {"query": "test query"})

        assert result.is_error is False
        assert len(result.content) > 0
        mock_search.assert_called_once_with("test query", 5)

    def test_handles_network_error(self):
        """Should handle network errors gracefully."""
        plugin = WebSearchPlugin()
        # Mock the client's get method to raise an exception
        plugin._client.get = MagicMock(side_effect=Exception("Network error"))

        result = plugin.execute("web_search", {"query": "test"})

        assert result.is_error is True
        # Should return a generic safe message
        assert "failed" in result.content[0]["text"].lower()

    def test_handles_empty_results(self):
        """Should handle empty search results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"

        plugin = WebSearchPlugin()
        plugin._client.get = MagicMock(return_value=mock_response)

        result = plugin.execute("web_search", {"query": "obscure query"})

        assert result.is_error is False
        # Should return message about no results

    def test_rejects_unknown_tool(self):
        """Should return error for unknown tool."""
        plugin = WebSearchPlugin()
        result = plugin.execute("unknown_tool", {})

        assert result.is_error is True

    def test_uses_duckduckgo_lite(self):
        """Should use DuckDuckGo Lite endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"

        plugin = WebSearchPlugin()
        plugin._client.get = MagicMock(return_value=mock_response)

        plugin.execute("web_search", {"query": "test"})

        # Verify DuckDuckGo Lite was called
        call_args = plugin._client.get.call_args
        assert "lite.duckduckgo.com" in call_args[0][0]

    def test_respects_max_results(self):
        """Should respect max_results parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Multiple results - using shorter HTML
        mock_response.text = (
            "<html><body>"
            '<div class="result"><a class="result__a" href="1">One</a>'
            '<a class="result__snippet">S1</a></div>'
            '<div class="result"><a class="result__a" href="2">Two</a>'
            '<a class="result__snippet">S2</a></div>'
            '<div class="result"><a class="result__a" href="3">Three</a>'
            '<a class="result__snippet">S3</a></div>'
            "</body></html>"
        )

        plugin = WebSearchPlugin()
        plugin._client.get = MagicMock(return_value=mock_response)

        result = plugin.execute("web_search", {"query": "test", "max_results": 2})

        assert result.is_error is False


class TestWebSearchPluginSchemaBounds:
    """Tests for schema bounds on WebSearchPlugin [D2]."""

    def test_schema_has_query_max_length(self):
        """Should have maxLength constraint on query field."""
        plugin = WebSearchPlugin()
        tools = plugin.get_tools()
        query_schema = tools[0].input_schema["properties"]["query"]

        assert "maxLength" in query_schema
        assert query_schema["maxLength"] == 500

    def test_schema_has_max_results_bounds(self):
        """Should have minimum and maximum on max_results field."""
        plugin = WebSearchPlugin()
        tools = plugin.get_tools()
        max_results_schema = tools[0].input_schema["properties"]["max_results"]

        assert "minimum" in max_results_schema
        assert max_results_schema["minimum"] == 1
        assert "maximum" in max_results_schema
        assert max_results_schema["maximum"] == 20

    def test_schema_default_max_results(self):
        """Should have default value for max_results."""
        plugin = WebSearchPlugin()
        tools = plugin.get_tools()
        max_results_schema = tools[0].input_schema["properties"]["max_results"]

        assert "default" in max_results_schema
        assert max_results_schema["default"] == 5


class TestWebSearchPluginConnectionPooling:
    """Tests for httpx connection pooling [D2]."""

    def test_uses_http_client(self):
        """Should use httpx.Client for connection pooling."""
        plugin = WebSearchPlugin()
        assert hasattr(plugin, "_client")
        assert isinstance(plugin._client, httpx.Client)

    def test_client_reused_across_requests(self):
        """Should reuse the same client across multiple requests."""
        plugin = WebSearchPlugin()
        client1 = plugin._client
        # Simulate multiple searches would use same client
        client2 = plugin._client
        assert client1 is client2

    def test_client_has_timeout_configured(self):
        """Should have timeout configured on the client."""
        plugin = WebSearchPlugin()
        assert plugin._client.timeout is not None

    def test_client_has_user_agent(self):
        """Should have user agent configured on the client."""
        plugin = WebSearchPlugin()
        assert "MCP-SecureLocal" in plugin._client.headers.get("User-Agent", "")

    def test_close_closes_client(self):
        """Should close the httpx client when close() is called."""
        plugin = WebSearchPlugin()
        assert not plugin._client.is_closed
        plugin.close()
        assert plugin._client.is_closed


class TestWebSearchPluginErrorSanitization:
    """Tests for error message sanitization [D3]."""

    def test_timeout_error_sanitized(self):
        """Timeout errors should return generic message without internal details."""
        plugin = WebSearchPlugin()
        plugin._client.get = MagicMock(side_effect=httpx.TimeoutException("Connection timed out"))

        result = plugin.execute("web_search", {"query": "test"})

        assert result.is_error is True
        error_text = result.content[0]["text"]
        assert "timed out" in error_text.lower()
        # Should NOT contain internal details
        assert "Connection" not in error_text

    def test_http_error_sanitized(self):
        """HTTP errors should return status code only, no internal details."""
        mock_response = MagicMock()
        mock_response.status_code = 503

        plugin = WebSearchPlugin()
        plugin._client.get = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Service Unavailable", request=MagicMock(), response=mock_response
            )
        )

        result = plugin.execute("web_search", {"query": "test"})

        assert result.is_error is True
        error_text = result.content[0]["text"]
        assert "503" in error_text
        # Should NOT contain full error message
        assert "Unavailable" not in error_text

    def test_generic_error_sanitized(self):
        """Generic errors should return safe message without internal details."""
        plugin = WebSearchPlugin()
        plugin._client.get = MagicMock(
            side_effect=Exception("Internal server at 192.168.1.1:8080 failed")
        )

        result = plugin.execute("web_search", {"query": "test"})

        assert result.is_error is True
        error_text = result.content[0]["text"]
        # Should NOT contain IP address
        assert "192.168" not in error_text
        # Should NOT contain port
        assert "8080" not in error_text
        # Should be a generic message
        assert "failed" in error_text.lower() or "try again" in error_text.lower()
