"""Plugin base class and data structures.

Defines the interface that all plugins must implement.

================================================================================
DEVELOPER GUIDE: Adding a New Plugin
================================================================================

This module defines the contract that all MCP tool plugins must follow. To add
a new capability (e.g., database queries, file operations, API integrations),
you need to:

1. CREATE YOUR PLUGIN FILE
   --------------------------
   Create a new file in src/plugins/ (e.g., src/plugins/dbquery.py)

   Example for a database query plugin:

   ```python
   from src.plugins.base import PluginBase, ToolDefinition, ToolResult

   class DBQueryPlugin(PluginBase):
       def __init__(self, connection_string: str):
           self._conn_string = connection_string
           self._connection = None

       @property
       def name(self) -> str:
           return "dbquery"

       @property
       def version(self) -> str:
           return "1.0.0"

       def get_tools(self) -> list[ToolDefinition]:
           return [
               ToolDefinition(
                   name="query_database",
                   description="Execute a read-only SQL query against the database",
                   input_schema={
                       "type": "object",
                       "properties": {
                           "query": {
                               "type": "string",
                               "description": "SQL SELECT query to execute"
                           },
                           "limit": {
                               "type": "integer",
                               "description": "Max rows to return (default: 100)",
                               "default": 100
                           }
                       },
                       "required": ["query"]
                   },
               )
           ]

       def execute(self, tool_name: str, arguments: dict) -> ToolResult:
           if tool_name != "query_database":
               return ToolResult(
                   content=[{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                   is_error=True,
               )

           query = arguments.get("query", "")
           limit = arguments.get("limit", 100)

           # SECURITY: Validate query is read-only (defense in depth)
           # The security policy should also block dangerous SQL, but validate here too
           if not self._is_safe_query(query):
               return ToolResult(
                   content=[{"type": "text", "text": "Only SELECT queries are allowed"}],
                   is_error=True,
               )

           try:
               results = self._execute_query(query, limit)
               return ToolResult(
                   content=[{"type": "text", "text": self._format_results(results)}],
                   is_error=False,
               )
           except Exception as e:
               return ToolResult(
                   content=[{"type": "text", "text": f"Query error: {e}"}],
                   is_error=True,
               )

       def _is_safe_query(self, query: str) -> bool:
           '''Check if query is read-only (defense in depth).'''
           dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
                        "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC"]
           query_upper = query.upper()
           return not any(kw in query_upper for kw in dangerous)
   ```

2. UPDATE THE SECURITY POLICY (config/policy.yaml)
   ------------------------------------------------
   For a database plugin, you MUST configure network access and add query
   validation. See config/policy.yaml for a full example, but the key sections:

   ```yaml
   network:
     allowed_endpoints:
       - host: "db.internal.company.com"
         ports: [5432]                      # PostgreSQL
         description: "Production database (read-only replica)"

     # Or for local databases:
     allowed_ranges:
       - "127.0.0.1/32"  # localhost only

   # Add database-specific security (custom section for your validator)
   database:
     # Only allow read operations
     blocked_keywords:
       - "INSERT"
       - "UPDATE"
       - "DELETE"
       - "DROP"
       - "TRUNCATE"
       - "ALTER"
       - "CREATE"
       - "EXEC"
       - "EXECUTE"

     # Tables that should never be queried
     blocked_tables:
       - "users_credentials"
       - "api_keys"
       - "sessions"
       - "audit_log"

     # Maximum query execution time (seconds)
     query_timeout: 30

     # Maximum rows returned
     max_rows: 1000
   ```

3. REGISTER YOUR PLUGIN (main.py)
   --------------------------------
   Import and register your plugin in main.py:

   ```python
   from src.plugins.dbquery import DBQueryPlugin

   # In main():
   server.register_plugin(DBQueryPlugin(
       connection_string=os.environ.get("DB_CONNECTION_STRING")
   ))
   ```

4. WRITE TESTS (tests/test_dbquery.py)
   -------------------------------------
   Follow TDD - write failing tests first:

   ```python
   class TestDBQueryPlugin:
       def test_implements_plugin_interface(self):
           plugin = DBQueryPlugin("sqlite:///:memory:")
           assert isinstance(plugin, PluginBase)

       def test_blocks_dangerous_queries(self):
           plugin = DBQueryPlugin("sqlite:///:memory:")
           result = plugin.execute("query_database", {"query": "DROP TABLE users"})
           assert result.is_error is True
           assert "SELECT" in result.content[0]["text"]
   ```

5. SECURITY CONSIDERATIONS FOR DATABASE PLUGINS
   -----------------------------------------------
   - Use a READ-ONLY database user/connection
   - Connect to a read replica, not the primary database
   - Validate queries at multiple layers (plugin + security policy)
   - Never include connection strings in code - use environment variables
   - Log all queries to the audit trail
   - Set query timeouts to prevent long-running queries
   - Limit result set sizes to prevent memory exhaustion
   - Block access to sensitive tables (credentials, PII, etc.)
   - Consider using parameterized queries if accepting user input

================================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolDefinition:
    """Definition of a tool provided by a plugin."""

    name: str
    description: str
    input_schema: dict[str, Any]
    aliases: list[str] = field(default_factory=list)
    intent_categories: list[str] = field(default_factory=list)

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

    Plugins must implement this interface to provide tools to the MCP server.

    Required Methods:
        - name: Return a unique identifier for the plugin (e.g., "dbquery")
        - version: Return the semantic version (e.g., "1.0.0")
        - get_tools(): Return list of ToolDefinition objects describing available tools
        - execute(): Handle tool invocations and return ToolResult

    Lifecycle:
        1. Plugin is instantiated (with any config in __init__)
        2. Plugin is registered with server via server.register_plugin(plugin)
        3. get_tools() is called when MCP client requests tools/list
        4. execute() is called when MCP client calls tools/call

    Security:
        - The security layer validates all inputs BEFORE execute() is called
        - Network access is blocked unless explicitly allowed in policy.yaml
        - Always implement defense-in-depth: validate inputs in execute() too
        - Never trust input data - sanitize and validate everything

    See the module docstring above for a complete example of implementing
    a database query plugin with proper security controls.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the plugin identifier."""
        pass  # pragma: no cover

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the plugin version."""
        pass  # pragma: no cover

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        """Return tool definitions provided by this plugin.

        Returns:
            List of ToolDefinition objects.
        """
        pass  # pragma: no cover

    @abstractmethod
    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            ToolResult with content and error status.
        """
        pass  # pragma: no cover

    def cleanup(self) -> None:  # noqa: B027
        """Clean up plugin resources.

        Called when the server is shutting down. Override this method
        to release any resources held by the plugin (database connections,
        file handles, etc.).

        The default implementation does nothing.
        """
        pass

    def is_available(self) -> bool:
        """Check if the plugin is available for use.

        Override this method to check for required environment variables,
        API keys, or other prerequisites. Plugins that return False will
        be filtered out of search results by default.

        Returns:
            True if the plugin is ready to use, False otherwise.
        """
        return True

    def availability_hint(self) -> str:
        """Return a hint for how to make the plugin available.

        Override this method to provide guidance when is_available() returns
        False. For example: "Set FIGMA_API_TOKEN environment variable."

        Returns:
            A hint string, or empty string if no hint is available.
        """
        return ""
