"""Web search plugin using DuckDuckGo.

Provides web search functionality through DuckDuckGo Lite,
which is allowed by the security policy.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

import httpx

from mcp_secure_server.plugins.base import PluginBase, ToolDefinition, ToolResult

# DuckDuckGo Lite endpoint (HTML-based, simpler to parse)
DUCKDUCKGO_LITE_URL = "https://lite.duckduckgo.com/lite/"

# User agent to use for requests
USER_AGENT = "MCP-SecureLocal/1.0 (Web Search Plugin)"


class WebSearchPlugin(PluginBase):
    """Web search plugin using DuckDuckGo.

    Provides a web_search tool that queries DuckDuckGo and
    returns formatted search results.
    """

    def __init__(self) -> None:
        """Initialize the plugin with a reusable HTTP client."""
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=10.0,
        )

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        self._client.close()

    @property
    def name(self) -> str:
        """Return plugin identifier."""
        return "websearch"

    @property
    def version(self) -> str:
        """Return plugin version."""
        return "1.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        """Return available tools.

        Returns:
            List containing the web_search tool definition.
        """
        return [
            ToolDefinition(
                name="web_search",
                description="Search the web using DuckDuckGo. Returns titles, URLs, and snippets.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                            "maxLength": 500,
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 5)",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                        },
                    },
                    "required": ["query"],
                },
            )
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            ToolResult with search results or error.
        """
        if tool_name != "web_search":
            return ToolResult(
                content=[{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                is_error=True,
            )

        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)

        try:
            results = self._search(query, max_results)
            return ToolResult(
                content=[{"type": "text", "text": results}],
                is_error=False,
            )
        except httpx.TimeoutException:
            return ToolResult(
                content=[{"type": "text", "text": "Search timed out. Please try again."}],
                is_error=True,
            )
        except httpx.HTTPStatusError as e:
            return ToolResult(
                content=[
                    {"type": "text", "text": f"Search failed (HTTP {e.response.status_code})"}
                ],
                is_error=True,
            )
        except Exception:
            return ToolResult(
                content=[{"type": "text", "text": "Search failed. Please try again later."}],
                is_error=True,
            )

    def _search(self, query: str, max_results: int) -> str:
        """Perform the actual search.

        Args:
            query: Search query.
            max_results: Maximum results to return.

        Returns:
            Formatted search results as a string.
        """
        # Build the request
        params = {"q": query, "kl": "us-en"}
        url = f"{DUCKDUCKGO_LITE_URL}?{urllib.parse.urlencode(params)}"

        # Make the request using the pooled client
        response = self._client.get(url)
        response.raise_for_status()

        # Parse the results
        results = self._parse_results(response.text, max_results)

        if not results:
            return f"No results found for: {query}"

        # Format the results
        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(
                f"{i}. {result['title']}\n   URL: {result['url']}\n   {result['snippet']}"
            )

        return f"Search results for: {query}\n\n" + "\n\n".join(formatted)

    def _parse_results(self, html: str, max_results: int) -> list[dict[str, str]]:
        """Parse search results from HTML.

        Args:
            html: HTML response from DuckDuckGo.
            max_results: Maximum results to extract.

        Returns:
            List of result dictionaries with title, url, snippet.
        """
        results = []

        # DuckDuckGo Lite uses simple HTML structure
        # Look for result links and snippets
        # Pattern for result links: <a class="result-link" href="...">...</a>
        # or <a class="result__a" href="...">...</a>

        # Simple regex-based parsing (more robust than BeautifulSoup for simple cases)
        # Find all result blocks
        result_pattern = re.compile(
            r'<a[^>]*class="[^"]*result[^"]*"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
            re.IGNORECASE,
        )

        snippet_pattern = re.compile(
            r'<a[^>]*class="[^"]*snippet[^"]*"[^>]*>([^<]+)</a>',
            re.IGNORECASE,
        )

        # Alternative pattern for Lite
        link_pattern = re.compile(
            r'<a[^>]*rel="nofollow"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
            re.IGNORECASE,
        )

        # Find links
        links = result_pattern.findall(html) or link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        # Match links with snippets
        for i, (url, title) in enumerate(links[:max_results]):
            snippet = snippets[i] if i < len(snippets) else ""
            results.append(
                {
                    "title": self._clean_text(title),
                    "url": url,
                    "snippet": self._clean_text(snippet),
                }
            )

        return results

    def _clean_text(self, text: str) -> str:
        """Clean HTML entities and whitespace from text.

        Args:
            text: Raw text to clean.

        Returns:
            Cleaned text.
        """
        import html

        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
