# MCP Secure Local Server

A production-ready, security-first Model Context Protocol (MCP) server that runs locally with strict security controls while allowing controlled external network access for specific use cases like web search.

## Features

- **Security-First Design**: All operations are validated against a configurable security policy
- **Network Firewall**: Block all external network access except explicitly allowlisted endpoints
- **Input Validation**: JSON Schema validation, path traversal protection, command sanitization
- **Rate Limiting**: Per-tool rate limits to prevent abuse
- **Audit Logging**: JSON Lines format logging with sensitive data redaction
- **Plugin System**: Extensible architecture for adding new tools
- **MCP Protocol Compliant**: Full JSON-RPC 2.0 over STDIO transport

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd mcp-server

# Install dependencies with uv
uv sync
```

### Running the Server

```bash
# Run with default policy
uv run python main.py

# Run with custom policy file
uv run python main.py --policy /path/to/policy.yaml

# Show version
uv run python main.py --version
```

### Integration with MCP Clients

This server works with any MCP-compatible client. Add the following to your client's MCP configuration:

```json
{
  "mcpServers": {
    "secure-local": {
      "command": "uv",
      "args": ["run", "python", "/path/to/mcp-server/main.py"],
      "env": {}
    }
  }
}
```

**Example client configuration locations:**
- **Claude Desktop**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
- **Other MCP clients**: Refer to your client's documentation for the configuration file location

## Architecture

```
mcp-server/
├── main.py                    # CLI entry point
├── config/
│   └── policy.yaml            # Security policy configuration
├── src/
│   ├── server.py              # Main MCP server
│   ├── protocol/
│   │   ├── jsonrpc.py         # JSON-RPC 2.0 parsing
│   │   ├── transport.py       # STDIO transport
│   │   ├── lifecycle.py       # MCP lifecycle management
│   │   └── tools.py           # tools/list & tools/call handlers
│   ├── plugins/
│   │   ├── base.py            # Plugin base class
│   │   ├── loader.py          # Plugin discovery
│   │   ├── dispatcher.py      # Tool call routing
│   │   ├── discovery.py       # Built-in: Progressive disclosure tools
│   │   ├── websearch.py       # Example: DuckDuckGo search plugin
│   │   └── bugtracker.py      # Example: Bug tracking plugin
│   └── security/
│       ├── policy.py          # Policy loader
│       ├── firewall.py        # Network access control
│       ├── validator.py       # Input validation
│       ├── engine.py          # Integrated security engine
│       └── audit.py           # Audit logging
└── tests/                     # Test suite (343 tests, 96%+ coverage)
```

## Security Policy

The security policy is defined in YAML format. See `config/policy.yaml` for a complete example.

### Network Security

```yaml
network:
  # Allowed local network ranges
  allowed_ranges:
    - "127.0.0.0/8"
    - "10.0.0.0/8"
    - "192.168.0.0/16"

  # Explicitly allowed external endpoints
  allowed_endpoints:
    - host: "lite.duckduckgo.com"
      ports: [443]
      description: "DuckDuckGo search"

  # Blocked ports (even on local network)
  blocked_ports:
    - 22  # SSH

  # DNS settings
  allow_dns: true
  dns_allowlist:
    - "lite.duckduckgo.com"
```

### Filesystem Security

```yaml
filesystem:
  # Allowed paths (supports globs and env vars)
  allowed_paths:
    - "${HOME}/projects/**"
    - "/tmp/mcp-workspace/**"

  # Denied paths (takes precedence)
  denied_paths:
    - "**/.ssh/**"
    - "**/.aws/**"
    - "**/*.pem"
    - "**/.env"
```

### Tool Configuration

```yaml
tools:
  # Rate limits (requests per minute)
  rate_limits:
    default: 60
    web_search: 20

  # Execution timeout
  timeout: 30
```

### Audit Logging

```yaml
audit:
  log_file: "${HOME}/.mcp-secure/audit.log"
  log_level: "INFO"
```

## Built-in Tools

The server automatically registers discovery tools for progressive disclosure, enabling agents to efficiently find and load only the tools they need.

### search_tools

Search for available tools by keyword or category. Use `detail_level` to control context usage.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Keyword to search in tool names and descriptions"
    },
    "category": {
      "type": "string",
      "description": "Filter by plugin category (e.g., 'bugtracker')"
    },
    "detail_level": {
      "type": "string",
      "enum": ["name", "summary", "full"],
      "description": "Level of detail: 'name' (just names), 'summary' (names + descriptions), 'full' (complete schemas)"
    }
  }
}
```

**Example - Find bug-related tools with minimal context:**
```json
{
  "name": "search_tools",
  "arguments": {
    "query": "bug",
    "detail_level": "name"
  }
}
// Returns: ["add_bug", "get_bug", "update_bug", "close_bug", "list_bugs", "search_bugs_global"]
```

**Example - Get full schema for a specific category:**
```json
{
  "name": "search_tools",
  "arguments": {
    "category": "websearch",
    "detail_level": "full"
  }
}
```

### list_categories

List all available tool categories (plugins) with tool counts. Use this to discover capabilities before searching.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {}
}
```

**Example Response:**
```json
[
  {
    "category": "discovery",
    "version": "1.0.0",
    "tool_count": 2,
    "tools": ["search_tools", "list_categories"]
  },
  {
    "category": "websearch",
    "version": "1.0.0",
    "tool_count": 1,
    "tools": ["web_search"]
  },
  {
    "category": "bugtracker",
    "version": "1.0.0",
    "tool_count": 7,
    "tools": ["init_bugtracker", "add_bug", "get_bug", "update_bug", "close_bug", "list_bugs", "search_bugs_global"]
  }
]
```

## Example Plugins

The server includes example plugins to demonstrate the plugin architecture. These are provided as reference implementations showing how to build your own plugins for any use case.

### web_search (Example Plugin)

An example plugin that searches the web using DuckDuckGo. Demonstrates how to build plugins that make external network requests within the security policy.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "The search query"
    },
    "max_results": {
      "type": "integer",
      "description": "Maximum results to return (default: 5)"
    }
  },
  "required": ["query"]
}
```

**Example:**
```json
{
  "name": "web_search",
  "arguments": {
    "query": "Python asyncio tutorial",
    "max_results": 3
  }
}
```

### Bug Tracker (Example Plugin)

An example plugin implementing a local bug tracking system with a centralized SQLite database. Demonstrates how to build plugins that manage local state, support multiple projects, and perform complex queries.

#### init_bugtracker

Initialize bug tracking for a project.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "project_path": {
      "type": "string",
      "description": "Path to project directory (defaults to cwd)"
    }
  }
}
```

#### add_bug

Add a new bug to the tracker.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "title": {
      "type": "string",
      "description": "Brief title for the bug"
    },
    "description": {
      "type": "string",
      "description": "Detailed description"
    },
    "priority": {
      "type": "string",
      "enum": ["low", "medium", "high", "critical"],
      "description": "Bug priority (default: medium)"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Tags for categorization"
    },
    "project_path": {
      "type": "string",
      "description": "Path to project directory (defaults to cwd)"
    }
  },
  "required": ["title"]
}
```

#### get_bug

Retrieve a bug by ID.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "bug_id": {
      "type": "string",
      "description": "The bug ID to retrieve"
    },
    "project_path": {
      "type": "string",
      "description": "Path to project directory (defaults to cwd)"
    }
  },
  "required": ["bug_id"]
}
```

#### update_bug

Update an existing bug's status, priority, tags, or related bugs. Supports note-only updates for progress tracking.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "bug_id": {
      "type": "string",
      "description": "The bug ID to update"
    },
    "status": {
      "type": "string",
      "enum": ["open", "in_progress", "closed"]
    },
    "priority": {
      "type": "string",
      "enum": ["low", "medium", "high", "critical"]
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "New tags (replaces existing)"
    },
    "related_bugs": {
      "type": "array",
      "description": "Related bugs with relationship type"
    },
    "note": {
      "type": "string",
      "description": "Note for the history entry"
    },
    "project_path": {
      "type": "string"
    }
  },
  "required": ["bug_id"]
}
```

#### close_bug

Close a bug with a resolution note.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "bug_id": {
      "type": "string",
      "description": "The bug ID to close"
    },
    "resolution": {
      "type": "string",
      "description": "Resolution note explaining how the bug was fixed"
    },
    "project_path": {
      "type": "string"
    }
  },
  "required": ["bug_id"]
}
```

#### list_bugs

List bugs with optional filtering.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["open", "in_progress", "closed"]
    },
    "priority": {
      "type": "string",
      "enum": ["low", "medium", "high", "critical"]
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Filter by tags (must have ALL specified tags)"
    },
    "project_path": {
      "type": "string"
    }
  }
}
```

#### search_bugs_global

Search bugs across all indexed projects.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["open", "in_progress", "closed"]
    },
    "priority": {
      "type": "string",
      "enum": ["low", "medium", "high", "critical"]
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"}
    }
  }
}
```

**Example - Create and track a bug:**
```json
// Add a bug
{
  "name": "add_bug",
  "arguments": {
    "title": "Login button not responding",
    "description": "The login button on the home page doesn't trigger the auth flow",
    "priority": "high",
    "tags": ["ui", "auth"]
  }
}

// Update with progress
{
  "name": "update_bug",
  "arguments": {
    "bug_id": "BUG-001",
    "status": "in_progress",
    "note": "Identified missing onClick handler"
  }
}

// Close with resolution
{
  "name": "close_bug",
  "arguments": {
    "bug_id": "BUG-001",
    "resolution": "Added onClick handler to LoginButton component"
  }
}
```

## Creating Custom Plugins

### Python Plugins

Plugins must inherit from `PluginBase` and implement the required methods:

```python
from src.plugins.base import PluginBase, ToolDefinition, ToolResult

class MyPlugin(PluginBase):
    @property
    def name(self) -> str:
        return "my_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="my_tool",
                description="Does something useful",
                input_schema={
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"}
                    },
                    "required": ["input"]
                },
            )
        ]

    def execute(self, tool_name: str, arguments: dict) -> ToolResult:
        if tool_name == "my_tool":
            result = do_something(arguments["input"])
            return ToolResult(
                content=[{"type": "text", "text": result}]
            )
        return ToolResult(
            content=[{"type": "text", "text": "Unknown tool"}],
            is_error=True
        )
```

Register the plugin in `main.py`:

```python
from my_plugin import MyPlugin

server.register_plugin(MyPlugin())
```

### External Plugins (Non-Python)

The plugin system can support tools written in any language (Rust, JavaScript, TypeScript, Go, etc.) through a subprocess wrapper approach. This is a planned feature - contributions welcome.

#### Architecture Overview

External plugins run as separate processes, communicating with the Python wrapper via JSON over stdin/stdout:

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Server (Python)                      │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ WebSearch    │    │ BugTracker   │    │ External     │   │
│  │ (Python)     │    │ (Python)     │    │ Plugin       │   │
│  └──────────────┘    └──────────────┘    │ (Wrapper)    │   │
│                                          └──────┬───────┘   │
│                                                 │            │
└─────────────────────────────────────────────────┼────────────┘
                                                  │ JSON/stdin/stdout
                                                  ▼
                                          ┌──────────────┐
                                          │ my-rust-tool │
                                          │ (subprocess) │
                                          └──────────────┘
```

#### How It Works

1. **Python Wrapper**: A thin `ExternalPlugin` class inherits from `PluginBase` and handles the subprocess lifecycle
2. **Manifest**: A `manifest.yaml` declares the tool definitions and points to the executable
3. **Contract**: The external tool receives JSON on stdin and writes JSON to stdout

#### Manifest Format

```yaml
name: my-rust-tools
version: "1.0.0"
type: external
executable: ./target/release/my-rust-tool

tools:
  - name: calculate_hash
    description: Calculate cryptographic hash of input
    input_schema:
      type: object
      properties:
        algorithm:
          type: string
          enum: [sha256, sha512, blake3]
        input:
          type: string
      required: [algorithm, input]
```

#### External Tool Contract

The external executable must:

1. **Accept** a JSON object on stdin:
```json
{
  "tool": "calculate_hash",
  "arguments": {
    "algorithm": "sha256",
    "input": "hello world"
  }
}
```

2. **Return** a JSON object on stdout:
```json
{
  "content": [
    {"type": "text", "text": "sha256: b94d27b9934d3e08..."}
  ],
  "isError": false
}
```

3. **Exit** with code 0 on success, non-zero on failure

#### Example: Rust Tool

```rust
use serde::{Deserialize, Serialize};
use std::io::{self, BufRead, Write};

#[derive(Deserialize)]
struct Request {
    tool: String,
    arguments: serde_json::Value,
}

#[derive(Serialize)]
struct Response {
    content: Vec<Content>,
    #[serde(rename = "isError")]
    is_error: bool,
}

#[derive(Serialize)]
struct Content {
    #[serde(rename = "type")]
    content_type: String,
    text: String,
}

fn main() {
    let stdin = io::stdin();
    let line = stdin.lock().lines().next().unwrap().unwrap();
    let request: Request = serde_json::from_str(&line).unwrap();

    let result = match request.tool.as_str() {
        "calculate_hash" => calculate_hash(request.arguments),
        _ => Err(format!("Unknown tool: {}", request.tool)),
    };

    let response = match result {
        Ok(text) => Response {
            content: vec![Content { content_type: "text".into(), text }],
            is_error: false,
        },
        Err(e) => Response {
            content: vec![Content { content_type: "text".into(), text: e }],
            is_error: true,
        },
    };

    println!("{}", serde_json::to_string(&response).unwrap());
}
```

#### Example: Node.js Tool

```javascript
const readline = require('readline');

const rl = readline.createInterface({ input: process.stdin });

rl.on('line', (line) => {
  const request = JSON.parse(line);

  let response;
  try {
    const result = handleTool(request.tool, request.arguments);
    response = {
      content: [{ type: 'text', text: result }],
      isError: false
    };
  } catch (e) {
    response = {
      content: [{ type: 'text', text: e.message }],
      isError: true
    };
  }

  console.log(JSON.stringify(response));
  process.exit(0);
});

function handleTool(tool, args) {
  switch (tool) {
    case 'format_json':
      return JSON.stringify(JSON.parse(args.input), null, 2);
    default:
      throw new Error(`Unknown tool: ${tool}`);
  }
}
```

#### Security Considerations for External Plugins

1. **Process Isolation**: External tools run in separate processes with their own memory space
2. **Timeout Enforcement**: The wrapper kills subprocesses that exceed the configured timeout
3. **No Network Inheritance**: Subprocess network access is governed by OS-level controls
4. **Executable Allowlist**: Only executables listed in registered manifests can be invoked
5. **Input Validation**: JSON schemas are validated before passing to the subprocess

#### Trade-offs

| Aspect | Python Plugin | External Plugin |
|--------|---------------|-----------------|
| **Startup latency** | None | ~10-50ms per call |
| **Memory** | Shared with server | Separate process |
| **Language** | Python only | Any language |
| **Debugging** | Easy | Harder (separate process) |
| **Security** | Shared memory space | Process isolation |

#### When to Use External Plugins

- **Performance-critical tools**: Rust/Go for CPU-intensive operations
- **Existing CLI tools**: Wrap existing binaries without rewriting
- **Language-specific libraries**: Use npm packages, Cargo crates, etc.
- **Team expertise**: Let teams use their preferred language

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_server.py -v
```

### Linting

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Project Structure

| Directory | Purpose |
|-----------|---------|
| `src/protocol/` | MCP protocol implementation (JSON-RPC, STDIO, lifecycle) |
| `src/plugins/` | Plugin system and built-in plugins |
| `src/security/` | Security layer (firewall, validation, audit) |
| `tests/` | Test suite |
| `config/` | Configuration files |

## MCP Protocol Support

This server implements MCP protocol version `2025-11-25` with support for:

| Method | Description |
|--------|-------------|
| `initialize` | Initialize the connection |
| `notifications/initialized` | Confirm initialization complete |
| `tools/list` | List available tools |
| `tools/call` | Execute a tool |

## Security Considerations

1. **Network Isolation**: By default, all external network access is blocked. Only explicitly allowlisted endpoints can be reached.

2. **Path Traversal Protection**: All file paths are validated against allowed/denied patterns to prevent accessing sensitive files.

3. **Command Injection Prevention**: Commands are sanitized to block dangerous patterns like shell operators.

4. **Rate Limiting**: Per-tool rate limits prevent abuse and resource exhaustion.

5. **Audit Trail**: All operations are logged with timestamps, request IDs, and sanitized arguments.

## License

MIT License - see LICENSE file for details.
