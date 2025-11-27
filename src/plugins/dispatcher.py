"""Tool dispatcher - routes tool calls to the appropriate plugin."""

from __future__ import annotations

from typing import Any

from src.plugins.base import PluginBase, ToolResult


class ToolNotFoundError(Exception):
    """Raised when a tool is not found."""

    pass


class ToolExecutionError(Exception):
    """Raised when a tool fails to execute."""

    pass


class ToolDispatcher:
    """Routes tool calls to registered plugins.

    Maintains a registry of plugins and their tools, dispatching
    calls to the appropriate handler.
    """

    def __init__(self) -> None:
        """Initialize the dispatcher."""
        self._plugins: list[PluginBase] = []
        self._tool_map: dict[str, PluginBase] = {}

    def register_plugin(self, plugin: PluginBase) -> None:
        """Register a plugin and index its tools.

        Args:
            plugin: Plugin instance to register.
        """
        self._plugins.append(plugin)

        # Index tools for fast lookup
        for tool in plugin.get_tools():
            self._tool_map[tool.name] = plugin

    def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools in MCP format.

        Returns:
            List of tool definitions in MCP format.
        """
        tools = []
        for plugin in self._plugins:
            for tool in plugin.get_tools():
                tools.append(tool.to_dict())
        return tools

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Call a tool by name.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool.

        Returns:
            ToolResult from the tool execution.

        Raises:
            ToolNotFoundError: If the tool is not registered.
            ToolExecutionError: If the tool fails to execute.
        """
        plugin = self._tool_map.get(tool_name)
        if plugin is None:
            raise ToolNotFoundError(f"Tool not found: {tool_name}")

        try:
            return plugin.execute(tool_name, arguments)
        except Exception as e:
            raise ToolExecutionError(f"Tool '{tool_name}' execution failed") from e

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        """Get the input schema for a tool.

        Args:
            tool_name: Name of the tool.

        Returns:
            Input schema dict or None if tool not found.
        """
        plugin = self._tool_map.get(tool_name)
        if plugin is None:
            return None

        for tool in plugin.get_tools():
            if tool.name == tool_name:
                return tool.input_schema

        return None

    def cleanup(self) -> None:
        """Clean up all registered plugins.

        Calls cleanup() on each plugin to release resources.
        Called by MCPServer.close() during shutdown.
        """
        for plugin in self._plugins:
            plugin.cleanup()
