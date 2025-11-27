# MCP Protocol Reference

This document describes the Model Context Protocol (MCP) implementation in this server.

## Protocol Version

This server implements MCP protocol version `2025-11-25`.

## Transport

The server uses STDIO (standard input/output) transport:

- **Input**: JSON-RPC messages are read from stdin, one per line
- **Output**: Responses are written to stdout, one per line
- **Logging**: Diagnostic messages go to stderr

## Message Format

All messages follow JSON-RPC 2.0 format.

### Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "method/name",
  "params": { ... }
}
```

### Response (Success)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { ... }
}
```

### Response (Error)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  }
}
```

### Notification

Notifications have no `id` field and receive no response:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

## Lifecycle

### Connection Flow

```
Client                           Server
  |                                 |
  |  ---- initialize ------------>  |
  |  <--- result (capabilities) --  |
  |                                 |
  |  ---- notifications/initialized |
  |                                 |
  |  ---- tools/list ------------>  |
  |  <--- result (tools) ---------  |
  |                                 |
  |  ---- tools/call ------------>  |
  |  <--- result -----------------  |
  |                                 |
```

### Initialize

Establishes the connection and exchanges capabilities.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "clientInfo": {
      "name": "my-client",
      "version": "1.0.0"
    },
    "capabilities": {}
  }
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-11-25",
    "serverInfo": {
      "name": "mcp-secure-local",
      "version": "1.0.0"
    },
    "capabilities": {
      "tools": {
        "listChanged": true
      }
    }
  }
}
```

### Initialized Notification

Sent by client after receiving initialize response:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

## Tools

### tools/list

List all available tools.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "The search query"
            },
            "max_results": {
              "type": "integer",
              "description": "Maximum results (default: 5)"
            }
          },
          "required": ["query"]
        }
      }
    ]
  }
}
```

### tools/call

Execute a tool.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "web_search",
    "arguments": {
      "query": "MCP protocol",
      "max_results": 3
    }
  }
}
```

**Response (Success):**

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Search results for: MCP protocol\n\n1. ..."
      }
    ],
    "isError": false
  }
}
```

**Response (Tool Error):**

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Search error: Network timeout"
      }
    ],
    "isError": true
  }
}
```

## Error Codes

Standard JSON-RPC 2.0 error codes:

| Code | Message | Description |
|------|---------|-------------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid Request | Not a valid request object |
| -32601 | Method not found | Unknown method |
| -32602 | Invalid params | Invalid method parameters |
| -32603 | Internal error | Server error |

## Content Types

Tool results can include these content types:

### Text

```json
{
  "type": "text",
  "text": "Hello, world!"
}
```

### Image (Base64)

```json
{
  "type": "image",
  "data": "base64-encoded-data",
  "mimeType": "image/png"
}
```

### Resource

```json
{
  "type": "resource",
  "uri": "file:///path/to/file",
  "mimeType": "text/plain",
  "text": "file contents"
}
```

## Example Session

Complete example of a client session:

```
→ {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","clientInfo":{"name":"test","version":"1.0"},"capabilities":{}}}
← {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-11-25","serverInfo":{"name":"mcp-secure-local","version":"1.0.0"},"capabilities":{"tools":{"listChanged":true}}}}
→ {"jsonrpc":"2.0","method":"notifications/initialized"}
→ {"jsonrpc":"2.0","id":2,"method":"tools/list"}
← {"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"web_search","description":"Search the web using DuckDuckGo","inputSchema":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}]}}
→ {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"web_search","arguments":{"query":"hello"}}}
← {"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"Search results for: hello\n..."}],"isError":false}}
```

## Security Notes

1. **Pre-initialization**: Only `initialize` is allowed before handshake completes
2. **Unknown methods**: Return error code -32601
3. **Tool errors**: Returned as results with `isError: true`, not JSON-RPC errors
4. **Rate limiting**: Excessive requests may be rejected
5. **Validation**: All tool inputs are validated against their schemas
