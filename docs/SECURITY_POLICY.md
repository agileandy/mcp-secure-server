# Security Policy Reference

This document provides a complete reference for the security policy configuration.

## Policy Structure

The security policy is a YAML file with the following top-level sections:

```yaml
version: "1.0"
network: { ... }
filesystem: { ... }
commands: { ... }
tools: { ... }
audit: { ... }
```

## Network Section

Controls network access for all tool operations.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `allowed_ranges` | list[string] | No | CIDR ranges for allowed local networks |
| `allowed_endpoints` | list[object] | No | External endpoints to allow |
| `blocked_ports` | list[int] | No | Ports to block even on local network |
| `allow_dns` | bool | No | Whether to allow DNS resolution |
| `dns_allowlist` | list[string] | No | Hostnames allowed for DNS |

### Example

```yaml
network:
  allowed_ranges:
    - "127.0.0.0/8"      # Localhost
    - "10.0.0.0/8"       # Private Class A
    - "172.16.0.0/12"    # Private Class B
    - "192.168.0.0/16"   # Private Class C
    - "::1/128"          # IPv6 localhost
    - "fe80::/10"        # IPv6 link-local

  allowed_endpoints:
    - host: "api.example.com"
      ports: [443, 8443]
      description: "Example API"

  blocked_ports:
    - 22    # SSH
    - 23    # Telnet
    - 3389  # RDP

  allow_dns: true
  dns_allowlist:
    - "api.example.com"
```

### Behavior

1. **Local networks**: Traffic to `allowed_ranges` is permitted (except `blocked_ports`)
2. **External endpoints**: Only explicitly listed hosts/ports are allowed
3. **DNS**: Resolution only works for `dns_allowlist` entries when `allow_dns` is true
4. **Default deny**: All other network access is blocked

## Filesystem Section

Controls file system access.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `allowed_paths` | list[string] | Yes | Glob patterns for allowed paths |
| `denied_paths` | list[string] | Yes | Glob patterns for denied paths (takes precedence) |

### Supported Patterns

- `*` - Match any characters within a path segment
- `**` - Match any characters across path segments
- `${ENV_VAR}` - Environment variable expansion

### Example

```yaml
filesystem:
  allowed_paths:
    - "${HOME}/projects/**"
    - "${HOME}/workspace/**"
    - "/tmp/mcp-workspace/**"

  denied_paths:
    - "**/.ssh/**"
    - "**/.aws/**"
    - "**/.gnupg/**"
    - "**/*.pem"
    - "**/*.key"
    - "**/.env"
    - "**/.env.*"
    - "**/secrets/**"
    - "**/.git/config"
```

### Behavior

1. **Denied paths take precedence**: A path matching both allowed and denied is blocked
2. **Glob matching**: Patterns are matched using Python's `fnmatch`
3. **Path normalization**: Paths are resolved to absolute paths before matching
4. **Symlink protection**: Symlinks are resolved to prevent traversal attacks

## Commands Section

Controls which shell commands can be executed.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `blocked` | list[string] | No | Commands that are never allowed |

### Example

```yaml
commands:
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
```

### Behavior

1. **Command extraction**: The first word of the command is checked
2. **Case-sensitive**: Command names are matched exactly
3. **Dangerous patterns**: Commands containing `|`, `&`, `;`, `>`, `<`, or backticks are blocked

## Tools Section

Controls tool execution behavior.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timeout` | int | No | Execution timeout in seconds (default: 30) |
| `rate_limits` | object | No | Per-tool rate limits |

### Rate Limits

Rate limits are specified as requests per minute:

```yaml
tools:
  timeout: 30
  rate_limits:
    default: 60          # Default for unlisted tools
    web_search: 20       # Specific limit for web_search
    filesystem_write: 30
    command_execute: 10
```

### Behavior

1. **Sliding window**: Rate limits use a 60-second sliding window
2. **Per-tool tracking**: Each tool has its own rate limit counter
3. **Default fallback**: Tools without specific limits use `default`

## Audit Section

Controls audit logging.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `log_file` | string | No | Path to audit log file |
| `log_level` | string | No | Minimum log level (DEBUG, INFO, WARN, ERROR) |
| `include` | list[string] | No | Fields to include in log entries |

### Example

```yaml
audit:
  log_file: "${HOME}/.mcp-secure/audit.log"
  log_level: "INFO"
  include:
    - timestamp
    - request_id
    - tool_name
    - arguments
    - result_status
    - execution_time
    - security_events
```

### Log Format

Logs are written in JSON Lines format:

```json
{"timestamp": "2025-01-15T10:30:00Z", "type": "request", "request_id": "abc123", "tool": "web_search", "arguments": {"query": "***"}}
{"timestamp": "2025-01-15T10:30:01Z", "type": "response", "request_id": "abc123", "status": "success", "duration_ms": 450}
```

### Sensitive Data Redaction

The following patterns are automatically redacted:
- API keys and tokens
- Passwords
- Private keys
- Credit card numbers
- Social security numbers

## Complete Example

```yaml
version: "1.0"

network:
  allowed_ranges:
    - "127.0.0.0/8"
    - "10.0.0.0/8"
    - "172.16.0.0/12"
    - "192.168.0.0/16"

  allowed_endpoints:
    - host: "lite.duckduckgo.com"
      ports: [443]
      description: "DuckDuckGo search"

  blocked_ports:
    - 22

  allow_dns: true
  dns_allowlist:
    - "lite.duckduckgo.com"

filesystem:
  allowed_paths:
    - "${HOME}/projects/**"
    - "/tmp/mcp-workspace/**"

  denied_paths:
    - "**/.ssh/**"
    - "**/.aws/**"
    - "**/*.pem"
    - "**/.env"

commands:
  blocked:
    - "curl"
    - "wget"
    - "ssh"

tools:
  timeout: 30
  rate_limits:
    default: 60
    web_search: 20

audit:
  log_file: "${HOME}/.mcp-secure/audit.log"
  log_level: "INFO"
```
