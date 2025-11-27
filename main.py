#!/usr/bin/env python3
"""MCP Secure Local Server - Main entry point.

A production-ready, security-first MCP server that runs locally with
strict security controls but can make allowlisted external network calls.

================================================================================
DEVELOPER GUIDE: Registering New Plugins
================================================================================

To add a new plugin to the server, follow these steps:

1. CREATE YOUR PLUGIN
   Create a new file in src/plugins/ implementing the PluginBase interface.
   See src/plugins/base.py for the interface and a detailed example.

2. UPDATE SECURITY POLICY
   Edit config/policy.yaml to allow any required network access, set rate
   limits, and add any custom validation rules. See the file for examples.

3. REGISTER THE PLUGIN HERE
   Import and register your plugin in main() as shown below.

EXAMPLE: Adding a Database Query Plugin
---------------------------------------

Step 1: Import the plugin (add near other imports):

    from src.plugins.dbquery import DBQueryPlugin

Step 2: Register the plugin (add after other register_plugin calls):

    # Database query plugin - connects to read-only replica
    # SECURITY: Connection string from environment, never hardcoded
    db_connection = os.environ.get("MCP_DB_CONNECTION")
    if db_connection:
        server.register_plugin(DBQueryPlugin(connection_string=db_connection))
        transport.log("Database query plugin registered")
    else:
        transport.log("Warning: MCP_DB_CONNECTION not set, DB plugin disabled")

Step 3: Update config/policy.yaml to allow database network access:

    network:
      allowed_endpoints:
        - host: "db-readonly.internal.company.com"
          ports: [5432]
          description: "PostgreSQL read replica"

    tools:
      rate_limits:
        query_database: 30  # 30 queries per minute

SECURITY NOTES
--------------
- Never hardcode credentials - use environment variables
- Use read-only database replicas, never primary databases
- Set appropriate rate limits to prevent abuse
- All plugin operations are logged to the audit trail
- The security layer validates inputs before plugins see them

TESTING
-------
Always write tests for your plugin before deploying. See tests/test_websearch.py
for an example of how to mock external dependencies.

================================================================================
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.plugins.bugtracker import BugTrackerPlugin
from src.plugins.websearch import WebSearchPlugin
from src.protocol.transport import StdioTransport
from src.server import MCPServer


def main() -> int:
    """Run the MCP server.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = argparse.ArgumentParser(
        description="MCP Secure Local Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--policy",
        "-p",
        type=Path,
        default=Path("config/policy.yaml"),
        help="Path to security policy YAML file (default: config/policy.yaml)",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="mcp-secure-local 1.0.0",
    )

    args = parser.parse_args()

    # Check policy file exists
    if not args.policy.exists():
        print(f"Error: Policy file not found: {args.policy}", file=sys.stderr)
        return 1

    # Initialize server
    try:
        server = MCPServer(policy_path=args.policy)
    except Exception as e:
        print(f"Error loading server: {e}", file=sys.stderr)
        return 1

    # Register built-in plugins
    # -------------------------------------------------------------------------
    # DEVELOPER: Add your custom plugins here using server.register_plugin()
    #
    # Example:
    #     from src.plugins.dbquery import DBQueryPlugin
    #     server.register_plugin(DBQueryPlugin(connection_string=os.environ["DB_CONN"]))
    #
    # Each plugin's tools will automatically appear in the MCP tools/list response.
    # The security layer will validate all inputs before your plugin sees them.
    # -------------------------------------------------------------------------
    server.register_plugin(WebSearchPlugin())
    server.register_plugin(BugTrackerPlugin())

    # Setup transport
    transport = StdioTransport()
    transport.log("MCP Secure Local Server started")
    transport.log(f"Policy loaded from: {args.policy}")

    # Main message loop
    try:
        while True:
            message = transport.read_message()
            if message is None:
                transport.log("EOF received, shutting down")
                break

            response = server.handle_message(message)
            if response is not None:
                transport.write_message(response)

    except KeyboardInterrupt:
        transport.log("Interrupted, shutting down")
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        transport.log(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
