"""Custom exceptions for figma-stories-plugin.

This module defines custom exception classes for error handling
throughout the plugin.
"""

from __future__ import annotations


class FigmaStoriesError(Exception):
    """Base exception for figma-stories-plugin."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(FigmaStoriesError):
    """Raised when configuration is invalid or missing."""

    pass


class FigmaAPIError(FigmaStoriesError):
    """Raised when Figma API request fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(message, details)
        self.status_code = status_code
        self.error_code = error_code


class FigmaAuthenticationError(FigmaAPIError):
    """Raised when Figma authentication fails."""

    def __init__(self, message: str = "Figma authentication failed"):
        super().__init__(message, status_code=401, error_code="authentication_failed")


class FigmaRateLimitError(FigmaAPIError):
    """Raised when Figma API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Figma API rate limit exceeded",
        retry_after: int | None = None,
    ):
        super().__init__(message, status_code=429, error_code="rate_limited")
        self.retry_after = retry_after


class FigmaFileNotFoundError(FigmaAPIError):
    """Raised when Figma file is not found."""

    def __init__(self, file_key: str):
        super().__init__(
            f"Figma file not found: {file_key}",
            status_code=404,
            error_code="file_not_found",
            details={"file_key": file_key},
        )


class AIError(FigmaStoriesError):
    """Raised when AI API request fails."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        status_code: int | None = None,
        details: dict | None = None,
    ):
        super().__init__(message, details)
        self.provider = provider
        self.status_code = status_code


class AIAuthenticationError(AIError):
    """Raised when AI API authentication fails."""

    def __init__(self, provider: str = "unknown"):
        super().__init__(
            f"{provider} authentication failed",
            provider=provider,
            status_code=401,
        )


class AIRateLimitError(AIError):
    """Raised when AI API rate limit is exceeded."""

    def __init__(
        self,
        provider: str = "unknown",
        retry_after: int | None = None,
    ):
        super().__init__(
            f"{provider} rate limit exceeded",
            provider=provider,
            status_code=429,
            details={"retry_after": retry_after},
        )
        self.retry_after = retry_after


class GenerationError(FigmaStoriesError):
    """Raised when story generation fails."""

    pass


class OutputError(FigmaStoriesError):
    """Raised when file output operations fail."""

    pass


class SecurityError(FigmaStoriesError):
    """Raised when security policy is violated."""

    pass


class ValidationError(FigmaStoriesError):
    """Raised when input validation fails."""

    pass
