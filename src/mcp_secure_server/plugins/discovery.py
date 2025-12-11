"""Tool discovery plugin for progressive disclosure.

Provides tools for agents to discover available tools on-demand,
reducing context window usage by loading only what's needed.

This implements the "Code Mode" progressive disclosure pattern
described in Anthropic's MCP efficiency guidelines.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal

from mcp_secure_server.plugins.base import PluginBase, ToolDefinition, ToolResult

if TYPE_CHECKING:
    from mcp_secure_server.plugins.dispatcher import ToolDispatcher


class ToolDiscoveryPlugin(PluginBase):
    """Plugin for discovering available tools.

    Provides progressive disclosure of tool definitions, allowing
    agents to search and browse tools without loading all definitions
    upfront into context.

    Tools:
        - search_tools: Search for tools by keyword or category
        - list_categories: List available plugin categories
    """

    def __init__(self, dispatcher: ToolDispatcher) -> None:
        """Initialize with reference to the tool dispatcher.

        Args:
            dispatcher: The ToolDispatcher containing registered plugins.
        """
        self._dispatcher = dispatcher

    @property
    def name(self) -> str:
        """Return plugin identifier."""
        return "discovery"

    @property
    def version(self) -> str:
        """Return plugin version."""
        return "1.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        """Return available tools.

        Returns:
            List containing search_tools and list_categories definitions.
        """
        return [
            ToolDefinition(
                name="search_tools",
                description=(
                    "Search for available tools by keyword or category. "
                    "Use detail_level to control how much information is returned: "
                    "'name' for just tool names, 'summary' for names and descriptions, "
                    "'full' for complete definitions including input schemas."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Keyword to search for in tool names and descriptions",
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by plugin category (e.g., 'bugtracker')",
                        },
                        "detail_level": {
                            "type": "string",
                            "enum": ["name", "summary", "full"],
                            "description": "Level of detail to return (default: 'summary')",
                            "default": "summary",
                        },
                    },
                },
            ),
            ToolDefinition(
                name="list_categories",
                description=(
                    "List all available tool categories (plugins) with their tool counts. "
                    "Use this to discover what capabilities are available before searching."
                ),
                input_schema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            ToolResult with search/list results or error.
        """
        if tool_name == "search_tools":
            return self._search_tools(arguments)
        elif tool_name == "list_categories":
            return self._list_categories()
        else:
            return ToolResult(
                content=[{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                is_error=True,
            )

    def _search_tools(self, arguments: dict[str, Any]) -> ToolResult:
        """Search for tools by query and/or category.

        Args:
            arguments: Search parameters (query, category, detail_level).

        Returns:
            ToolResult with matching tools.
        """
        query = arguments.get("query", "").lower()
        category = arguments.get("category", "").lower()
        detail_level: Literal["name", "summary", "full"] = arguments.get("detail_level", "summary")

        # Collect all tools with their plugin info
        matching_tools = []
        for plugin in self._dispatcher._plugins:
            plugin_name = plugin.name.lower()

            # Filter by category if specified
            if category and plugin_name != category:
                continue

            for tool in plugin.get_tools():
                # Filter by query if specified
                if query:
                    name_match = query in tool.name.lower()
                    desc_match = query in tool.description.lower()
                    if not (name_match or desc_match):
                        continue

                matching_tools.append(tool)

        # Format output based on detail level
        if detail_level == "name":
            result = [tool.name for tool in matching_tools]
        elif detail_level == "summary":
            result = [
                {"name": tool.name, "description": tool.description} for tool in matching_tools
            ]
        else:  # full
            result = [tool.to_dict() for tool in matching_tools]

        return ToolResult(
            content=[{"type": "text", "text": json.dumps(result, indent=2)}],
            is_error=False,
        )

    def _list_categories(self) -> ToolResult:
        """List all plugin categories with tool counts.

        Returns:
            ToolResult with category information.
        """
        categories = []
        for plugin in self._dispatcher._plugins:
            tools = plugin.get_tools()
            categories.append(
                {
                    "category": plugin.name,
                    "version": plugin.version,
                    "tool_count": len(tools),
                    "tools": [tool.name for tool in tools],
                }
            )

        return ToolResult(
            content=[{"type": "text", "text": json.dumps(categories, indent=2)}],
            is_error=False,
        )
