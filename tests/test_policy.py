"""Tests for security policy loader and schema validation."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.security.policy import (
    PolicyLoadError,
    SecurityPolicy,
    expand_env_vars,
    load_policy,
)


class TestExpandEnvVars:
    """Tests for environment variable expansion."""

    def test_expands_home_variable(self):
        """Should expand ${HOME} to actual home directory."""
        result = expand_env_vars("${HOME}/projects")
        assert result == os.path.expanduser("~") + "/projects"

    def test_expands_custom_variable(self):
        """Should expand custom environment variables."""
        os.environ["TEST_MCP_VAR"] = "/custom/path"
        try:
            result = expand_env_vars("${TEST_MCP_VAR}/subdir")
            assert result == "/custom/path/subdir"
        finally:
            del os.environ["TEST_MCP_VAR"]

    def test_leaves_unknown_variables_unchanged(self):
        """Should leave unknown variables as-is (fail-safe)."""
        result = expand_env_vars("${UNKNOWN_VAR_12345}/path")
        assert result == "${UNKNOWN_VAR_12345}/path"

    def test_handles_no_variables(self):
        """Should handle strings without variables."""
        result = expand_env_vars("/simple/path")
        assert result == "/simple/path"


class TestSecurityPolicy:
    """Tests for SecurityPolicy dataclass."""

    def test_from_dict_minimal(self):
        """Should create policy from minimal valid config."""
        config = {"version": "1.0"}
        policy = SecurityPolicy.from_dict(config)
        assert policy.version == "1.0"
        assert policy.network_allowed_ranges == []
        assert policy.network_allowed_endpoints == []

    def test_from_dict_full(self):
        """Should parse full configuration correctly."""
        config = {
            "version": "1.0",
            "network": {
                "allowed_ranges": ["127.0.0.0/8", "10.0.0.0/8"],
                "allowed_endpoints": [{"host": "api.example.com", "ports": [443]}],
                "blocked_ports": [22],
                "allow_dns": True,
                "dns_allowlist": ["api.example.com"],
            },
            "filesystem": {
                "allowed_paths": ["${HOME}/projects/**"],
                "denied_paths": ["**/.ssh/**"],
            },
            "commands": {
                "blocked": ["curl", "wget"],
            },
            "tools": {
                "rate_limits": {"default": 60},
                "timeout": 30,
            },
            "audit": {
                "log_file": "${HOME}/.mcp-secure/audit.log",
                "log_level": "INFO",
            },
        }
        policy = SecurityPolicy.from_dict(config)

        assert policy.version == "1.0"
        assert "127.0.0.0/8" in policy.network_allowed_ranges
        assert len(policy.network_allowed_endpoints) == 1
        assert policy.network_allowed_endpoints[0]["host"] == "api.example.com"
        assert 22 in policy.network_blocked_ports
        assert policy.allow_dns is True
        assert "api.example.com" in policy.dns_allowlist
        assert "**/.ssh/**" in policy.filesystem_denied_paths
        assert "curl" in policy.commands_blocked
        assert policy.tool_timeout == 30

    def test_from_dict_expands_env_vars(self):
        """Should expand environment variables in paths."""
        config = {
            "version": "1.0",
            "filesystem": {
                "allowed_paths": ["${HOME}/projects/**"],
            },
            "audit": {
                "log_file": "${HOME}/.mcp-secure/audit.log",
            },
        }
        policy = SecurityPolicy.from_dict(config)

        home = os.path.expanduser("~")
        assert f"{home}/projects/**" in policy.filesystem_allowed_paths
        assert policy.audit_log_file == f"{home}/.mcp-secure/audit.log"


class TestLoadPolicy:
    """Tests for loading policy from YAML files."""

    def test_loads_valid_yaml(self):
        """Should load and parse valid YAML policy file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"version": "1.0"}, f)
            f.flush()

            try:
                policy = load_policy(Path(f.name))
                assert policy.version == "1.0"
            finally:
                os.unlink(f.name)

    def test_raises_on_missing_file(self):
        """Should raise PolicyLoadError for missing file."""
        with pytest.raises(PolicyLoadError, match="not found"):
            load_policy(Path("/nonexistent/policy.yaml"))

    def test_raises_on_invalid_yaml(self):
        """Should raise PolicyLoadError for malformed YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()

            try:
                with pytest.raises(PolicyLoadError, match="parse"):
                    load_policy(Path(f.name))
            finally:
                os.unlink(f.name)

    def test_raises_on_missing_version(self):
        """Should raise PolicyLoadError when version is missing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"network": {}}, f)
            f.flush()

            try:
                with pytest.raises(PolicyLoadError, match="version"):
                    load_policy(Path(f.name))
            finally:
                os.unlink(f.name)


class TestSecurityPolicyValidation:
    """Tests for policy validation methods."""

    def test_is_port_blocked(self):
        """Should correctly identify blocked ports."""
        policy = SecurityPolicy.from_dict(
            {
                "version": "1.0",
                "network": {"blocked_ports": [22, 23]},
            }
        )
        assert policy.is_port_blocked(22) is True
        assert policy.is_port_blocked(23) is True
        assert policy.is_port_blocked(443) is False

    def test_is_command_blocked(self):
        """Should correctly identify blocked commands."""
        policy = SecurityPolicy.from_dict(
            {
                "version": "1.0",
                "commands": {"blocked": ["curl", "wget"]},
            }
        )
        assert policy.is_command_blocked("curl") is True
        assert policy.is_command_blocked("wget") is True
        assert policy.is_command_blocked("ls") is False

    def test_is_endpoint_allowed(self):
        """Should correctly identify allowed external endpoints."""
        policy = SecurityPolicy.from_dict(
            {
                "version": "1.0",
                "network": {
                    "allowed_endpoints": [
                        {"host": "api.example.com", "ports": [443, 8443]},
                    ],
                },
            }
        )
        assert policy.is_endpoint_allowed("api.example.com", 443) is True
        assert policy.is_endpoint_allowed("api.example.com", 8443) is True
        assert policy.is_endpoint_allowed("api.example.com", 80) is False
        assert policy.is_endpoint_allowed("other.com", 443) is False

    def test_get_rate_limit(self):
        """Should return correct rate limits for tools."""
        policy = SecurityPolicy.from_dict(
            {
                "version": "1.0",
                "tools": {
                    "rate_limits": {
                        "default": 60,
                        "web_search": 20,
                    },
                },
            }
        )
        assert policy.get_rate_limit("web_search") == 20
        assert policy.get_rate_limit("unknown_tool") == 60

    def test_is_dns_allowed(self):
        """Should correctly check DNS allowlist."""
        policy = SecurityPolicy.from_dict(
            {
                "version": "1.0",
                "network": {
                    "allow_dns": True,
                    "dns_allowlist": ["api.example.com"],
                },
            }
        )
        assert policy.is_dns_allowed("api.example.com") is True
        assert policy.is_dns_allowed("other.com") is False

        # When DNS is disabled, nothing is allowed
        policy_no_dns = SecurityPolicy.from_dict(
            {
                "version": "1.0",
                "network": {"allow_dns": False},
            }
        )
        assert policy_no_dns.is_dns_allowed("api.example.com") is False
