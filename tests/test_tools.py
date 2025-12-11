"""Tests for tools/list and tools/call handlers."""

from mcp_secure_server.plugins.base import PluginBase, ToolDefinition, ToolResult
from mcp_secure_server.plugins.dispatcher import ToolDispatcher
from mcp_secure_server.protocol.tools import ToolsCallResult, ToolsHandler, ToolsListResult


class MockPlugin(PluginBase):
    """Mock plugin for testing."""

    @property
    def name(self) -> str:
        return "mock"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="echo",
                description="Echoes the input",
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
        return ToolResult(
            content=[{"type": "text", "text": "Unknown tool"}],
            is_error=True,
        )


class FailingPlugin(PluginBase):
    """Plugin that always fails."""

    @property
    def name(self) -> str:
        return "failing"

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
        raise RuntimeError("Intentional crash for testing")


class TestToolsHandler:
    """Tests for ToolsHandler class."""

    def test_creates_handler_with_dispatcher(self):
        """Should create handler with a dispatcher."""
        dispatcher = ToolDispatcher()
        handler = ToolsHandler(dispatcher)
        assert handler._dispatcher is dispatcher

    def test_handles_tools_list(self):
        """Should return list of all registered tools."""
        dispatcher = ToolDispatcher()
        dispatcher.register_plugin(MockPlugin())
        handler = ToolsHandler(dispatcher)

        result = handler.handle_list()

        assert isinstance(result, ToolsListResult)
        assert len(result.tools) == 2
        tool_names = [t["name"] for t in result.tools]
        assert "echo" in tool_names
        assert "add" in tool_names

    def test_handles_tools_call_success(self):
        """Should execute tool and return result."""
        dispatcher = ToolDispatcher()
        dispatcher.register_plugin(MockPlugin())
        handler = ToolsHandler(dispatcher)

        result = handler.handle_call("echo", {"message": "Hello"})

        assert isinstance(result, ToolsCallResult)
        assert result.is_error is False
        assert result.content[0]["text"] == "Hello"

    def test_handles_tools_call_with_numbers(self):
        """Should handle numeric tool arguments."""
        dispatcher = ToolDispatcher()
        dispatcher.register_plugin(MockPlugin())
        handler = ToolsHandler(dispatcher)

        result = handler.handle_call("add", {"a": 5, "b": 3})

        assert result.is_error is False
        assert result.content[0]["text"] == "8"

    def test_handles_unknown_tool(self):
        """Should return error for unknown tool."""
        dispatcher = ToolDispatcher()
        dispatcher.register_plugin(MockPlugin())
        handler = ToolsHandler(dispatcher)

        result = handler.handle_call("nonexistent", {})

        assert result.is_error is True
        assert "not found" in result.content[0]["text"].lower()

    def test_handles_tool_execution_error(self):
        """Should return error when tool crashes."""
        dispatcher = ToolDispatcher()
        dispatcher.register_plugin(FailingPlugin())
        handler = ToolsHandler(dispatcher)

        result = handler.handle_call("crash", {})

        assert result.is_error is True
        assert "crash" in result.content[0]["text"].lower()


class TestToolsListResult:
    """Tests for ToolsListResult dataclass."""

    def test_converts_to_dict(self):
        """Should convert to MCP result format."""
        tools = [{"name": "test", "description": "Test", "inputSchema": {"type": "object"}}]
        result = ToolsListResult(tools=tools)

        d = result.to_dict()

        assert "tools" in d
        assert len(d["tools"]) == 1


class TestToolsCallResult:
    """Tests for ToolsCallResult dataclass."""

    def test_converts_success_to_dict(self):
        """Should convert success result to MCP format."""
        result = ToolsCallResult(
            content=[{"type": "text", "text": "Success"}],
            is_error=False,
        )

        d = result.to_dict()

        assert d["isError"] is False
        assert len(d["content"]) == 1

    def test_converts_error_to_dict(self):
        """Should convert error result to MCP format."""
        result = ToolsCallResult(
            content=[{"type": "text", "text": "Failed"}],
            is_error=True,
        )

        d = result.to_dict()

        assert d["isError"] is True
