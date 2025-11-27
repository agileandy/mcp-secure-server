"""Tests for plugin system - base class, loader, and dispatcher."""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.plugins.base import PluginBase, ToolDefinition, ToolResult
from src.plugins.dispatcher import ToolDispatcher, ToolExecutionError, ToolNotFoundError
from src.plugins.loader import PluginLoader


class MockPlugin(PluginBase):
    """Mock plugin for testing."""

    @property
    def name(self) -> str:
        return "mock_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="echo",
                description="Echoes back the input",
                input_schema={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                    },
                    "required": ["message"],
                },
            ),
            ToolDefinition(
                name="add",
                description="Adds two numbers",
                input_schema={
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"},
                    },
                    "required": ["a", "b"],
                },
            ),
        ]

    def execute(self, tool_name: str, arguments: dict) -> ToolResult:
        if tool_name == "echo":
            return ToolResult(content=[{"type": "text", "text": arguments["message"]}])
        elif tool_name == "add":
            result = arguments["a"] + arguments["b"]
            return ToolResult(content=[{"type": "text", "text": str(result)}])
        else:
            return ToolResult(
                content=[{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                is_error=True,
            )


class TestToolDefinition:
    """Tests for ToolDefinition dataclass."""

    def test_creates_tool_definition(self):
        """Should create tool definition with required fields."""
        tool = ToolDefinition(
            name="test",
            description="Test tool",
            input_schema={"type": "object"},
        )
        assert tool.name == "test"
        assert tool.description == "Test tool"

    def test_converts_to_dict(self):
        """Should convert to MCP tool format."""
        tool = ToolDefinition(
            name="search",
            description="Search the web",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        )
        d = tool.to_dict()

        assert d["name"] == "search"
        assert d["description"] == "Search the web"
        assert "inputSchema" in d


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_creates_success_result(self):
        """Should create successful result."""
        result = ToolResult(content=[{"type": "text", "text": "Success"}])
        assert result.is_error is False
        assert len(result.content) == 1

    def test_creates_error_result(self):
        """Should create error result."""
        result = ToolResult(
            content=[{"type": "text", "text": "Error occurred"}],
            is_error=True,
        )
        assert result.is_error is True

    def test_converts_to_dict(self):
        """Should convert to MCP result format."""
        result = ToolResult(content=[{"type": "text", "text": "Hello"}])
        d = result.to_dict()

        assert "content" in d
        assert d["isError"] is False


class TestPluginBase:
    """Tests for PluginBase abstract class."""

    def test_mock_plugin_implements_interface(self):
        """Should be able to implement PluginBase."""
        plugin = MockPlugin()

        assert plugin.name == "mock_plugin"
        assert plugin.version == "1.0.0"
        assert len(plugin.get_tools()) == 2

    def test_mock_plugin_executes_tool(self):
        """Should execute tools correctly."""
        plugin = MockPlugin()

        result = plugin.execute("echo", {"message": "Hello"})
        assert result.content[0]["text"] == "Hello"

        result = plugin.execute("add", {"a": 2, "b": 3})
        assert result.content[0]["text"] == "5"


class TestPluginLoader:
    """Tests for PluginLoader class."""

    def test_discovers_plugins_in_directory(self):
        """Should discover plugins with manifest.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a plugin directory
            plugin_dir = Path(tmpdir) / "test_plugin"
            plugin_dir.mkdir()

            # Create manifest
            manifest = {
                "name": "test_plugin",
                "version": "1.0.0",
                "description": "Test plugin",
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {"type": "object"},
                    },
                ],
            }
            with open(plugin_dir / "manifest.yaml", "w") as f:
                yaml.dump(manifest, f)

            # Create handler.py
            handler_code = """
from src.plugins.base import PluginBase, ToolDefinition, ToolResult

class Plugin(PluginBase):
    @property
    def name(self) -> str:
        return "test_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        return [ToolDefinition(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"},
        )]

    def execute(self, tool_name: str, arguments: dict) -> ToolResult:
        return ToolResult(content=[{"type": "text", "text": "test"}])
"""
            with open(plugin_dir / "handler.py", "w") as f:
                f.write(handler_code)

            loader = PluginLoader(Path(tmpdir))
            plugins = loader.discover_plugins()

            assert len(plugins) == 1
            assert plugins[0].name == "test_plugin"

    def test_skips_directories_without_manifest(self):
        """Should skip directories without manifest.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directory without manifest
            (Path(tmpdir) / "not_a_plugin").mkdir()

            loader = PluginLoader(Path(tmpdir))
            plugins = loader.discover_plugins()

            assert len(plugins) == 0


class TestToolDispatcherErrorSanitization:
    """Tests for error message sanitization in dispatcher [D3]."""

    def test_execution_error_is_sanitized(self):
        """Should not expose internal error details in ToolExecutionError."""

        class LeakyPlugin(PluginBase):
            @property
            def name(self) -> str:
                return "leaky"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return [
                    ToolDefinition(
                        name="leak",
                        description="Leaks internal info",
                        input_schema={"type": "object"},
                    )
                ]

            def execute(self, tool_name: str, arguments: dict) -> ToolResult:
                raise RuntimeError("Database connection to 192.168.1.100:5432 failed")

        dispatcher = ToolDispatcher()
        dispatcher.register_plugin(LeakyPlugin())

        with pytest.raises(ToolExecutionError) as exc_info:
            dispatcher.call_tool("leak", {})

        error_msg = str(exc_info.value)
        # Should NOT contain IP address
        assert "192.168" not in error_msg
        # Should NOT contain port
        assert "5432" not in error_msg
        # Should still mention the tool name for debugging
        assert "leak" in error_msg

    def test_error_chain_preserved(self):
        """Should preserve exception chain for debugging (via __cause__)."""

        class ChainPlugin(PluginBase):
            @property
            def name(self) -> str:
                return "chain"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return [
                    ToolDefinition(
                        name="chain_tool",
                        description="Chains exception",
                        input_schema={"type": "object"},
                    )
                ]

            def execute(self, tool_name: str, arguments: dict) -> ToolResult:
                raise ValueError("Original internal error")

        dispatcher = ToolDispatcher()
        dispatcher.register_plugin(ChainPlugin())

        with pytest.raises(ToolExecutionError) as exc_info:
            dispatcher.call_tool("chain_tool", {})

        # Exception chain should be preserved for debugging
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_loads_builtin_plugins(self):
        """Should load built-in plugins."""
        loader = PluginLoader(Path("."))
        loader.register_plugin(MockPlugin())

        plugins = loader.get_all_plugins()
        assert any(p.name == "mock_plugin" for p in plugins)


class TestToolDispatcher:
    """Tests for ToolDispatcher class."""

    def test_lists_all_tools(self):
        """Should list tools from all plugins."""
        dispatcher = ToolDispatcher()
        dispatcher.register_plugin(MockPlugin())

        tools = dispatcher.list_tools()

        assert len(tools) == 2
        tool_names = [t["name"] for t in tools]
        assert "echo" in tool_names
        assert "add" in tool_names

    def test_dispatches_tool_call(self):
        """Should dispatch tool call to correct plugin."""
        dispatcher = ToolDispatcher()
        dispatcher.register_plugin(MockPlugin())

        result = dispatcher.call_tool("echo", {"message": "test"})

        assert result.content[0]["text"] == "test"

    def test_raises_on_unknown_tool(self):
        """Should raise ToolNotFoundError for unknown tool."""
        dispatcher = ToolDispatcher()
        dispatcher.register_plugin(MockPlugin())

        with pytest.raises(ToolNotFoundError, match="nonexistent"):
            dispatcher.call_tool("nonexistent", {})

    def test_handles_tool_execution_error(self):
        """Should wrap tool execution errors."""

        class BrokenPlugin(PluginBase):
            @property
            def name(self) -> str:
                return "broken"

            @property
            def version(self) -> str:
                return "1.0.0"

            def get_tools(self) -> list[ToolDefinition]:
                return [
                    ToolDefinition(
                        name="crash",
                        description="Always crashes",
                        input_schema={"type": "object"},
                    )
                ]

            def execute(self, tool_name: str, arguments: dict) -> ToolResult:
                raise RuntimeError("Intentional crash")

        dispatcher = ToolDispatcher()
        dispatcher.register_plugin(BrokenPlugin())

        with pytest.raises(ToolExecutionError, match="crash"):
            dispatcher.call_tool("crash", {})

    def test_finds_tool_schema(self):
        """Should return schema for a tool."""
        dispatcher = ToolDispatcher()
        dispatcher.register_plugin(MockPlugin())

        schema = dispatcher.get_tool_schema("echo")

        assert schema is not None
        assert "properties" in schema
        assert "message" in schema["properties"]

    def test_returns_none_for_unknown_tool_schema(self):
        """Should return None for unknown tool schema."""
        dispatcher = ToolDispatcher()

        schema = dispatcher.get_tool_schema("nonexistent")

        assert schema is None


class TestPluginLoaderEdgeCases:
    """Edge case tests for PluginLoader."""

    def test_handles_nonexistent_directory(self):
        """Should handle non-existent plugins directory gracefully."""
        loader = PluginLoader(Path("/nonexistent/plugins"))
        plugins = loader.discover_plugins()
        assert plugins == []

    def test_skips_files_in_plugins_dir(self):
        """Should skip regular files in plugins directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file, not a directory
            (Path(tmpdir) / "not_a_dir.py").write_text("# just a file")

            loader = PluginLoader(Path(tmpdir))
            plugins = loader.discover_plugins()

            assert len(plugins) == 0

    def test_handles_missing_handler(self):
        """Should raise error for plugin without handler.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "incomplete_plugin"
            plugin_dir.mkdir()

            # Create manifest only, no handler
            manifest = {"name": "incomplete", "version": "1.0.0"}
            with open(plugin_dir / "manifest.yaml", "w") as f:
                yaml.dump(manifest, f)

            loader = PluginLoader(Path(tmpdir))
            # Should not crash, but should log error
            plugins = loader.discover_plugins()
            assert len(plugins) == 0

    def test_handles_invalid_handler_class(self):
        """Should raise error if Plugin class doesn't inherit PluginBase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "invalid_plugin"
            plugin_dir.mkdir()

            manifest = {"name": "invalid", "version": "1.0.0"}
            with open(plugin_dir / "manifest.yaml", "w") as f:
                yaml.dump(manifest, f)

            # Create handler with wrong class
            handler_code = """
class Plugin:
    pass  # Doesn't inherit from PluginBase
"""
            with open(plugin_dir / "handler.py", "w") as f:
                f.write(handler_code)

            loader = PluginLoader(Path(tmpdir))
            plugins = loader.discover_plugins()
            assert len(plugins) == 0

    def test_handles_missing_plugin_class(self):
        """Should raise error if handler has no Plugin class."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "no_class_plugin"
            plugin_dir.mkdir()

            manifest = {"name": "no_class", "version": "1.0.0"}
            with open(plugin_dir / "manifest.yaml", "w") as f:
                yaml.dump(manifest, f)

            handler_code = """
# No Plugin class here
def hello():
    pass
"""
            with open(plugin_dir / "handler.py", "w") as f:
                f.write(handler_code)

            loader = PluginLoader(Path(tmpdir))
            plugins = loader.discover_plugins()
            assert len(plugins) == 0
