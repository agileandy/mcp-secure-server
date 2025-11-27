"""Plugin system for MCP tools."""

from src.plugins.base import PluginBase, ToolDefinition, ToolResult
from src.plugins.discovery import ToolDiscoveryPlugin
from src.plugins.dispatcher import ToolDispatcher, ToolExecutionError, ToolNotFoundError
from src.plugins.loader import PluginLoader, PluginLoadError

__all__ = [
    "PluginBase",
    "PluginLoadError",
    "PluginLoader",
    "ToolDefinition",
    "ToolDiscoveryPlugin",
    "ToolDispatcher",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolResult",
]
