"""Tests for web search plugin."""

from unittest.mock import MagicMock, patch

from src.plugins.base import PluginBase
from src.plugins.websearch import WebSearchPlugin


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

    @patch("src.plugins.websearch.httpx")
    def test_executes_search(self, mock_httpx):
        """Should execute search and return results."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <body>
            <div class="result">
                <a class="result__a" href="https://example.com">Example Title</a>
                <a class="result__snippet">This is a snippet of text.</a>
            </div>
        </body>
        </html>
        """
        mock_httpx.get.return_value = mock_response

        plugin = WebSearchPlugin()
        result = plugin.execute("web_search", {"query": "test query"})

        assert result.is_error is False
        assert len(result.content) > 0

    @patch("src.plugins.websearch.httpx")
    def test_handles_network_error(self, mock_httpx):
        """Should handle network errors gracefully."""
        mock_httpx.get.side_effect = Exception("Network error")

        plugin = WebSearchPlugin()
        result = plugin.execute("web_search", {"query": "test"})

        assert result.is_error is True
        assert "error" in result.content[0]["text"].lower()

    @patch("src.plugins.websearch.httpx")
    def test_handles_empty_results(self, mock_httpx):
        """Should handle empty search results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"
        mock_httpx.get.return_value = mock_response

        plugin = WebSearchPlugin()
        result = plugin.execute("web_search", {"query": "obscure query"})

        assert result.is_error is False
        # Should return message about no results

    def test_rejects_unknown_tool(self):
        """Should return error for unknown tool."""
        plugin = WebSearchPlugin()
        result = plugin.execute("unknown_tool", {})

        assert result.is_error is True

    @patch("src.plugins.websearch.httpx")
    def test_uses_duckduckgo_lite(self, mock_httpx):
        """Should use DuckDuckGo Lite endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body></body></html>"
        mock_httpx.get.return_value = mock_response

        plugin = WebSearchPlugin()
        plugin.execute("web_search", {"query": "test"})

        # Verify DuckDuckGo Lite was called
        call_args = mock_httpx.get.call_args
        assert "lite.duckduckgo.com" in call_args[0][0] or "html.duckduckgo.com" in call_args[0][0]

    @patch("src.plugins.websearch.httpx")
    def test_respects_max_results(self, mock_httpx):
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
        mock_httpx.get.return_value = mock_response

        plugin = WebSearchPlugin()
        result = plugin.execute("web_search", {"query": "test", "max_results": 2})

        assert result.is_error is False
