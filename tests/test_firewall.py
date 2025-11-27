"""Tests for network firewall validation layer."""

import socket
from unittest.mock import patch

import pytest

from src.security.firewall import (
    NetworkFirewall,
    SecurityError,
    is_private_address,
    parse_ip_network,
)
from src.security.policy import SecurityPolicy


@pytest.fixture
def basic_policy() -> SecurityPolicy:
    """Create a basic policy for testing."""
    return SecurityPolicy.from_dict(
        {
            "version": "1.0",
            "network": {
                "allowed_ranges": [
                    "127.0.0.0/8",
                    "10.0.0.0/8",
                    "172.16.0.0/12",
                    "192.168.0.0/16",
                ],
                "allowed_endpoints": [
                    {"host": "api.duckduckgo.com", "ports": [443]},
                ],
                "blocked_ports": [22],
                "allow_dns": True,
                "dns_allowlist": ["api.duckduckgo.com"],
            },
        }
    )


class TestParseIpNetwork:
    """Tests for IP network parsing."""

    def test_parses_valid_ipv4_cidr(self):
        """Should parse valid IPv4 CIDR notation."""
        network = parse_ip_network("192.168.1.0/24")
        assert network is not None
        assert network.version == 4

    def test_parses_valid_ipv6_cidr(self):
        """Should parse valid IPv6 CIDR notation."""
        network = parse_ip_network("fe80::/10")
        assert network is not None
        assert network.version == 6

    def test_returns_none_for_invalid(self):
        """Should return None for invalid CIDR."""
        assert parse_ip_network("invalid") is None
        assert parse_ip_network("999.999.999.999/32") is None


class TestIsPrivateAddress:
    """Tests for private address detection."""

    def test_localhost_is_private(self):
        """Should recognize localhost as private."""
        assert is_private_address("127.0.0.1") is True
        assert is_private_address("127.0.0.2") is True

    def test_private_ranges_are_private(self):
        """Should recognize RFC 1918 ranges as private."""
        assert is_private_address("10.0.0.1") is True
        assert is_private_address("10.255.255.255") is True
        assert is_private_address("172.16.0.1") is True
        assert is_private_address("172.31.255.255") is True
        assert is_private_address("192.168.1.1") is True
        assert is_private_address("192.168.255.255") is True

    def test_public_addresses_are_not_private(self):
        """Should recognize public addresses as not private."""
        assert is_private_address("8.8.8.8") is False
        assert is_private_address("1.1.1.1") is False
        assert is_private_address("52.1.2.3") is False

    def test_ipv6_localhost_is_private(self):
        """Should recognize IPv6 localhost as private."""
        assert is_private_address("::1") is True

    def test_ipv6_link_local_is_private(self):
        """Should recognize IPv6 link-local as private."""
        assert is_private_address("fe80::1") is True

    def test_invalid_address_returns_false(self):
        """Should return False for invalid addresses."""
        assert is_private_address("not.an.ip") is False


class TestNetworkFirewall:
    """Tests for NetworkFirewall class."""

    def test_allows_loopback_address(self, basic_policy: SecurityPolicy):
        """Should allow loopback addresses."""
        firewall = NetworkFirewall(basic_policy)
        assert firewall.validate_address("127.0.0.1", 8080) is True

    def test_allows_private_network_addresses(self, basic_policy: SecurityPolicy):
        """Should allow addresses in private ranges."""
        firewall = NetworkFirewall(basic_policy)
        assert firewall.validate_address("10.0.0.5", 8080) is True
        assert firewall.validate_address("172.16.1.1", 8080) is True
        assert firewall.validate_address("192.168.1.100", 8080) is True

    def test_blocks_public_addresses_by_default(self, basic_policy: SecurityPolicy):
        """Should block public addresses not in allowlist."""
        firewall = NetworkFirewall(basic_policy)
        with pytest.raises(SecurityError, match="not allowed"):
            firewall.validate_address("8.8.8.8", 443)

    def test_blocks_port_on_blocked_list(self, basic_policy: SecurityPolicy):
        """Should block ports in the blocked list even for local addresses."""
        firewall = NetworkFirewall(basic_policy)
        with pytest.raises(SecurityError, match="port.*blocked"):
            firewall.validate_address("127.0.0.1", 22)

    def test_allows_allowlisted_external_endpoint(self, basic_policy: SecurityPolicy):
        """Should allow explicitly allowlisted external endpoints."""
        firewall = NetworkFirewall(basic_policy)
        # Mock DNS resolution to return a public IP
        with patch.object(firewall, "_resolve_hostname") as mock_resolve:
            mock_resolve.return_value = "52.1.2.3"
            assert firewall.validate_address("api.duckduckgo.com", 443) is True

    def test_blocks_non_allowlisted_port_on_allowlisted_host(self, basic_policy: SecurityPolicy):
        """Should block non-allowlisted ports even on allowlisted hosts."""
        firewall = NetworkFirewall(basic_policy)
        with patch.object(firewall, "_resolve_hostname") as mock_resolve:
            mock_resolve.return_value = "52.1.2.3"
            with pytest.raises(SecurityError, match="not allowed"):
                firewall.validate_address("api.duckduckgo.com", 80)

    def test_blocks_dns_resolution_for_non_allowlisted_hosts(self, basic_policy: SecurityPolicy):
        """Should block DNS resolution for non-allowlisted hostnames."""
        firewall = NetworkFirewall(basic_policy)
        with pytest.raises(SecurityError, match="DNS.*not allowed"):
            firewall.validate_address("evil.com", 443)


class TestNetworkFirewallUrl:
    """Tests for URL validation."""

    def test_validates_local_url(self, basic_policy: SecurityPolicy):
        """Should validate URLs pointing to local addresses."""
        firewall = NetworkFirewall(basic_policy)
        assert firewall.validate_url("http://127.0.0.1:8080/api") is True
        assert firewall.validate_url("http://localhost:3000/") is True

    def test_blocks_external_url(self, basic_policy: SecurityPolicy):
        """Should block URLs pointing to external addresses."""
        firewall = NetworkFirewall(basic_policy)
        with pytest.raises(SecurityError):
            firewall.validate_url("https://evil.com/steal")

    def test_allows_allowlisted_external_url(self, basic_policy: SecurityPolicy):
        """Should allow URLs to allowlisted endpoints."""
        firewall = NetworkFirewall(basic_policy)
        with patch.object(firewall, "_resolve_hostname") as mock_resolve:
            mock_resolve.return_value = "52.1.2.3"
            assert firewall.validate_url("https://api.duckduckgo.com/?q=test") is True

    def test_blocks_url_with_wrong_port(self, basic_policy: SecurityPolicy):
        """Should block allowlisted URLs with wrong port."""
        firewall = NetworkFirewall(basic_policy)
        with patch.object(firewall, "_resolve_hostname") as mock_resolve:
            mock_resolve.return_value = "52.1.2.3"
            with pytest.raises(SecurityError):
                firewall.validate_url("http://api.duckduckgo.com:80/")

    def test_handles_invalid_url(self, basic_policy: SecurityPolicy):
        """Should raise SecurityError for invalid URLs."""
        firewall = NetworkFirewall(basic_policy)
        with pytest.raises(SecurityError, match="Invalid URL"):
            firewall.validate_url("not a valid url")

    def test_extracts_default_ports(self, basic_policy: SecurityPolicy):
        """Should use default ports (80 for http, 443 for https)."""
        firewall = NetworkFirewall(basic_policy)
        with patch.object(firewall, "_resolve_hostname") as mock_resolve:
            mock_resolve.return_value = "52.1.2.3"
            # HTTPS defaults to 443 which is allowed
            assert firewall.validate_url("https://api.duckduckgo.com/") is True


class TestNetworkFirewallDnsPolicy:
    """Tests for DNS resolution policy enforcement."""

    def test_blocks_all_dns_when_disabled(self):
        """Should block all DNS when allow_dns is False."""
        policy = SecurityPolicy.from_dict(
            {
                "version": "1.0",
                "network": {
                    "allowed_ranges": ["127.0.0.0/8"],
                    "allow_dns": False,
                },
            }
        )
        firewall = NetworkFirewall(policy)
        with pytest.raises(SecurityError, match="DNS.*disabled"):
            firewall.validate_address("example.com", 443)

    def test_caches_dns_resolution(self, basic_policy: SecurityPolicy):
        """Should cache DNS resolution results."""
        firewall = NetworkFirewall(basic_policy)
        with patch("socket.getaddrinfo") as mock_getaddr:
            mock_getaddr.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("52.1.2.3", 443))
            ]
            # First call
            try:
                firewall.validate_address("api.duckduckgo.com", 443)
            except SecurityError:
                pass  # May fail for other reasons

            # Second call should use cache
            try:
                firewall.validate_address("api.duckduckgo.com", 443)
            except SecurityError:
                pass

            # Should only have called getaddrinfo once
            assert mock_getaddr.call_count == 1


class TestNetworkFirewallEdgeCases:
    """Edge case tests for NetworkFirewall."""

    def test_handles_dns_resolution_failure(self, basic_policy: SecurityPolicy):
        """Should raise SecurityError on DNS resolution failure."""
        firewall = NetworkFirewall(basic_policy)
        with patch("socket.getaddrinfo") as mock_getaddr:
            mock_getaddr.side_effect = socket.gaierror("DNS lookup failed")
            with pytest.raises(SecurityError, match="DNS resolution failed"):
                firewall.validate_address("api.duckduckgo.com", 443)

    def test_handles_empty_dns_result(self, basic_policy: SecurityPolicy):
        """Should raise SecurityError on empty DNS result."""
        firewall = NetworkFirewall(basic_policy)
        with patch("socket.getaddrinfo") as mock_getaddr:
            mock_getaddr.return_value = []
            with pytest.raises(SecurityError, match="DNS resolution failed"):
                firewall.validate_address("api.duckduckgo.com", 443)

    def test_validates_raw_ip_that_is_not_in_allowed_ranges(self, basic_policy: SecurityPolicy):
        """Should block raw public IP addresses."""
        firewall = NetworkFirewall(basic_policy)
        with pytest.raises(SecurityError, match="not allowed"):
            firewall.validate_address("52.1.2.3", 443)

    def test_handles_unsupported_url_scheme(self, basic_policy: SecurityPolicy):
        """Should reject unsupported URL schemes."""
        firewall = NetworkFirewall(basic_policy)
        with pytest.raises(SecurityError, match="Unsupported URL scheme"):
            firewall.validate_url("ftp://127.0.0.1/file")

    def test_url_without_port_uses_scheme_default(self, basic_policy: SecurityPolicy):
        """Should use scheme default port for http."""
        firewall = NetworkFirewall(basic_policy)
        # HTTP to localhost should work (port 80)
        assert firewall.validate_url("http://127.0.0.1/api") is True

    def test_hostname_in_dns_allowlist_resolving_to_private(self):
        """Should allow hostname in DNS allowlist that resolves to private IP."""
        policy = SecurityPolicy.from_dict(
            {
                "version": "1.0",
                "network": {
                    "allowed_ranges": ["192.168.0.0/16"],
                    "allow_dns": True,
                    "dns_allowlist": ["local.example.com"],
                },
            }
        )
        firewall = NetworkFirewall(policy)
        with patch("socket.getaddrinfo") as mock_getaddr:
            mock_getaddr.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.100", 80))
            ]
            assert firewall.validate_address("local.example.com", 80) is True

    def test_hostname_already_cached(self, basic_policy: SecurityPolicy):
        """Should use cached IP for hostname."""
        firewall = NetworkFirewall(basic_policy)
        # Pre-populate cache
        firewall._dns_cache["api.duckduckgo.com"] = "52.1.2.3"
        # Should use cache and allow (since it's in endpoint allowlist)
        assert firewall.validate_address("api.duckduckgo.com", 443) is True

    def test_resolve_hostname_with_ip_address(self, basic_policy: SecurityPolicy):
        """Should return IP address unchanged when passed to _resolve_hostname."""
        firewall = NetworkFirewall(basic_policy)
        # Directly test _resolve_hostname with an IP
        result = firewall._resolve_hostname("127.0.0.1")
        assert result == "127.0.0.1"

    def test_resolve_hostname_dns_disabled_direct(self):
        """Should raise when DNS is disabled and hostname is passed to _resolve_hostname."""
        policy = SecurityPolicy.from_dict(
            {
                "version": "1.0",
                "network": {
                    "allowed_ranges": ["127.0.0.0/8"],
                    "allow_dns": False,
                },
            }
        )
        firewall = NetworkFirewall(policy)
        with pytest.raises(SecurityError, match="DNS.*disabled"):
            firewall._resolve_hostname("example.com")

    def test_resolve_hostname_not_in_allowlist_direct(self, basic_policy: SecurityPolicy):
        """Should raise when hostname is not in DNS allowlist."""
        firewall = NetworkFirewall(basic_policy)
        with pytest.raises(SecurityError, match="DNS.*not allowed"):
            firewall._resolve_hostname("evil.com")


class TestDnsCacheTTL:
    """Tests for DNS cache TTL behavior [D5]."""

    def test_dns_cache_is_ttl_cache(self, basic_policy: SecurityPolicy):
        """DNS cache should be a TTLCache instance."""
        from cachetools import TTLCache

        firewall = NetworkFirewall(basic_policy)
        assert isinstance(firewall._dns_cache, TTLCache)

    def test_dns_cache_has_max_size(self, basic_policy: SecurityPolicy):
        """DNS cache should have a maximum size to prevent unbounded growth."""
        firewall = NetworkFirewall(basic_policy)
        assert firewall._dns_cache.maxsize <= 1000  # Reasonable limit

    def test_dns_cache_has_ttl(self, basic_policy: SecurityPolicy):
        """DNS cache should have a TTL for entries."""
        firewall = NetworkFirewall(basic_policy)
        assert firewall._dns_cache.ttl > 0
        assert firewall._dns_cache.ttl <= 600  # Max 10 minutes
