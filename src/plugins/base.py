"""Plugin base class and data structures.

Defines the interface that all plugins must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolDefinition:
    """Definition of a tool provided by a plugin."""

    name: str
    description: str
    input_schema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to MCP tool format.

        Returns:
            Dictionary in MCP tools/list format.
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class ToolResult:
    """Result of a tool execution."""

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


class PluginBase(ABC):
    """Abstract base class for all plugins.

    Plugins must implement this interface to provide tools
    to the MCP server.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the plugin identifier."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the plugin version."""
        pass

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        """Return tool definitions provided by this plugin.

        Returns:
            List of ToolDefinition objects.
        """
        pass

    @abstractmethod
    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            ToolResult with content and error status.
        """
        pass
