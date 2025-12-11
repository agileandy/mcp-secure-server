"""Tests for integrated security policy engine."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_secure_server.security.engine import (
    RateLimitExceeded,
    SecurityEngine,
    SecurityViolation,
)
from mcp_secure_server.security.policy import SecurityPolicy


@pytest.fixture
def policy_with_audit():
    """Create a policy with audit logging to a temp file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        policy = SecurityPolicy.from_dict(
            {
                "version": "1.0",
                "network": {
                    "allowed_ranges": ["127.0.0.0/8"],
                    "allowed_endpoints": [
                        {"host": "api.duckduckgo.com", "ports": [443]},
                    ],
                    "blocked_ports": [22],
                    "allow_dns": True,
                    "dns_allowlist": ["api.duckduckgo.com"],
                },
                "filesystem": {
                    "allowed_paths": [f"{tmpdir}/**"],
                    "denied_paths": ["**/.ssh/**"],
                },
                "commands": {
                    "blocked": ["curl", "wget"],
                },
                "tools": {
                    "rate_limits": {
                        "default": 60,
                        "web_search": 5,
                    },
                    "timeout": 30,
                },
                "audit": {
                    "log_file": f"{tmpdir}/audit.log",
                },
            }
        )
        yield policy, tmpdir


class TestSecurityEngine:
    """Tests for SecurityEngine class."""

    def test_validates_network_access(self, policy_with_audit):
        """Should validate network access through firewall."""
        policy, tmpdir = policy_with_audit
        engine = SecurityEngine(policy)

        # Local address should be allowed
        assert engine.validate_network("127.0.0.1", 8080) is True

        # External address should be blocked
        with pytest.raises(SecurityViolation, match="not allowed"):
            engine.validate_network("8.8.8.8", 443)

    def test_validates_url_access(self, policy_with_audit):
        """Should validate URL access."""
        policy, tmpdir = policy_with_audit
        engine = SecurityEngine(policy)

        # Local URL should be allowed
        assert engine.validate_url("http://127.0.0.1:8080/api") is True

        # External URL should be blocked
        with pytest.raises(SecurityViolation):
            engine.validate_url("https://evil.com/")

    def test_validates_tool_input(self, policy_with_audit):
        """Should validate tool input through validator."""
        policy, tmpdir = policy_with_audit
        engine = SecurityEngine(policy)

        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        }

        # Valid input should pass
        result = engine.validate_input("search", schema, {"query": "test"})
        assert result["query"] == "test"

        # Invalid input should raise
        with pytest.raises(SecurityViolation, match="validation"):
            engine.validate_input("search", schema, {})

    def test_enforces_rate_limits(self, policy_with_audit):
        """Should enforce rate limits for tools."""
        policy, tmpdir = policy_with_audit
        engine = SecurityEngine(policy)

        # web_search has rate limit of 5 per minute
        for _ in range(5):
            engine.check_rate_limit("web_search")

        # 6th call should be blocked
        with pytest.raises(RateLimitExceeded):
            engine.check_rate_limit("web_search")

    def test_rate_limits_reset_over_time(self, policy_with_audit):
        """Should reset rate limits after window passes."""
        policy, tmpdir = policy_with_audit
        # Use a very short window for testing
        engine = SecurityEngine(policy, rate_limit_window_seconds=0.1)

        # Use up rate limit
        for _ in range(5):
            engine.check_rate_limit("web_search")

        # Wait for window to pass
        time.sleep(0.15)

        # Should be allowed again
        engine.check_rate_limit("web_search")

    def test_logs_security_events(self, policy_with_audit):
        """Should log security violations to audit log."""
        policy, tmpdir = policy_with_audit
        engine = SecurityEngine(policy)

        # Trigger a security violation
        try:
            engine.validate_network("8.8.8.8", 443)
        except SecurityViolation:
            pass

        engine.close()

        # Check audit log
        log_path = Path(tmpdir) / "audit.log"
        assert log_path.exists()
        content = log_path.read_text()
        assert "security" in content.lower() or "blocked" in content.lower()

    def test_logs_successful_operations(self, policy_with_audit):
        """Should log successful operations."""
        policy, tmpdir = policy_with_audit
        engine = SecurityEngine(policy)

        # Successful validation
        engine.log_tool_execution("req-123", "test_tool", {"arg": "value"})
        engine.log_tool_result("req-123", "success", 100.0)
        engine.close()

        # Check audit log
        log_path = Path(tmpdir) / "audit.log"
        content = log_path.read_text()
        assert "req-123" in content
        assert "test_tool" in content

    def test_context_manager_support(self, policy_with_audit):
        """Should support context manager protocol."""
        policy, tmpdir = policy_with_audit

        with SecurityEngine(policy) as engine:
            engine.validate_network("127.0.0.1", 8080)

        # Log should be written and closed
        log_path = Path(tmpdir) / "audit.log"
        assert log_path.exists()

    def test_get_timeout(self, policy_with_audit):
        """Should return configured timeout."""
        policy, tmpdir = policy_with_audit
        engine = SecurityEngine(policy)

        assert engine.get_timeout() == 30


class TestSecurityEngineAllowlist:
    """Tests for allowlist functionality."""

    def test_allows_allowlisted_external_endpoint(self, policy_with_audit):
        """Should allow explicitly allowlisted external endpoints."""
        policy, tmpdir = policy_with_audit
        engine = SecurityEngine(policy)

        # Mock DNS resolution
        with patch.object(engine._firewall, "_resolve_hostname", return_value="52.1.2.3"):
            assert engine.validate_network("api.duckduckgo.com", 443) is True
            assert engine.validate_url("https://api.duckduckgo.com/?q=test") is True


class TestSecurityEngineEdgeCases:
    """Edge case tests for SecurityEngine."""

    def test_engine_without_audit_logger(self):
        """Should work without audit logging configured."""
        policy = SecurityPolicy.from_dict(
            {
                "version": "1.0",
                "network": {
                    "allowed_ranges": ["127.0.0.0/8"],
                },
            }
        )
        engine = SecurityEngine(policy)

        # Should work without errors
        engine.log_tool_execution("req-001", "tool", {})
        engine.log_tool_result("req-001", "success", 100.0)
        engine.close()

    def test_generate_request_id(self, policy_with_audit):
        """Should generate unique request IDs."""
        policy, tmpdir = policy_with_audit
        engine = SecurityEngine(policy)

        ids = [engine.generate_request_id() for _ in range(100)]
        # All IDs should be unique
        assert len(set(ids)) == 100

    def test_logs_url_blocked_event(self, policy_with_audit):
        """Should log URL blocked security event."""
        policy, tmpdir = policy_with_audit
        engine = SecurityEngine(policy)

        try:
            engine.validate_url("https://evil.com/malware")
        except SecurityViolation:
            pass

        engine.close()

        log_path = Path(tmpdir) / "audit.log"
        content = log_path.read_text()
        assert "url_blocked" in content or "evil.com" in content
