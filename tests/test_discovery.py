"""Tests for tool discovery plugin."""

from __future__ import annotations

import json

import pytest

from src.plugins.base import PluginBase, ToolDefinition, ToolResult
from src.plugins.discovery import ToolDiscoveryPlugin
from src.plugins.dispatcher import ToolDispatcher


class TestToolDiscoveryPluginInterface:
    """Tests for ToolDiscoveryPlugin interface compliance."""

    def test_implements_plugin_interface(self):
        """Should implement PluginBase interface."""
        dispatcher = ToolDispatcher()
        plugin = ToolDiscoveryPlugin(dispatcher)
        assert isinstance(plugin, PluginBase)

    def test_has_name(self):
        """Should have plugin name."""
        dispatcher = ToolDispatcher()
        plugin = ToolDiscoveryPlugin(dispatcher)
        assert plugin.name == "discovery"

    def test_has_version(self):
        """Should have plugin version."""
        dispatcher = ToolDispatcher()
        plugin = ToolDiscoveryPlugin(dispatcher)
        assert plugin.version == "1.0.0"

    def test_provides_two_tools(self):
        """Should provide search_tools and list_categories tools."""
        dispatcher = ToolDispatcher()
        plugin = ToolDiscoveryPlugin(dispatcher)
        tools = plugin.get_tools()

        assert len(tools) == 2
        tool_names = {t.name for t in tools}
        assert "search_tools" in tool_names
        assert "list_categories" in tool_names


class TestSearchToolsTool:
    """Tests for the search_tools tool."""

    @pytest.fixture
    def dispatcher_with_plugins(self):
        """Create dispatcher with mock plugins for testing."""
        dispatcher = ToolDispatcher()

        # Create a mock plugin
        class MockPlugin(PluginBase):
            @property
            def name(self) -> str:
                return "mock"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return [
                    ToolDefinition(
                        name="mock_tool",
                        description="A mock tool for testing",
                        input_schema={"type": "object", "properties": {"arg": {"type": "string"}}},
                    ),
                    ToolDefinition(
                        name="another_mock",
                        description="Another mock tool",
                        input_schema={"type": "object", "properties": {}},
                    ),
                ]

            def execute(self, tool_name: str, arguments: dict) -> ToolResult:
                return ToolResult(content=[{"type": "text", "text": "ok"}])

        dispatcher.register_plugin(MockPlugin())
        return dispatcher

    def test_search_tools_returns_all_with_no_filter(self, dispatcher_with_plugins):
        """Should return all tools when no query or category specified."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_plugins)
        result = plugin.execute("search_tools", {})

        assert result.is_error is False
        tools = json.loads(result.content[0]["text"])
        # Should include discovery plugin's own tools plus mock tools
        assert len(tools) >= 2

    def test_search_tools_detail_level_name(self, dispatcher_with_plugins):
        """Should return only names at detail_level='name'."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_plugins)
        dispatcher_with_plugins.register_plugin(plugin)
        result = plugin.execute("search_tools", {"detail_level": "name"})

        assert result.is_error is False
        tools = json.loads(result.content[0]["text"])
        # Should be list of strings
        assert all(isinstance(t, str) for t in tools)
        assert "mock_tool" in tools

    def test_search_tools_detail_level_summary(self, dispatcher_with_plugins):
        """Should return name and description at detail_level='summary'."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_plugins)
        dispatcher_with_plugins.register_plugin(plugin)
        result = plugin.execute("search_tools", {"detail_level": "summary"})

        assert result.is_error is False
        tools = json.loads(result.content[0]["text"])
        # Should be list of dicts with name and description
        assert all(isinstance(t, dict) for t in tools)
        mock_tool = next(t for t in tools if t["name"] == "mock_tool")
        assert "name" in mock_tool
        assert "description" in mock_tool
        assert "input_schema" not in mock_tool

    def test_search_tools_detail_level_full(self, dispatcher_with_plugins):
        """Should return full definition at detail_level='full'."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_plugins)
        dispatcher_with_plugins.register_plugin(plugin)
        result = plugin.execute("search_tools", {"detail_level": "full"})

        assert result.is_error is False
        tools = json.loads(result.content[0]["text"])
        mock_tool = next(t for t in tools if t["name"] == "mock_tool")
        assert "name" in mock_tool
        assert "description" in mock_tool
        assert "inputSchema" in mock_tool

    def test_search_tools_filters_by_query(self, dispatcher_with_plugins):
        """Should filter tools by query keyword."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_plugins)
        dispatcher_with_plugins.register_plugin(plugin)
        result = plugin.execute("search_tools", {"query": "another"})

        assert result.is_error is False
        tools = json.loads(result.content[0]["text"])
        # Default detail level is summary
        tool_names = [t["name"] for t in tools]
        assert "another_mock" in tool_names
        assert "mock_tool" not in tool_names

    def test_search_tools_filters_by_category(self, dispatcher_with_plugins):
        """Should filter tools by category (plugin name)."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_plugins)
        dispatcher_with_plugins.register_plugin(plugin)
        result = plugin.execute("search_tools", {"category": "mock"})

        assert result.is_error is False
        tools = json.loads(result.content[0]["text"])
        tool_names = [t["name"] for t in tools]
        assert "mock_tool" in tool_names
        assert "another_mock" in tool_names
        # Should not include discovery tools
        assert "search_tools" not in tool_names
        assert "list_categories" not in tool_names

    def test_search_tools_query_case_insensitive(self, dispatcher_with_plugins):
        """Should search case-insensitively."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_plugins)
        dispatcher_with_plugins.register_plugin(plugin)
        result = plugin.execute("search_tools", {"query": "MOCK"})

        assert result.is_error is False
        tools = json.loads(result.content[0]["text"])
        assert len(tools) >= 2  # Should find mock_tool and another_mock

    def test_search_tools_unknown_tool_returns_error(self, dispatcher_with_plugins):
        """Should return error for unknown tool name."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_plugins)
        result = plugin.execute("unknown_tool", {})

        assert result.is_error is True


class TestListCategoriesTool:
    """Tests for the list_categories tool."""

    @pytest.fixture
    def dispatcher_with_plugins(self):
        """Create dispatcher with mock plugins for testing."""
        dispatcher = ToolDispatcher()

        class MockPlugin(PluginBase):
            @property
            def name(self) -> str:
                return "mock"

            @property
            def version(self) -> str:
                return "2.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return [
                    ToolDefinition(
                        name="tool1",
                        description="First tool",
                        input_schema={"type": "object"},
                    ),
                    ToolDefinition(
                        name="tool2",
                        description="Second tool",
                        input_schema={"type": "object"},
                    ),
                ]

            def execute(self, tool_name: str, arguments: dict) -> ToolResult:
                return ToolResult(content=[{"type": "text", "text": "ok"}])

        dispatcher.register_plugin(MockPlugin())
        return dispatcher

    def test_list_categories_returns_plugins(self, dispatcher_with_plugins):
        """Should return list of plugin categories."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_plugins)
        dispatcher_with_plugins.register_plugin(plugin)
        result = plugin.execute("list_categories", {})

        assert result.is_error is False
        categories = json.loads(result.content[0]["text"])
        assert isinstance(categories, list)
        assert len(categories) >= 1

    def test_list_categories_includes_tool_count(self, dispatcher_with_plugins):
        """Should include tool count for each category."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_plugins)
        dispatcher_with_plugins.register_plugin(plugin)
        result = plugin.execute("list_categories", {})

        categories = json.loads(result.content[0]["text"])
        mock_cat = next(c for c in categories if c["category"] == "mock")
        assert mock_cat["tool_count"] == 2

    def test_list_categories_includes_version(self, dispatcher_with_plugins):
        """Should include plugin version."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_plugins)
        dispatcher_with_plugins.register_plugin(plugin)
        result = plugin.execute("list_categories", {})

        categories = json.loads(result.content[0]["text"])
        mock_cat = next(c for c in categories if c["category"] == "mock")
        assert mock_cat["version"] == "2.0.0"

    def test_list_categories_includes_tool_names(self, dispatcher_with_plugins):
        """Should include list of tool names for each category."""
        plugin = ToolDiscoveryPlugin(dispatcher_with_plugins)
        dispatcher_with_plugins.register_plugin(plugin)
        result = plugin.execute("list_categories", {})

        categories = json.loads(result.content[0]["text"])
        mock_cat = next(c for c in categories if c["category"] == "mock")
        assert "tools" in mock_cat
        assert "tool1" in mock_cat["tools"]
        assert "tool2" in mock_cat["tools"]
