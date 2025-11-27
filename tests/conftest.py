"""Pytest configuration and fixtures for bugtracker tests."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def allow_tmp_path_for_bugtracker(tmp_path: Path, request):
    """Automatically allow tmp_path for BugTrackerPlugin in most tests.

    This fixture sets the allowed_root to "/" to disable path traversal
    checks for tests that don't specifically test path validation.

    Tests in TestPathTraversalProtection are excluded from this fixture
    so they can test the actual path validation behavior.
    """
    # Skip for path traversal tests - they need real path validation
    if "TestPathTraversalProtection" in str(request.node.nodeid):
        yield
        return

    # For all other tests, allow any path (disable path traversal check)
    from src.plugins.bugtracker import BugTrackerPlugin

    original_root = BugTrackerPlugin.allowed_root
    BugTrackerPlugin.allowed_root = Path("/")

    yield

    # Restore original setting
    BugTrackerPlugin.allowed_root = original_root
