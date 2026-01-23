# Plugin Development Guide

This guide explains how to create custom plugins for the MCP Secure Local Server.

## Overview

Plugins extend the server with new tools that can be called via the MCP protocol. Each plugin:

- Inherits from `PluginBase`
- Defines one or more tools with JSON Schema input validation
- Implements tool execution logic
- Returns results in MCP format

## Quick Start

### 1. Create the Plugin Class

```python
from src.plugins.base import PluginBase, ToolDefinition, ToolResult

class CalculatorPlugin(PluginBase):
    """A simple calculator plugin."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="add",
                description="Add two numbers",
                input_schema={
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"},
                    },
                    "required": ["a", "b"],
                },
            ),
            ToolDefinition(
                name="multiply",
                description="Multiply two numbers",
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
        if tool_name == "add":
            result = arguments["a"] + arguments["b"]
            return ToolResult(
                content=[{"type": "text", "text": str(result)}]
            )
        elif tool_name == "multiply":
            result = arguments["a"] * arguments["b"]
            return ToolResult(
                content=[{"type": "text", "text": str(result)}]
            )
        else:
            return ToolResult(
                content=[{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                is_error=True,
            )
```

### 2. Register the Plugin

In `main.py`, add:

```python
from my_plugins.calculator import CalculatorPlugin

# In main():
server.register_plugin(CalculatorPlugin())
```

### 3. Test the Plugin

```python
# tests/test_calculator.py
from my_plugins.calculator import CalculatorPlugin

def test_add():
    plugin = CalculatorPlugin()
    result = plugin.execute("add", {"a": 2, "b": 3})
    assert result.content[0]["text"] == "5"
    assert result.is_error is False
```

## API Reference

### PluginBase

Abstract base class all plugins must inherit from.

```python
class PluginBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the plugin identifier."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the plugin version."""
        pass

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        """Return tool definitions provided by this plugin."""
        pass

    @abstractmethod
    def execute(self, tool_name: str, arguments: dict) -> ToolResult:
        """Execute a tool."""
        pass
```

### ToolDefinition

Defines a tool's metadata and input schema.

```python
@dataclass
class ToolDefinition:
    name: str                    # Unique tool identifier
    description: str             # Human-readable description
    input_schema: dict[str, Any] # JSON Schema for input validation

    def to_dict(self) -> dict[str, Any]:
        """Convert to MCP tool format."""
```

### ToolResult

Represents the result of a tool execution.

```python
@dataclass
class ToolResult:
    content: list[dict[str, Any]]  # Result content blocks
    is_error: bool = False          # Whether this is an error result

    def to_dict(self) -> dict[str, Any]:
        """Convert to MCP result format."""
```

## Content Types

Tool results can include multiple content blocks:

### Text Content

```python
ToolResult(content=[
    {"type": "text", "text": "Hello, world!"}
])
```

### Multiple Blocks

```python
ToolResult(content=[
    {"type": "text", "text": "Results:"},
    {"type": "text", "text": "Item 1"},
    {"type": "text", "text": "Item 2"},
])
```

### Error Results

```python
ToolResult(
    content=[{"type": "text", "text": "Something went wrong"}],
    is_error=True,
)
```

## Input Schema

Tool input schemas use JSON Schema format.

### Basic Types

```python
input_schema={
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "count": {"type": "integer"},
        "ratio": {"type": "number"},
        "enabled": {"type": "boolean"},
    },
    "required": ["text"],
}
```

### With Descriptions

```python
input_schema={
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search query to execute",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results",
            "default": 10,
        },
    },
    "required": ["query"],
}
```

### Enums

```python
input_schema={
    "type": "object",
    "properties": {
        "format": {
            "type": "string",
            "enum": ["json", "xml", "csv"],
            "description": "Output format",
        },
    },
}
```

### Arrays

```python
input_schema={
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of items to process",
        },
    },
}
```

## Best Practices

### 1. Handle Errors Gracefully

```python
def execute(self, tool_name: str, arguments: dict) -> ToolResult:
    try:
        result = self._do_work(arguments)
        return ToolResult(content=[{"type": "text", "text": result}])
    except ValueError as e:
        return ToolResult(
            content=[{"type": "text", "text": f"Invalid input: {e}"}],
            is_error=True,
        )
    except Exception as e:
        return ToolResult(
            content=[{"type": "text", "text": f"Error: {e}"}],
            is_error=True,
        )
```

### 2. Validate Input

Even though the server validates against your schema, add defensive checks:

```python
def execute(self, tool_name: str, arguments: dict) -> ToolResult:
    query = arguments.get("query", "").strip()
    if not query:
        return ToolResult(
            content=[{"type": "text", "text": "Query cannot be empty"}],
            is_error=True,
        )
    # ... rest of implementation
```

### 3. Respect Timeouts

For long-running operations, check for cancellation:

```python
def execute(self, tool_name: str, arguments: dict) -> ToolResult:
    results = []
    for item in items:
        # Process in chunks, allowing for timeout
        result = process_item(item)
        results.append(result)
    return ToolResult(content=[{"type": "text", "text": "\n".join(results)}])
```

### 4. Use Type Hints

```python
from typing import Any

def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
    ...
```

### 5. Write Tests

```python
import pytest
from my_plugin import MyPlugin

class TestMyPlugin:
    def test_provides_tools(self):
        plugin = MyPlugin()
        tools = plugin.get_tools()
        assert len(tools) > 0

    def test_executes_tool(self):
        plugin = MyPlugin()
        result = plugin.execute("my_tool", {"input": "test"})
        assert result.is_error is False

    def test_handles_unknown_tool(self):
        plugin = MyPlugin()
        result = plugin.execute("unknown", {})
        assert result.is_error is True
```

## Example: HTTP API Plugin

A more complete example that calls an external API:

```python
import httpx
from src.plugins.base import PluginBase, ToolDefinition, ToolResult

class WeatherPlugin(PluginBase):
    """Weather information plugin."""

    API_URL = "https://api.weather.example.com/v1"

    @property
    def name(self) -> str:
        return "weather"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="get_weather",
                description="Get current weather for a location",
                input_schema={
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "City name",
                        },
                        "units": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "default": "celsius",
                        },
                    },
                    "required": ["city"],
                },
            ),
        ]

    def execute(self, tool_name: str, arguments: dict) -> ToolResult:
        if tool_name != "get_weather":
            return ToolResult(
                content=[{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                is_error=True,
            )

        city = arguments["city"]
        units = arguments.get("units", "celsius")

        try:
            response = httpx.get(
                f"{self.API_URL}/weather",
                params={"city": city, "units": units},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            text = (
                f"Weather in {city}:\n"
                f"Temperature: {data['temp']}°{'C' if units == 'celsius' else 'F'}\n"
                f"Conditions: {data['conditions']}\n"
                f"Humidity: {data['humidity']}%"
            )

            return ToolResult(content=[{"type": "text", "text": text}])

        except httpx.HTTPError as e:
            return ToolResult(
                content=[{"type": "text", "text": f"API error: {e}"}],
                is_error=True,
            )
```

**Important**: Remember to add the API endpoint to your security policy's `allowed_endpoints` list!

## File-Based Plugins

For file-based plugin loading, create a directory with:

```
plugins/
└── my_plugin/
    ├── manifest.yaml
    └── handler.py
```

### manifest.yaml

```yaml
name: my_plugin
version: 1.0.0
description: My custom plugin
tools:
  - name: my_tool
    description: Does something
    inputSchema:
      type: object
      properties:
        input:
          type: string
      required:
        - input
```

### handler.py

```python
from src.plugins.base import PluginBase, ToolDefinition, ToolResult

class Plugin(PluginBase):
    # Must be named "Plugin"
    ...
```

The `PluginLoader` will discover and load these automatically.
