"""Rate limiting component for security engine.

Provides standalone rate limiting functionality that can be used
by SecurityEngine or other components requiring request throttling.
"""

from __future__ import annotations

import time
from collections import defaultdict


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    pass


class RateLimiter:
    """Sliding window rate limiter for tool invocations.

    Tracks request timestamps per tool and enforces configurable
    rate limits within a sliding time window.

    Example:
        limiter = RateLimiter(window_seconds=60.0)
        try:
            limiter.check_rate_limit("my_tool", limit=10)
        except RateLimitExceeded:
            print("Too many requests!")
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        """Initialize the rate limiter.

        Args:
            window_seconds: Size of the sliding window in seconds.

        Raises:
            ValueError: If window_seconds is not positive.
        """
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self._window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    @property
    def window_seconds(self) -> float:
        """Get the window size in seconds."""
        return self._window_seconds

    def check_rate_limit(self, tool_name: str, limit: int) -> None:
        """Check if a tool invocation is within rate limits.

        Records the request if allowed.

        Args:
            tool_name: Name of the tool being invoked.
            limit: Maximum requests allowed in the window.

        Raises:
            RateLimitExceeded: If the rate limit has been exceeded.
        """
        now = time.time()
        window_start = now - self._window_seconds

        # Clean old entries outside the window
        bucket = self._buckets[tool_name]
        self._buckets[tool_name] = [t for t in bucket if t > window_start]

        # Check if limit would be exceeded
        if len(self._buckets[tool_name]) >= limit:
            raise RateLimitExceeded(
                f"Rate limit exceeded for {tool_name}: {limit} requests per {self._window_seconds}s"
            )

        # Record this request
        self._buckets[tool_name].append(now)

    def get_request_count(self, tool_name: str) -> int:
        """Get the current request count for a tool within the window.

        Args:
            tool_name: Name of the tool.

        Returns:
            Number of requests in the current window.
        """
        now = time.time()
        window_start = now - self._window_seconds

        # Clean and count
        bucket = self._buckets.get(tool_name, [])
        return len([t for t in bucket if t > window_start])

    def reset(self, tool_name: str | None = None) -> None:
        """Reset rate limit buckets.

        Args:
            tool_name: If provided, only reset this tool's bucket.
                      If None, reset all buckets.
        """
        if tool_name is not None:
            self._buckets[tool_name] = []
        else:
            self._buckets.clear()
