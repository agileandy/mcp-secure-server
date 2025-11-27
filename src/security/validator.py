"""Input validation and sanitization for tool arguments.

Provides schema-based validation and security-focused sanitization
for all tool inputs before execution.
"""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

if TYPE_CHECKING:
    from src.security.policy import SecurityPolicy


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass


# Shell metacharacters that could enable command injection
SHELL_METACHARACTERS = re.compile(r"[;&|`$(){}]")

# Patterns that indicate command chaining/substitution
DANGEROUS_PATTERNS = [
    re.compile(r";\s*"),  # Command chaining
    re.compile(r"\|\s*"),  # Pipes
    re.compile(r"&&"),  # AND chaining
    re.compile(r"\|\|"),  # OR chaining
    re.compile(r"`[^`]*`"),  # Backtick substitution
    re.compile(r"\$\([^)]*\)"),  # $() substitution
    re.compile(r"\$\{[^}]*\}"),  # ${} substitution
]


def sanitize_path(path: str, base_path: str | None = None) -> str:
    """Sanitize and resolve a file path.

    Args:
        path: Path to sanitize.
        base_path: Optional base path for resolving relative paths.

    Returns:
        Sanitized absolute path.

    Raises:
        ValidationError: If the path is invalid or contains traversal.
    """
    # Check for null bytes
    if "\x00" in path:
        raise ValidationError("Path contains null bytes")

    # Expand home directory
    if path.startswith("~"):
        path = os.path.expanduser(path)

    # Resolve to absolute path
    if base_path and not os.path.isabs(path):
        resolved = Path(base_path) / path
    else:
        resolved = Path(path)

    try:
        # Resolve symlinks and normalize
        resolved = resolved.resolve()
    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid path: {e}") from e

    # Check for path traversal after resolution
    if base_path:
        base_resolved = Path(base_path).resolve()
        try:
            resolved.relative_to(base_resolved)
        except ValueError:
            raise ValidationError(f"Path traversal detected: {path} escapes {base_path}") from None

    return str(resolved)


def sanitize_command(command: str) -> str:
    """Sanitize a shell command.

    Args:
        command: Command to sanitize.

    Returns:
        Sanitized command.

    Raises:
        ValidationError: If the command contains dangerous patterns.
    """
    command = command.strip()

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(command):
            raise ValidationError(
                f"Command contains blocked metacharacter/pattern: {pattern.pattern}"
            )

    return command


class InputValidator:
    """Validates and sanitizes tool inputs.

    Combines JSON Schema validation with security-focused
    sanitization for paths, commands, and other sensitive inputs.
    """

    def __init__(
        self,
        policy: SecurityPolicy,
        max_string_length: int = 10000,
    ) -> None:
        """Initialize the validator.

        Args:
            policy: Security policy to enforce.
            max_string_length: Maximum allowed string length.
        """
        self._policy = policy
        self._max_string_length = max_string_length

        # Pre-resolve allowed paths patterns for proper matching
        self._resolved_allowed_paths: list[str] = []
        for pattern in policy.filesystem_allowed_paths:
            # Extract the base path (before any glob patterns)
            if "**" in pattern:
                base, _, suffix = pattern.partition("**")
                try:
                    resolved_base = str(Path(base.rstrip("/")).resolve())
                    self._resolved_allowed_paths.append(resolved_base + "/**" + suffix)
                except (OSError, ValueError):
                    self._resolved_allowed_paths.append(pattern)
            else:
                try:
                    self._resolved_allowed_paths.append(str(Path(pattern).resolve()))
                except (OSError, ValueError):
                    self._resolved_allowed_paths.append(pattern)

    def _is_path_allowed(self, path: str) -> bool:
        """Check if a path is in the allowed list."""
        for pattern in self._resolved_allowed_paths:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False

    def _is_path_denied(self, path: str) -> bool:
        """Check if a path matches a denied pattern."""
        for pattern in self._policy.filesystem_denied_paths:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False

    def _is_command_blocked(self, command: str) -> bool:
        """Check if a command is in the blocked list."""
        # Extract the base command (first word)
        base_command = command.split()[0] if command.split() else ""

        for blocked in self._policy.commands_blocked:
            # Check if it's a full command or just the base
            if blocked in command or base_command == blocked:
                return True
        return False

    def _validate_string_length(self, value: str, field: str) -> None:
        """Validate string length."""
        if len(value) > self._max_string_length:
            raise ValidationError(
                f"Field '{field}' exceeds maximum length of {self._max_string_length}"
            )

    def _validate_path_field(self, path: str) -> str:
        """Validate and sanitize a path field."""
        # Sanitize first
        sanitized = sanitize_path(path)

        # Check denied patterns first (they take precedence)
        if self._is_path_denied(sanitized):
            raise ValidationError(f"Path is denied by policy: {sanitized}")

        # Check if in allowed paths
        if self._policy.filesystem_allowed_paths and not self._is_path_allowed(sanitized):
            raise ValidationError(f"Path is not in allowed directories: {sanitized}")

        return sanitized

    def _validate_command_field(self, command: str) -> str:
        """Validate and sanitize a command field."""
        # Sanitize first (checks for metacharacters)
        sanitized = sanitize_command(command)

        # Check blocked commands
        if self._is_command_blocked(sanitized):
            raise ValidationError(f"Command is blocked by policy: {command}")

        return sanitized

    def _process_value(self, value: Any, schema: dict[str, Any], field_name: str) -> Any:
        """Process and validate a single value based on schema."""
        if isinstance(value, str):
            self._validate_string_length(value, field_name)

            # Check for format-specific validation
            format_type = schema.get("format")
            if format_type == "path":
                return self._validate_path_field(value)
            elif format_type == "command":
                return self._validate_command_field(value)

        return value

    def _process_arguments(
        self, arguments: dict[str, Any], schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Process and validate all arguments."""
        result = {}
        properties = schema.get("properties", {})

        for key, value in arguments.items():
            prop_schema = properties.get(key, {})

            if isinstance(value, dict) and prop_schema.get("type") == "object":
                # Recursively process nested objects
                result[key] = self._process_arguments(value, prop_schema)
            elif isinstance(value, list):
                # Process array items
                items_schema = prop_schema.get("items", {})
                result[key] = [
                    self._process_value(item, items_schema, f"{key}[{i}]")
                    for i, item in enumerate(value)
                ]
            else:
                result[key] = self._process_value(value, prop_schema, key)

        return result

    def validate_tool_input(
        self, tool_name: str, schema: dict[str, Any], arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate and sanitize tool input.

        Args:
            tool_name: Name of the tool (for error messages).
            schema: JSON Schema for the tool's input.
            arguments: Arguments to validate.

        Returns:
            Validated and sanitized arguments.

        Raises:
            ValidationError: If validation fails.
        """
        # First, validate against JSON Schema
        try:
            validator = Draft202012Validator(schema)
            errors = list(validator.iter_errors(arguments))
            if errors:
                # Report first error
                error = errors[0]
                path = ".".join(str(p) for p in error.path) if error.path else "root"
                raise ValidationError(f"Schema validation failed at '{path}': {error.message}")
        except SchemaError as e:
            raise ValidationError(f"Invalid schema for tool {tool_name}: {e}") from e

        # Then apply security-focused processing
        return self._process_arguments(arguments, schema)
