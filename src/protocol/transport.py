"""STDIO transport layer for MCP communication.

Handles reading/writing JSON-RPC messages over stdin/stdout per MCP spec.
"""

from __future__ import annotations

import sys
from typing import TextIO


class StdioTransport:
    """STDIO transport for MCP communication.

    Reads JSON-RPC messages from stdin and writes responses to stdout.
    Logging goes to stderr to avoid corrupting the protocol stream.
    """

    def __init__(
        self,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
        stderr: TextIO | None = None,
    ) -> None:
        """Initialize the transport.

        Args:
            stdin: Input stream (defaults to sys.stdin).
            stdout: Output stream (defaults to sys.stdout).
            stderr: Log stream (defaults to sys.stderr).
        """
        self._stdin = stdin or sys.stdin
        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr

    def read_message(self) -> str | None:
        """Read a message from stdin.

        Reads lines until a non-empty line is found.

        Returns:
            Message string (stripped), or None on EOF.
        """
        while True:
            try:
                line = self._stdin.readline()
            except Exception:
                return None

            if not line:  # EOF
                return None

            line = line.strip()
            if line:  # Skip empty lines
                return line

    def write_message(self, message: str) -> None:
        """Write a message to stdout.

        Args:
            message: JSON string to write.
        """
        self._stdout.write(message + "\n")
        self._stdout.flush()

    def log(self, message: str) -> None:
        """Write a log message to stderr.

        Args:
            message: Log message.
        """
        self._stderr.write(f"[MCP] {message}\n")
        self._stderr.flush()
