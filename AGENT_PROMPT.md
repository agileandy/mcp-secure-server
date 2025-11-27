# Agentic Coding Prompt: Build a Local-Only Secure MCP Server

## Mission

Build a **production-ready, security-first MCP (Model Context Protocol) server** that runs **100% locally** with **zero data leakage**. This server acts as a secure wrapper that enforces strict network isolation while providing pluggable tool capabilities to MCP-compatible hosts.

---

## Critical Constraints

### Non-Negotiable Security Requirements

1. **ZERO external network calls** - All outbound network traffic MUST be blocked by default
2. **STDIO transport ONLY** - No HTTP endpoints, no network sockets, no attack surface
3. **Allowlist-only networking** - If any tool requires network access, ONLY local ranges permitted:
   - `127.0.0.1`, `localhost`
   - `10.0.0.0/8`
   - `172.16.0.0/12`
   - `192.168.0.0/16`
4. **No DNS resolution** - Prevent DNS lookups that could leak queries to external resolvers
5. **Fail-closed design** - Unknown operations are BLOCKED, not allowed
6. **Complete audit trail** - Every operation logged with timestamp, tool, arguments, and result

### Compliance

- MUST comply with **MCP Specification 2025-11-25**: https://modelcontextprotocol.io/specification/2025-11-25
- MUST use **JSON-RPC 2.0** message format
- MUST implement proper **capability negotiation** during initialization
- MUST handle **protocol errors** vs **tool execution errors** correctly per spec

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Local Machine Only                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  STDIO  ┌──────────────────────────────┐  │
│  │   MCP Host   │◀───────▶│     Secure MCP Wrapper       │  │
│  │  (Claude,    │         │  ┌─────────────────────────┐ │  │
│  │   OpenCode,  │         │  │    Security Layer       │ │  │
│  │   etc.)      │         │  │  - Network Firewall     │ │  │
│  └──────────────┘         │  │  - Policy Engine        │ │  │
│                           │  │  - Input Validation     │ │  │
│                           │  │  - Audit Logger         │ │  │
│                           │  └─────────────────────────┘ │  │
│                           │              │               │  │
│                           │              ▼               │  │
│                           │  ┌─────────────────────────┐ │  │
│                           │  │    Plugin System        │ │  │
│                           │  │  - Filesystem tools     │ │  │
│                           │  │  - Code analysis        │ │  │
│                           │  │  - Custom tools         │ │  │
│                           │  └─────────────────────────┘ │  │
│                           └──────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
mcp-secure-local/
├── src/
│   ├── __init__.py
│   ├── server.py           # Main MCP STDIO server
│   ├── lifecycle.py        # Initialize/capability negotiation
│   ├── dispatcher.py       # Routes tools/call to plugins
│   ├── security/
│   │   ├── __init__.py
│   │   ├── firewall.py     # Network validation layer
│   │   ├── policy.py       # Security policy engine
│   │   ├── validator.py    # Input sanitization
│   │   └── audit.py        # Audit logging
│   └── plugins/
│       ├── __init__.py
│       ├── base.py         # Plugin base class
│       └── loader.py       # Plugin discovery
├── plugins/                # Drop-in plugin directory
│   └── example/
│       ├── manifest.yaml
│       └── handler.py
├── config/
│   └── policy.yaml         # Security policy configuration
├── tests/
│   ├── __init__.py
│   ├── test_server.py
│   ├── test_lifecycle.py
│   ├── test_firewall.py
│   ├── test_policy.py
│   ├── test_validator.py
│   ├── test_dispatcher.py
│   └── test_plugins.py
├── pyproject.toml
├── README.md
└── .gitignore
```

---

## Implementation Specifications

### 1. MCP Protocol Layer (`server.py`, `lifecycle.py`)

Implement per MCP Spec 2025-11-25:

#### Initialization Handshake

```python
# Handle initialize request
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {...},
        "clientInfo": {"name": "...", "version": "..."}
    }
}

# Respond with server capabilities
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "protocolVersion": "2025-11-25",
        "capabilities": {
            "tools": {"listChanged": true}
        },
        "serverInfo": {
            "name": "secure-local-mcp",
            "version": "1.0.0"
        }
    }
}
```

#### Required Methods

| Method | Direction | Implementation |
|--------|-----------|----------------|
| `initialize` | Client → Server | Return capabilities, validate protocol version |
| `notifications/initialized` | Client → Server | Mark session as ready |
| `tools/list` | Client → Server | Return all loaded plugin tools |
| `tools/call` | Client → Server | Validate → Policy check → Execute → Audit |
| `notifications/tools/list_changed` | Server → Client | Emit when plugins change |

#### STDIO Transport Rules (from spec)

- Read JSON-RPC from `stdin`, write to `stdout`
- Messages delimited by newlines, MUST NOT contain embedded newlines
- Logging to `stderr` only (MUST NOT write non-MCP content to stdout)
- UTF-8 encoding required

### 2. Security Layer

#### Firewall (`security/firewall.py`)

```python
class NetworkFirewall:
    """
    Validates all network operations against allowlist.
    
    ALLOWED (local only):
    - 127.0.0.0/8 (loopback)
    - 10.0.0.0/8 (private)
    - 172.16.0.0/12 (private)
    - 192.168.0.0/16 (private)
    - ::1 (IPv6 loopback)
    - fe80::/10 (IPv6 link-local)
    
    BLOCKED:
    - All other addresses
    - DNS resolution to external servers
    - Any hostname that resolves to non-local IP
    """
    
    def validate_address(self, host: str, port: int) -> bool:
        """Returns True only if address is local. Raises SecurityError otherwise."""
        
    def validate_url(self, url: str) -> bool:
        """Parse URL and validate host. Block if external."""
```

#### Policy Engine (`security/policy.py`)

Load from `config/policy.yaml`:

```yaml
# Security Policy Configuration
version: "1.0"

network:
  # Only these are allowed - everything else blocked
  allowed_ranges:
    - "127.0.0.0/8"
    - "10.0.0.0/8"
    - "172.16.0.0/12"
    - "192.168.0.0/16"
  
  # Block these ports even on local network
  blocked_ports:
    - 22    # SSH (prevent lateral movement)
  
  # DNS settings
  allow_dns: false  # Block all DNS queries
  
filesystem:
  # Allowed paths (glob patterns)
  allowed_paths:
    - "${HOME}/projects/**"
    - "${HOME}/workspace/**"
    - "/tmp/mcp-workspace/**"
  
  # Explicitly denied (takes precedence)
  denied_paths:
    - "**/.ssh/**"
    - "**/.aws/**"
    - "**/.gnupg/**"
    - "**/*.pem"
    - "**/*.key"
    - "**/.env"
    - "**/.env.*"
    - "**/secrets/**"
    - "**/.git/config"  # May contain credentials

commands:
  # Blocked commands (security risk)
  blocked:
    - "curl"
    - "wget"
    - "ssh"
    - "scp"
    - "rsync"
    - "nc"
    - "netcat"
    - "telnet"
    - "ftp"
    - "sftp"

tools:
  # Per-tool rate limits (requests per minute)
  rate_limits:
    default: 60
    filesystem_write: 30
    command_execute: 10
  
  # Timeout in seconds
  timeout: 30

audit:
  # Log file location
  log_file: "${HOME}/.mcp-secure/audit.log"
  
  # What to log
  log_level: "INFO"  # DEBUG, INFO, WARN, ERROR
  
  # Include these in audit log
  include:
    - timestamp
    - tool_name
    - arguments
    - result_status
    - execution_time
```

#### Input Validator (`security/validator.py`)

```python
class InputValidator:
    """
    Sanitizes and validates all tool inputs.
    
    - Validate against JSON Schema (2020-12 per spec)
    - Check for path traversal attacks
    - Sanitize shell-sensitive characters
    - Enforce size limits
    """
    
    def validate_tool_input(self, tool_name: str, schema: dict, arguments: dict) -> dict:
        """Validate and sanitize input. Raises ValidationError on failure."""
        
    def sanitize_path(self, path: str) -> str:
        """Resolve path, check for traversal, validate against policy."""
        
    def sanitize_command(self, command: str) -> str:
        """Check command against blocklist, sanitize arguments."""
```

#### Audit Logger (`security/audit.py`)

```python
class AuditLogger:
    """
    Immutable, append-only audit log.
    
    Every operation logged with:
    - ISO 8601 timestamp
    - Request ID
    - Tool name
    - Arguments (sanitized)
    - Result status (success/error)
    - Execution duration
    - Security events (policy blocks, validation failures)
    """
    
    def log_request(self, request_id: str, tool: str, arguments: dict) -> None:
        """Log incoming request."""
        
    def log_response(self, request_id: str, status: str, duration_ms: float) -> None:
        """Log response."""
        
    def log_security_event(self, event_type: str, details: dict) -> None:
        """Log security-relevant events (blocks, violations)."""
```

### 3. Plugin System

#### Base Plugin (`plugins/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Any

class PluginBase(ABC):
    """Base class for all plugins."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier."""
        
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        
    @abstractmethod
    def get_tools(self) -> list[dict]:
        """Return tool definitions (JSON Schema format)."""
        
    @abstractmethod
    def execute(self, tool_name: str, arguments: dict) -> Any:
        """Execute a tool. Returns result or raises ToolError."""
```

#### Plugin Manifest Format (`plugins/example/manifest.yaml`)

```yaml
name: example
version: "1.0.0"
description: "Example plugin demonstrating the plugin format"

tools:
  - name: echo
    description: "Returns the input message"
    inputSchema:
      type: object
      properties:
        message:
          type: string
          description: "Message to echo back"
      required:
        - message
    
  - name: add_numbers
    description: "Adds two numbers"
    inputSchema:
      type: object
      properties:
        a:
          type: number
        b:
          type: number
      required:
        - a
        - b
    outputSchema:
      type: object
      properties:
        result:
          type: number
      required:
        - result

# Plugin-specific security hints (merged with global policy)
security:
  requires_network: false
  requires_filesystem: false
```

#### Plugin Loader (`plugins/loader.py`)

```python
class PluginLoader:
    """
    Discovers and loads plugins from the plugins/ directory.
    
    - Scans for manifest.yaml files
    - Validates manifest schema
    - Dynamically imports handler.py
    - Registers tools with dispatcher
    """
    
    def discover_plugins(self, plugins_dir: Path) -> list[PluginBase]:
        """Find and load all valid plugins."""
        
    def reload_plugins(self) -> None:
        """Hot-reload plugins and emit list_changed notification."""
```

### 4. Error Handling (Per MCP Spec)

#### Protocol Errors (JSON-RPC errors)

```python
# Unknown method
{
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32601,
        "message": "Method not found"
    }
}

# Invalid params
{
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32602,
        "message": "Invalid params: unknown tool 'bad_tool'"
    }
}
```

#### Tool Execution Errors (in result with isError)

```python
# Policy violation
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "content": [
            {
                "type": "text",
                "text": "Security policy violation: path '/etc/passwd' is not in allowed paths"
            }
        ],
        "isError": true
    }
}

# Validation failure
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "content": [
            {
                "type": "text",
                "text": "Validation error: 'count' must be a positive integer"
            }
        ],
        "isError": true
    }
}
```

---

## Development Requirements

### Technology Stack

- **Python**: 3.11+
- **Package Manager**: `uv`
- **Linting**: `ruff`
- **Testing**: `pytest`
- **Type Checking**: Use type hints throughout

### Dependencies (minimal)

```toml
[project]
name = "mcp-secure-local"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    "pyyaml>=6.0",           # Config parsing
    "jsonschema>=4.20",      # Schema validation
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.4",
]
```

### TDD Requirements

**MANDATORY: Follow Red-Green-Refactor cycle**

1. **RED**: Write a failing test FIRST
2. **GREEN**: Write minimal code to pass
3. **REFACTOR**: Clean up while keeping tests green

Test coverage requirements:
- Security layer: 100% coverage
- Protocol handling: 100% coverage
- Plugin system: 90%+ coverage
- Overall: 95%+ coverage

### Git Workflow

- Create feature branch for each component
- Atomic commits: ≤50 lines OR 2-3 TDD tests
- Run `ruff check` and `ruff format` before every commit
- Commit message format: `<type>: <description>` (e.g., `feat: add network firewall`)

---

## Acceptance Criteria

### Security (MUST PASS)

- [ ] No code path can make external network requests
- [ ] All tool inputs validated against JSON Schema
- [ ] Path traversal attacks blocked
- [ ] Sensitive file patterns blocked
- [ ] Dangerous commands blocked
- [ ] Rate limiting enforced
- [ ] Complete audit trail generated
- [ ] Fail-closed on unknown operations

### Protocol Compliance (MUST PASS)

- [ ] Correct JSON-RPC 2.0 message format
- [ ] Proper capability negotiation
- [ ] Protocol errors vs tool errors distinguished correctly
- [ ] STDIO transport works correctly
- [ ] UTF-8 encoding throughout

### Functionality (MUST PASS)

- [ ] Plugin discovery works
- [ ] Tools listed correctly via `tools/list`
- [ ] Tool execution works via `tools/call`
- [ ] Hot-reload triggers `list_changed` notification
- [ ] Graceful shutdown

### Code Quality (MUST PASS)

- [ ] All tests passing
- [ ] 95%+ test coverage
- [ ] No ruff errors
- [ ] Type hints on all public APIs
- [ ] Docstrings on all public classes/methods

---

## Implementation Order

Execute in this order, completing each phase before moving to next:

### Phase 1: Foundation
1. Project scaffolding (`pyproject.toml`, directory structure)
2. Security policy loader and schema
3. Audit logger

### Phase 2: Security Layer
4. Network firewall
5. Input validator
6. Policy engine integration

### Phase 3: Protocol Layer
7. JSON-RPC message parsing
8. STDIO transport
9. Lifecycle management (initialize, initialized)

### Phase 4: Tool System
10. Plugin base class
11. Plugin loader
12. Tool dispatcher
13. `tools/list` implementation
14. `tools/call` implementation

### Phase 5: Integration
15. Main server entry point
16. Example plugin
17. Integration tests
18. Documentation

---

## Reference Documentation

- **MCP Specification 2025-11-25**: https://modelcontextprotocol.io/specification/2025-11-25
- **MCP Architecture**: https://modelcontextprotocol.io/specification/2025-11-25/architecture
- **MCP Tools**: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- **MCP Transports**: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- **JSON-RPC 2.0**: https://www.jsonrpc.org/specification
- **JSON Schema 2020-12**: https://json-schema.org/specification

---

## Final Notes

This server is designed for **enterprise security requirements**. Every design decision prioritizes:

1. **Security** - No data leaves the local machine
2. **Auditability** - Complete trail of all operations
3. **Extensibility** - Plugin system for custom capabilities
4. **Compliance** - Full MCP spec adherence

The architecture separates concerns cleanly:
- **Fixed**: Transport, security, audit, protocol handling
- **Swappable**: Plugins defining actual tool capabilities

Build this correctly, and it becomes a trusted foundation for local AI tooling in security-conscious environments.
