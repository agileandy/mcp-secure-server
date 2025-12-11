"""Integrated security policy engine.

Provides a unified interface for all security operations, combining
firewall, validator, and audit logger into a single engine.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from mcp_secure_server.security.audit import AuditLogger
from mcp_secure_server.security.firewall import NetworkFirewall, SecurityError
from mcp_secure_server.security.policy import SecurityPolicy
from mcp_secure_server.security.ratelimiter import RateLimiter
from mcp_secure_server.security.ratelimiter import RateLimitExceeded as RateLimitExceeded  # Re-export
from mcp_secure_server.security.validator import InputValidator, ValidationError


class SecurityViolation(Exception):
    """Raised when a security policy is violated."""

    pass


class SecurityEngine:
    """Unified security engine integrating all security components.

    This engine provides:
    - Network access control via firewall
    - Input validation and sanitization
    - Rate limiting
    - Audit logging
    """

    def __init__(
        self,
        policy: SecurityPolicy,
        rate_limit_window_seconds: float = 60.0,
    ) -> None:
        """Initialize the security engine.

        Args:
            policy: Security policy to enforce.
            rate_limit_window_seconds: Time window for rate limiting.
        """
        self._policy = policy
        self._firewall = NetworkFirewall(policy)
        self._validator = InputValidator(policy)
        self._rate_limiter = RateLimiter(window_seconds=rate_limit_window_seconds)

        # Initialize audit logger if configured
        if policy.audit_log_file:
            log_path = Path(policy.audit_log_file)
            self._audit_logger: AuditLogger | None = AuditLogger(log_path)
        else:
            self._audit_logger = None

    def validate_network(self, host: str, port: int) -> bool:
        """Validate network access.

        Args:
            host: Target hostname or IP.
            port: Target port.

        Returns:
            True if access is allowed.

        Raises:
            SecurityViolation: If access is blocked.
        """
        try:
            return self._firewall.validate_address(host, port)
        except SecurityError as e:
            self._log_security_event(
                "network_blocked",
                {
                    "host": host,
                    "port": port,
                    "reason": str(e),
                },
            )
            raise SecurityViolation(str(e)) from e

    def validate_url(self, url: str) -> bool:
        """Validate URL access.

        Args:
            url: Target URL.

        Returns:
            True if access is allowed.

        Raises:
            SecurityViolation: If access is blocked.
        """
        try:
            return self._firewall.validate_url(url)
        except SecurityError as e:
            self._log_security_event(
                "url_blocked",
                {
                    "url": url,
                    "reason": str(e),
                },
            )
            raise SecurityViolation(str(e)) from e

    def validate_input(
        self, tool_name: str, schema: dict[str, Any], arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate and sanitize tool input.

        Args:
            tool_name: Name of the tool.
            schema: JSON Schema for validation.
            arguments: Arguments to validate.

        Returns:
            Validated and sanitized arguments.

        Raises:
            SecurityViolation: If validation fails.
        """
        try:
            return self._validator.validate_tool_input(tool_name, schema, arguments)
        except ValidationError as e:
            self._log_security_event(
                "input_validation_failed",
                {
                    "tool": tool_name,
                    "reason": str(e),
                },
            )
            raise SecurityViolation(f"Input validation failed: {e}") from e

    def check_rate_limit(self, tool_name: str) -> None:
        """Check if tool is within rate limit.

        Args:
            tool_name: Name of the tool.

        Raises:
            RateLimitExceeded: If rate limit is exceeded.
        """
        limit = self._policy.get_rate_limit(tool_name)
        try:
            self._rate_limiter.check_rate_limit(tool_name, limit)
        except RateLimitExceeded:
            self._log_security_event(
                "rate_limit_exceeded",
                {
                    "tool": tool_name,
                    "limit": limit,
                    "window_seconds": self._rate_limiter.window_seconds,
                },
            )
            raise

    def get_timeout(self) -> int:
        """Get configured timeout for tool execution.

        Returns:
            Timeout in seconds.
        """
        return self._policy.tool_timeout

    def log_tool_execution(
        self, request_id: str, tool_name: str, arguments: dict[str, Any]
    ) -> None:
        """Log a tool execution request.

        Args:
            request_id: Unique request identifier.
            tool_name: Name of the tool.
            arguments: Tool arguments.
        """
        if self._audit_logger:
            self._audit_logger.log_request(request_id, tool_name, arguments)

    def log_tool_result(self, request_id: str, status: str, duration_ms: float) -> None:
        """Log a tool execution result.

        Args:
            request_id: Request identifier.
            status: Result status.
            duration_ms: Execution duration in milliseconds.
        """
        if self._audit_logger:
            self._audit_logger.log_response(request_id, status, duration_ms)

    def _log_security_event(self, event_type: str, details: dict[str, Any]) -> None:
        """Log a security event.

        Args:
            event_type: Type of security event.
            details: Event details.
        """
        if self._audit_logger:
            self._audit_logger.log_security_event(event_type, details)

    def generate_request_id(self) -> str:
        """Generate a unique request ID.

        Returns:
            Unique request identifier.
        """
        return str(uuid.uuid4())

    def close(self) -> None:
        """Close the security engine and flush logs."""
        if self._audit_logger:
            self._audit_logger.close()

    def __enter__(self) -> SecurityEngine:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
