#!/usr/bin/env python3
"""MCP Secure Local Server - Main entry point.

A production-ready, security-first MCP server that runs locally with
strict security controls but can make allowlisted external network calls.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
    server.register_plugin(WebSearchPlugin())

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
