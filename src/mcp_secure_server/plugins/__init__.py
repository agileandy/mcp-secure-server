"""Plugin system for MCP tools."""

from mcp_secure_server.plugins.base import PluginBase, ToolDefinition, ToolResult
from mcp_secure_server.plugins.discovery import ToolDiscoveryPlugin
from mcp_secure_server.plugins.dispatcher import ToolDispatcher, ToolExecutionError, ToolNotFoundError
from mcp_secure_server.plugins.loader import PluginLoader, PluginLoadError

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
