"""Network firewall validation layer.

Enforces network access restrictions based on security policy.
All network operations must pass through this firewall before execution.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from src.security.policy import SecurityPolicy


class SecurityError(Exception):
    """Raised when a security policy violation is detected."""

    pass


def parse_ip_network(cidr: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
    """Parse a CIDR notation string into an IP network.

    Args:
        cidr: CIDR notation string (e.g., "192.168.1.0/24").

    Returns:
        IP network object or None if invalid.
    """
    try:
        return ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return None


def is_private_address(address: str) -> bool:
    """Check if an IP address is in a private/local range.

    Args:
        address: IP address string.

    Returns:
        True if the address is private/local, False otherwise.
    """
    try:
        ip = ipaddress.ip_address(address)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


class NetworkFirewall:
    """Network firewall that enforces security policy on all network access.

    This firewall implements a fail-closed design: all network operations
    are blocked by default unless explicitly allowed by policy.
    """

    def __init__(self, policy: SecurityPolicy) -> None:
        """Initialize the firewall with a security policy.

        Args:
            policy: Security policy to enforce.
        """
        self._policy = policy
        self._allowed_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        self._dns_cache: dict[str, str] = {}

        # Parse allowed network ranges
        for cidr in policy.network_allowed_ranges:
            network = parse_ip_network(cidr)
            if network:
                self._allowed_networks.append(network)

    def _is_ip_in_allowed_ranges(self, ip_str: str) -> bool:
        """Check if an IP address is in the allowed ranges.

        Args:
            ip_str: IP address string.

        Returns:
            True if in allowed ranges, False otherwise.
        """
        try:
            ip = ipaddress.ip_address(ip_str)
            for network in self._allowed_networks:
                if ip in network:
                    return True
            return False
        except ValueError:
            return False

    def _resolve_hostname(self, hostname: str) -> str:
        """Resolve a hostname to an IP address with caching.

        Args:
            hostname: Hostname to resolve.

        Returns:
            Resolved IP address.

        Raises:
            SecurityError: If DNS resolution fails or is not allowed.
        """
        # Check cache first
        if hostname in self._dns_cache:
            return self._dns_cache[hostname]

        # Check if hostname is already an IP address
        try:
            ipaddress.ip_address(hostname)
            return hostname
        except ValueError:
            pass  # Not an IP, need to resolve

        # Check DNS policy
        if not self._policy.allow_dns:
            raise SecurityError(f"DNS resolution disabled by policy for: {hostname}")

        if not self._policy.is_dns_allowed(hostname):
            raise SecurityError(f"DNS resolution not allowed for: {hostname}")

        try:
            # Resolve hostname
            results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
            if not results:
                raise SecurityError(f"DNS resolution failed for: {hostname}")

            # Get first IP address
            ip_address = results[0][4][0]
            self._dns_cache[hostname] = ip_address
            return ip_address
        except socket.gaierror as e:
            raise SecurityError(f"DNS resolution failed for {hostname}: {e}") from e

    def validate_address(self, host: str, port: int) -> bool:
        """Validate that a host:port combination is allowed.

        Args:
            host: Hostname or IP address.
            port: Port number.

        Returns:
            True if access is allowed.

        Raises:
            SecurityError: If access is blocked by policy.
        """
        if self._policy.is_port_blocked(port):
            raise SecurityError(f"Access denied: port {port} is blocked by policy")

        # Try to validate as IP address first
        if self._validate_ip_address(host, port):
            return True

        # Not an IP address, validate as hostname
        return self._validate_hostname(host, port)

    def _validate_ip_address(self, host: str, port: int) -> bool:
        """Validate a raw IP address.

        Args:
            host: Potential IP address string.
            port: Port number.

        Returns:
            True if valid IP in allowed ranges, False if not an IP address.

        Raises:
            SecurityError: If IP is not in allowed ranges.
        """
        try:
            ip = ipaddress.ip_address(host)
            ip_str = str(ip)

            if self._is_ip_in_allowed_ranges(ip_str):
                return True

            raise SecurityError(f"Access denied: address {host}:{port} is not allowed")

        except ValueError:
            # Not an IP address
            return False

    def _validate_hostname(self, host: str, port: int) -> bool:
        """Validate a hostname for network access.

        Args:
            host: Hostname to validate.
            port: Port number.

        Returns:
            True if access is allowed.

        Raises:
            SecurityError: If access is blocked by policy.
        """
        if host == "localhost":
            return True

        # Check if hostname is in external endpoint allowlist
        if self._policy.is_endpoint_allowed(host, port):
            self._resolve_hostname(host)  # Resolve to verify
            return True

        # Enforce DNS policy for non-allowlisted hosts
        self._enforce_dns_policy(host)

        # Hostname is in DNS allowlist - resolve and check if private
        ip_str = self._resolve_hostname(host)
        if self._is_ip_in_allowed_ranges(ip_str):
            return True

        raise SecurityError(f"Access denied: {host}:{port} is not allowed")

    def _enforce_dns_policy(self, host: str) -> None:
        """Check if DNS resolution is allowed for a hostname.

        Args:
            host: Hostname to check.

        Raises:
            SecurityError: If DNS resolution is not allowed.
        """
        if not self._policy.allow_dns:
            raise SecurityError(f"DNS resolution disabled by policy for: {host}")

        if not self._policy.is_dns_allowed(host):
            raise SecurityError(f"DNS resolution not allowed for: {host}")

    def validate_url(self, url: str) -> bool:
        """Validate that a URL is allowed by policy.

        Args:
            url: Full URL to validate.

        Returns:
            True if access is allowed.

        Raises:
            SecurityError: If access is blocked by policy.
        """
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise SecurityError(f"Invalid URL: {url}") from e

        if not parsed.scheme or not parsed.hostname:
            raise SecurityError(f"Invalid URL: {url}")

        # Determine port
        if parsed.port:
            port = parsed.port
        elif parsed.scheme == "https":
            port = 443
        elif parsed.scheme == "http":
            port = 80
        else:
            raise SecurityError(f"Unsupported URL scheme: {parsed.scheme}")

        return self.validate_address(parsed.hostname, port)
