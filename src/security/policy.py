"""Security policy loader and validation.

This module handles loading security policies from YAML configuration files
and provides validation methods for the security layer.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class PolicyLoadError(Exception):
    """Raised when policy loading or validation fails."""

    pass


def expand_env_vars(value: str) -> str:
    """Expand environment variables in a string.

    Supports ${VAR_NAME} syntax. Unknown variables are left unchanged.

    Args:
        value: String potentially containing environment variable references.

    Returns:
        String with known environment variables expanded.
    """
    pattern = re.compile(r"\$\{([^}]+)\}")

    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is not None:
            return env_value
        # Special handling for HOME
        if var_name == "HOME":
            return os.path.expanduser("~")
        return match.group(0)  # Return unchanged if not found

    return pattern.sub(replacer, value)


@dataclass
class SecurityPolicy:
    """Security policy configuration.

    Immutable configuration loaded from policy.yaml that defines all security
    constraints for the MCP server.
    """

    version: str

    # Network settings
    network_allowed_ranges: list[str] = field(default_factory=list)
    network_allowed_endpoints: list[dict[str, Any]] = field(default_factory=list)
    network_blocked_ports: list[int] = field(default_factory=list)
    allow_dns: bool = False
    dns_allowlist: list[str] = field(default_factory=list)

    # Filesystem settings
    filesystem_allowed_paths: list[str] = field(default_factory=list)
    filesystem_denied_paths: list[str] = field(default_factory=list)

    # Command settings
    commands_blocked: list[str] = field(default_factory=list)

    # Tool settings
    tool_rate_limits: dict[str, int] = field(default_factory=dict)
    tool_timeout: int = 30

    # Audit settings
    audit_log_file: str = ""
    audit_log_level: str = "INFO"
    audit_include: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> SecurityPolicy:
        """Create a SecurityPolicy from a configuration dictionary.

        Args:
            config: Dictionary parsed from YAML configuration.

        Returns:
            SecurityPolicy instance with all settings populated.
        """
        network = config.get("network", {})
        filesystem = config.get("filesystem", {})
        commands = config.get("commands", {})
        tools = config.get("tools", {})
        audit = config.get("audit", {})

        # Expand environment variables in paths
        allowed_paths = [expand_env_vars(p) for p in filesystem.get("allowed_paths", [])]
        denied_paths = [expand_env_vars(p) for p in filesystem.get("denied_paths", [])]
        log_file = expand_env_vars(audit.get("log_file", ""))

        return cls(
            version=config.get("version", ""),
            network_allowed_ranges=network.get("allowed_ranges", []),
            network_allowed_endpoints=network.get("allowed_endpoints", []),
            network_blocked_ports=network.get("blocked_ports", []),
            allow_dns=network.get("allow_dns", False),
            dns_allowlist=network.get("dns_allowlist", []),
            filesystem_allowed_paths=allowed_paths,
            filesystem_denied_paths=denied_paths,
            commands_blocked=commands.get("blocked", []),
            tool_rate_limits=tools.get("rate_limits", {}),
            tool_timeout=tools.get("timeout", 30),
            audit_log_file=log_file,
            audit_log_level=audit.get("log_level", "INFO"),
            audit_include=audit.get("include", []),
        )

    def is_port_blocked(self, port: int) -> bool:
        """Check if a port is in the blocked list.

        Args:
            port: Port number to check.

        Returns:
            True if the port is blocked, False otherwise.
        """
        return port in self.network_blocked_ports

    def is_command_blocked(self, command: str) -> bool:
        """Check if a command is in the blocked list.

        Args:
            command: Command name to check.

        Returns:
            True if the command is blocked, False otherwise.
        """
        return command in self.commands_blocked

    def is_endpoint_allowed(self, host: str, port: int) -> bool:
        """Check if an external endpoint is explicitly allowed.

        Args:
            host: Hostname to check.
            port: Port number to check.

        Returns:
            True if the endpoint is in the allowlist, False otherwise.
        """
        for endpoint in self.network_allowed_endpoints:
            if endpoint.get("host") == host and port in endpoint.get("ports", []):
                return True
        return False

    def get_rate_limit(self, tool_name: str) -> int:
        """Get the rate limit for a specific tool.

        Args:
            tool_name: Name of the tool.

        Returns:
            Rate limit in requests per minute, or default if not specified.
        """
        return self.tool_rate_limits.get(tool_name, self.tool_rate_limits.get("default", 60))

    def is_dns_allowed(self, hostname: str) -> bool:
        """Check if DNS resolution is allowed for a hostname.

        Args:
            hostname: Hostname to check.

        Returns:
            True if DNS resolution is allowed, False otherwise.
        """
        if not self.allow_dns:
            return False
        return hostname in self.dns_allowlist


def load_policy(path: Path) -> SecurityPolicy:
    """Load security policy from a YAML file.

    Args:
        path: Path to the policy YAML file.

    Returns:
        SecurityPolicy instance.

    Raises:
        PolicyLoadError: If the file cannot be found, parsed, or validated.
    """
    if not path.exists():
        raise PolicyLoadError(f"Policy file not found: {path}")

    try:
        with open(path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise PolicyLoadError(f"Failed to parse policy YAML: {e}") from e

    if not isinstance(config, dict):
        raise PolicyLoadError("Policy must be a YAML mapping")

    if "version" not in config:
        raise PolicyLoadError("Policy must include 'version' field")

    return SecurityPolicy.from_dict(config)
