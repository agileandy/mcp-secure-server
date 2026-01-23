"""Tests for progressive disclosure enhancements.

P0: Environment-aware tool filtering (is_available, availability_hint)
P1: Semantic/alias search (aliases, intent_categories)
"""

from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import patch

import pytest

from src.plugins.base import PluginBase, ToolDefinition, ToolResult
from src.plugins.discovery import ToolDiscoveryPlugin
from src.plugins.dispatcher import ToolDispatcher

# =============================================================================
# P0: Environment-Aware Tool Filtering Tests
# =============================================================================


class TestPluginBaseAvailability:
    """Tests for PluginBase is_available and availability_hint methods."""

    def test_is_available_default_returns_true(self):
        """Default is_available should return True for plugins without requirements."""

        class SimplePlugin(PluginBase):
            @property
            def name(self) -> str:
                return "simple"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return []

            def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
                return ToolResult(content=[{"type": "text", "text": "ok"}])

        plugin = SimplePlugin()
        assert plugin.is_available() is True

    def test_availability_hint_default_returns_empty_string(self):
        """Default availability_hint should return empty string."""

        class SimplePlugin(PluginBase):
            @property
            def name(self) -> str:
                return "simple"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return []

            def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
                return ToolResult(content=[{"type": "text", "text": "ok"}])

        plugin = SimplePlugin()
        assert plugin.availability_hint() == ""

    def test_plugin_can_override_is_available(self):
        """Plugins should be able to override is_available to check requirements."""

        class EnvRequiredPlugin(PluginBase):
            @property
            def name(self) -> str:
                return "env_required"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return []

            def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
                return ToolResult(content=[{"type": "text", "text": "ok"}])

            def is_available(self) -> bool:
                return os.environ.get("REQUIRED_TOKEN") is not None

            def availability_hint(self) -> str:
                return "Set REQUIRED_TOKEN environment variable to enable this plugin."

        plugin = EnvRequiredPlugin()

        # Without env var
        with patch.dict(os.environ, {}, clear=True):
            assert plugin.is_available() is False
            assert "REQUIRED_TOKEN" in plugin.availability_hint()

        # With env var
        with patch.dict(os.environ, {"REQUIRED_TOKEN": "secret"}):
            assert plugin.is_available() is True


class TestSearchToolsAvailabilityFiltering:
    """Tests for availability filtering in search_tools."""

    @pytest.fixture
    def dispatcher_with_unavailable_plugin(self):
        """Create dispatcher with an available and unavailable plugin."""
        dispatcher = ToolDispatcher()

        class AvailablePlugin(PluginBase):
            @property
            def name(self) -> str:
                return "available"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return [
                    ToolDefinition(
                        name="available_tool",
                        description="This tool is always available",
                        input_schema={"type": "object", "properties": {}},
                    )
                ]

            def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
                return ToolResult(content=[{"type": "text", "text": "ok"}])

            def is_available(self) -> bool:
                return True

        class UnavailablePlugin(PluginBase):
            @property
            def name(self) -> str:
                return "unavailable"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return [
                    ToolDefinition(
                        name="unavailable_tool",
                        description="This tool requires an API key",
                        input_schema={"type": "object", "properties": {}},
                    )
                ]

            def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
                return ToolResult(content=[{"type": "text", "text": "ok"}])

            def is_available(self) -> bool:
                return False

            def availability_hint(self) -> str:
                return "Set API_KEY to enable this plugin."

        dispatcher.register_plugin(AvailablePlugin())
        dispatcher.register_plugin(UnavailablePlugin())
        return dispatcher

    def test_search_tools_filters_unavailable_by_default(self, dispatcher_with_unavailable_plugin):
        """By default, search_tools should not return unavailable plugins' tools."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_unavailable_plugin)
        result = plugin.execute("search_tools", {"detail_level": "name"})

        assert result.is_error is False
        tools = json.loads(result.content[0]["text"])
        assert "available_tool" in tools
        assert "unavailable_tool" not in tools

    def test_search_tools_includes_unavailable_when_requested(
        self, dispatcher_with_unavailable_plugin
    ):
        """search_tools should include unavailable tools when include_unavailable=True."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_unavailable_plugin)
        result = plugin.execute(
            "search_tools", {"detail_level": "name", "include_unavailable": True}
        )

        assert result.is_error is False
        tools = json.loads(result.content[0]["text"])
        assert "available_tool" in tools
        assert "unavailable_tool" in tools

    def test_search_tools_shows_availability_status_when_including_unavailable(
        self, dispatcher_with_unavailable_plugin
    ):
        """When including unavailable tools, should show availability status."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_unavailable_plugin)
        result = plugin.execute(
            "search_tools", {"detail_level": "summary", "include_unavailable": True}
        )

        assert result.is_error is False
        tools = json.loads(result.content[0]["text"])

        available_tool = next(t for t in tools if t["name"] == "available_tool")
        unavailable_tool = next(t for t in tools if t["name"] == "unavailable_tool")

        assert available_tool.get("available") is True
        assert unavailable_tool.get("available") is False
        assert "API_KEY" in unavailable_tool.get("availability_hint", "")


class TestListCategoriesAvailability:
    """Tests for availability info in list_categories."""

    @pytest.fixture
    def dispatcher_with_mixed_availability(self):
        """Create dispatcher with plugins of different availability."""
        dispatcher = ToolDispatcher()

        class AvailablePlugin(PluginBase):
            @property
            def name(self) -> str:
                return "available"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return [
                    ToolDefinition(
                        name="tool1",
                        description="Tool 1",
                        input_schema={"type": "object"},
                    )
                ]

            def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
                return ToolResult(content=[{"type": "text", "text": "ok"}])

            def is_available(self) -> bool:
                return True

        class UnavailablePlugin(PluginBase):
            @property
            def name(self) -> str:
                return "unavailable"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return [
                    ToolDefinition(
                        name="tool2",
                        description="Tool 2",
                        input_schema={"type": "object"},
                    )
                ]

            def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
                return ToolResult(content=[{"type": "text", "text": "ok"}])

            def is_available(self) -> bool:
                return False

            def availability_hint(self) -> str:
                return "Missing configuration."

        dispatcher.register_plugin(AvailablePlugin())
        dispatcher.register_plugin(UnavailablePlugin())
        return dispatcher

    def test_list_categories_includes_availability(self, dispatcher_with_mixed_availability):
        """list_categories should include availability status for each category."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_mixed_availability)
        result = plugin.execute("list_categories", {})

        assert result.is_error is False
        categories = json.loads(result.content[0]["text"])

        available_cat = next(c for c in categories if c["category"] == "available")
        unavailable_cat = next(c for c in categories if c["category"] == "unavailable")

        assert available_cat.get("available") is True
        assert unavailable_cat.get("available") is False
        assert "Missing configuration" in unavailable_cat.get("availability_hint", "")
