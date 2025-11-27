"""Pytest configuration and fixtures for bugtracker tests."""

from pathlib import Path

import pytest


@pytest.fixture
def global_db_path(tmp_path: Path, monkeypatch):
    """Set up a temporary global database for tests.

    This redirects the global database to a temp directory
    so tests don't pollute the real ~/.mcp-bugtracker/ location.
    """
    test_home = tmp_path / "home"
    test_home.mkdir()
    monkeypatch.setenv("HOME", str(test_home))

    yield test_home / ".mcp-bugtracker" / "bugs.db"


@pytest.fixture
def project_path(tmp_path: Path, monkeypatch):
    """Create a temporary project directory and set it as MCP_PROJECT_PATH.

    Returns the project path for use in tests.
    """
    project = tmp_path / "test-project"
    project.mkdir()
    monkeypatch.setenv("MCP_PROJECT_PATH", str(project))

    yield project
