"""Tests for RateLimiter component.

These tests define the contract for rate limiting behavior,
extracted from SecurityEngine to follow Single Responsibility Principle.
"""

from __future__ import annotations

import time

import pytest

from src.security.ratelimiter import RateLimiter, RateLimitExceeded


class TestRateLimiterInit:
    """Tests for RateLimiter initialization."""

    def test_creates_with_default_window(self) -> None:
        """RateLimiter uses 60s window by default."""
        limiter = RateLimiter()
        assert limiter.window_seconds == 60.0

    def test_creates_with_custom_window(self) -> None:
        """RateLimiter accepts custom window size."""
        limiter = RateLimiter(window_seconds=30.0)
        assert limiter.window_seconds == 30.0

    def test_rejects_zero_window(self) -> None:
        """RateLimiter rejects zero window size."""
        with pytest.raises(ValueError, match="window_seconds must be positive"):
            RateLimiter(window_seconds=0)

    def test_rejects_negative_window(self) -> None:
        """RateLimiter rejects negative window size."""
        with pytest.raises(ValueError, match="window_seconds must be positive"):
            RateLimiter(window_seconds=-1.0)


class TestRateLimiterCheck:
    """Tests for check_rate_limit method."""

    def test_allows_first_request(self) -> None:
        """First request is always allowed."""
        limiter = RateLimiter()
        # Should not raise
        limiter.check_rate_limit("test_tool", limit=10)

    def test_allows_requests_under_limit(self) -> None:
        """Requests under the limit are allowed."""
        limiter = RateLimiter()
        for _ in range(5):
            limiter.check_rate_limit("test_tool", limit=10)
        # All 5 should succeed without raising

    def test_allows_exactly_at_limit(self) -> None:
        """Exactly limit number of requests are allowed."""
        limiter = RateLimiter()
        for _ in range(10):
            limiter.check_rate_limit("test_tool", limit=10)
        # All 10 should succeed

    def test_blocks_over_limit(self) -> None:
        """Request over limit raises RateLimitExceeded."""
        limiter = RateLimiter(window_seconds=60.0)
        for _ in range(10):
            limiter.check_rate_limit("test_tool", limit=10)

        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check_rate_limit("test_tool", limit=10)

        assert "test_tool" in str(exc_info.value)
        assert "10" in str(exc_info.value)

    def test_tracks_tools_independently(self) -> None:
        """Each tool has its own rate limit bucket."""
        limiter = RateLimiter()

        # Max out tool_a
        for _ in range(5):
            limiter.check_rate_limit("tool_a", limit=5)

        # tool_b should still work
        limiter.check_rate_limit("tool_b", limit=5)

        # tool_a should be blocked
        with pytest.raises(RateLimitExceeded):
            limiter.check_rate_limit("tool_a", limit=5)


class TestRateLimiterWindowExpiry:
    """Tests for rate limit window expiry behavior."""

    def test_allows_after_window_expires(self) -> None:
        """Requests allowed after window expires."""
        limiter = RateLimiter(window_seconds=1.0)

        # Max out the limit
        for _ in range(3):
            limiter.check_rate_limit("test_tool", limit=3)

        # Should be blocked
        with pytest.raises(RateLimitExceeded):
            limiter.check_rate_limit("test_tool", limit=3)

        # Wait for window to expire
        time.sleep(1.1)

        # Should work again
        limiter.check_rate_limit("test_tool", limit=3)

    def test_cleans_old_entries_on_check(self) -> None:
        """Old entries are cleaned when checking rate limit."""
        limiter = RateLimiter(window_seconds=0.5)

        # Make some requests
        limiter.check_rate_limit("test_tool", limit=10)
        limiter.check_rate_limit("test_tool", limit=10)

        # Wait for window to expire
        time.sleep(0.6)

        # Check count - should be 1 (this new request only)
        limiter.check_rate_limit("test_tool", limit=10)
        assert limiter.get_request_count("test_tool") == 1


class TestRateLimiterReset:
    """Tests for reset functionality."""

    def test_reset_clears_all_buckets(self) -> None:
        """Reset clears all rate limit buckets."""
        limiter = RateLimiter()

        limiter.check_rate_limit("tool_a", limit=10)
        limiter.check_rate_limit("tool_b", limit=10)

        limiter.reset()

        assert limiter.get_request_count("tool_a") == 0
        assert limiter.get_request_count("tool_b") == 0

    def test_reset_single_tool(self) -> None:
        """Reset can clear a single tool's bucket."""
        limiter = RateLimiter()

        limiter.check_rate_limit("tool_a", limit=10)
        limiter.check_rate_limit("tool_b", limit=10)

        limiter.reset(tool_name="tool_a")

        assert limiter.get_request_count("tool_a") == 0
        assert limiter.get_request_count("tool_b") == 1


class TestRateLimiterRequestCount:
    """Tests for get_request_count method."""

    def test_returns_zero_for_unknown_tool(self) -> None:
        """Unknown tool returns zero count."""
        limiter = RateLimiter()
        assert limiter.get_request_count("unknown") == 0

    def test_returns_current_count(self) -> None:
        """Returns accurate count of requests in window."""
        limiter = RateLimiter()

        limiter.check_rate_limit("test_tool", limit=10)
        limiter.check_rate_limit("test_tool", limit=10)
        limiter.check_rate_limit("test_tool", limit=10)

        assert limiter.get_request_count("test_tool") == 3
