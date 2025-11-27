"""MCP tools/list and tools/call handlers.

Handles tool-related MCP requests, routing them through the plugin dispatcher.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.plugins.dispatcher import ToolDispatcher, ToolExecutionError, ToolNotFoundError


@dataclass
class ToolsListResult:
    """Result of tools/list request."""

    tools: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Convert to MCP result format.

        Returns:
            Dictionary in MCP tools/list result format.
        """
        return {"tools": self.tools}


@dataclass
class ToolsCallResult:
    """Result of tools/call request."""

    content: list[dict[str, Any]]
    is_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to MCP result format.

        Returns:
            Dictionary in MCP tools/call result format.
        """
        return {
            "content": self.content,
            "isError": self.is_error,
        }


class ToolsHandler:
    """Handles tools/list and tools/call MCP requests.

    Routes requests through the plugin dispatcher and formats
    results according to MCP specification.
    """

    def __init__(self, dispatcher: ToolDispatcher) -> None:
        """Initialize the handler.

        Args:
            dispatcher: Tool dispatcher for routing calls.
        """
        self._dispatcher = dispatcher

    def handle_list(self) -> ToolsListResult:
        """Handle tools/list request.

        Returns:
            ToolsListResult with all available tools.
        """
        tools = self._dispatcher.list_tools()
        return ToolsListResult(tools=tools)

    def handle_call(self, name: str, arguments: dict[str, Any]) -> ToolsCallResult:
        """Handle tools/call request.

        Args:
            name: Name of the tool to call.
            arguments: Tool arguments.

        Returns:
            ToolsCallResult with execution result.
        """
        try:
            result = self._dispatcher.call_tool(name, arguments)
            return ToolsCallResult(
                content=result.content,
                is_error=result.is_error,
            )
        except ToolNotFoundError:
            return ToolsCallResult(
                content=[{"type": "text", "text": f"Tool not found: {name}"}],
                is_error=True,
            )
        except ToolExecutionError as e:
            return ToolsCallResult(
                content=[{"type": "text", "text": f"Tool execution failed: {e}"}],
                is_error=True,
            )
