"""Tests for audit logging system."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

from src.security.audit import AuditEvent, AuditLogger, SecurityEvent


class TestAuditEvent:
    """Tests for AuditEvent dataclass."""

    def test_to_dict_includes_all_fields(self):
        """Should serialize all fields to dictionary."""
        event = AuditEvent(
            timestamp="2024-01-15T10:30:00Z",
            request_id="req-123",
            tool_name="web_search",
            arguments={"query": "test"},
            result_status="success",
            execution_time_ms=150.5,
        )
        d = event.to_dict()

        assert d["timestamp"] == "2024-01-15T10:30:00Z"
        assert d["request_id"] == "req-123"
        assert d["tool_name"] == "web_search"
        assert d["arguments"] == {"query": "test"}
        assert d["result_status"] == "success"
        assert d["execution_time_ms"] == 150.5

    def test_to_json_returns_valid_json(self):
        """Should return valid JSON string."""
        event = AuditEvent(
            timestamp="2024-01-15T10:30:00Z",
            request_id="req-123",
            tool_name="echo",
            arguments={},
            result_status="success",
            execution_time_ms=10.0,
        )
        json_str = event.to_json()
        parsed = json.loads(json_str)

        assert parsed["request_id"] == "req-123"


class TestSecurityEvent:
    """Tests for SecurityEvent dataclass."""

    def test_to_dict_includes_all_fields(self):
        """Should serialize security event fields."""
        event = SecurityEvent(
            timestamp="2024-01-15T10:30:00Z",
            event_type="policy_violation",
            details={"blocked": "external_network", "target": "evil.com"},
        )
        d = event.to_dict()

        assert d["timestamp"] == "2024-01-15T10:30:00Z"
        assert d["event_type"] == "policy_violation"
        assert d["details"]["blocked"] == "external_network"


class TestAuditLogger:
    """Tests for AuditLogger class."""

    def test_creates_log_directory_if_missing(self):
        """Should create log directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "subdir" / "audit.log"
            logger = AuditLogger(log_path)

            assert log_path.parent.exists()
            logger.close()

    def test_log_request_writes_to_file(self):
        """Should write request event to log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path)

            logger.log_request("req-001", "test_tool", {"arg": "value"})
            logger.close()

            content = log_path.read_text()
            assert "req-001" in content
            assert "test_tool" in content

    def test_log_response_writes_to_file(self):
        """Should write response event to log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path)

            logger.log_response("req-001", "success", 100.5)
            logger.close()

            content = log_path.read_text()
            assert "req-001" in content
            assert "success" in content

    def test_log_security_event_writes_to_file(self):
        """Should write security event to log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path)

            logger.log_security_event("blocked", {"reason": "external_network"})
            logger.close()

            content = log_path.read_text()
            assert "blocked" in content
            assert "external_network" in content

    def test_logs_are_json_lines_format(self):
        """Should write logs in JSON Lines format (one JSON per line)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path)

            logger.log_request("req-001", "tool1", {})
            logger.log_request("req-002", "tool2", {})
            logger.close()

            lines = log_path.read_text().strip().split("\n")
            assert len(lines) == 2

            # Each line should be valid JSON
            for line in lines:
                parsed = json.loads(line)
                assert "timestamp" in parsed

    def test_timestamp_is_iso8601_utc(self):
        """Should use ISO 8601 format with UTC timezone."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path)

            logger.log_request("req-001", "tool", {})
            logger.close()

            content = log_path.read_text()
            parsed = json.loads(content)
            timestamp = parsed["timestamp"]

            # Should be parseable as ISO 8601
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            assert dt.tzinfo is not None

    def test_sanitizes_sensitive_arguments(self):
        """Should sanitize potentially sensitive data in arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path)

            # Arguments with sensitive-looking keys
            args = {
                "query": "normal query",
                "password": "secret123",
                "api_key": "sk-12345",
                "token": "bearer-xyz",
            }
            logger.log_request("req-001", "tool", args)
            logger.close()

            content = log_path.read_text()
            parsed = json.loads(content)

            # Normal args should be preserved
            assert parsed["arguments"]["query"] == "normal query"
            # Sensitive args should be redacted
            assert parsed["arguments"]["password"] == "[REDACTED]"
            assert parsed["arguments"]["api_key"] == "[REDACTED]"
            assert parsed["arguments"]["token"] == "[REDACTED]"

    def test_context_manager_support(self):
        """Should support context manager protocol."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"

            with AuditLogger(log_path) as logger:
                logger.log_request("req-001", "tool", {})

            # File should be written and closed
            assert log_path.exists()
            content = log_path.read_text()
            assert "req-001" in content

    def test_append_mode_preserves_existing_logs(self):
        """Should append to existing log file, not overwrite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"

            # First logger session
            with AuditLogger(log_path) as logger:
                logger.log_request("req-001", "tool1", {})

            # Second logger session
            with AuditLogger(log_path) as logger:
                logger.log_request("req-002", "tool2", {})

            # Both entries should exist
            content = log_path.read_text()
            assert "req-001" in content
            assert "req-002" in content

    def test_flush_on_each_write(self):
        """Should flush after each write for durability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.log"
            logger = AuditLogger(log_path)

            logger.log_request("req-001", "tool", {})
            # Should be readable immediately without close
            content = log_path.read_text()
            assert "req-001" in content

            logger.close()
