# MCP Server

pycommence includes a built-in [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes your Commence database to LLM agents like Claude, GPT, and Copilot.

## Installation

```bash
pip install pycommence2[mcp]
```

## Quick Start

### Via CLI

```bash
# Start MCP server over stdio (default)
pycommence2 mcp

# Read-only mode (no add/edit/delete tools)
pycommence2 mcp --read-only

# SSE transport for web-based clients
pycommence2 mcp --transport sse --port 8000
```

### Via standalone entry point

```bash
pycommence2-mcp
pycommence2-mcp --read-only
```

## Configuration for Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "commence": {
      "command": "pycommence2-mcp",
      "args": []
    }
  }
}
```

For read-only access:

```json
{
  "mcpServers": {
    "commence": {
      "command": "pycommence2-mcp",
      "args": ["--read-only"]
    }
  }
}
```

## Available Tools

### Read Tools (always available)

| Tool | Description |
|------|-------------|
| `list_categories` | List all category (table) names |
| `get_category_field_names` | Get field names for a category |
| `get_category_field_definitions` | Get field definitions with types and metadata |
| `get_row_count` | Count rows in a category |
| `read_rows` | Read rows with pagination (limit/offset) |
| `read_row_by_pk` | Read a single row by primary key value |
| `search_rows` | Search by field condition (Contains, Equal To, etc.) |
| `get_db_name` | Get database name and path |
| `get_db_info` | Get full database metadata |
| `get_connections` | Get connection definitions for a category |

### Write Tools (disabled with `--read-only`)

| Tool | Description |
|------|-------------|
| `add_row` | Add a new row to a category |
| `edit_row` | Edit a row by its unique ID |
| `delete_row` | Delete a row by its unique ID |
| `assign_connection` | Create a connection between two items |
| `unassign_connection` | Remove a connection between two items |

## Architecture

The MCP server uses `AsyncCommenceSession` internally:

```
┌─────────────────────────────────────┐
│  LLM Agent (Claude, GPT, etc.)      │
├─────────────────────────────────────┤
│  MCP Protocol (stdio or SSE)        │
├─────────────────────────────────────┤
│  FastMCP Server (mcp_server.py)     │
│  ┌───────────────────────────────┐  │
│  │  AsyncCommenceSession          │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  ThreadDispatcher        │  │  │
│  │  │  (COM worker thread)     │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
├─────────────────────────────────────┤
│  Commence Database (COM/DDE)        │
└─────────────────────────────────────┘
```

The async session is lazily initialised on the first tool call, so the server starts quickly even before Commence is ready.

## Programmatic Usage

You can also build and run the server programmatically:

```python
from pycommence2.mcp_server import _build_server

server = _build_server(read_only=True)
server.run(transport="stdio")
```

## Security

!!! warning "Read-only mode recommended"
    When exposing a database to an LLM agent, use `--read-only` mode unless you specifically need write access. LLM agents can make mistakes, and write operations cannot be undone.

## Comparison to External Server

The external [`pycommence-db`](https://github.com/pawrequest/pycommence-db) MCP server was the prototype that validated this approach. The built-in server offers:

- **Zero setup** — no separate package to install
- **Same tool set** — matching the proven external server's tools
- **Write support** — add/edit/delete tools (gated behind `--read-only`)
- **Connection tools** — assign/unassign connections
- **Single process** — no IPC overhead

