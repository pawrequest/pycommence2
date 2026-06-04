# Getting Started

## Installation

Install with [uv](https://docs.astral.sh/uv/):

```bash
uv add pycommence2
```

Or with pip:

```bash
pip install pycommence2
```

### Optional Extras

pycommence has optional dependency groups for additional features:

```bash
# Command-line interface (click + rich)
pip install pycommence2[cli]

# NiceGUI desktop frontend
pip install pycommence2[gui]

# Excel export support (openpyxl)
pip install pycommence2[export]

# MCP server for LLM agent access
pip install pycommence2[mcp]

# Install everything
pip install pycommence2[cli,gui,export,mcp]
```

## Prerequisites

1. **Windows** — Commence uses COM automation, which is Windows-only.
2. **Commence must be running** with a database open before you create a `CommenceSession`.
3. **Python 3.13+** is required.

## Hello World

```python
from pycommence2 import CommenceSession, __version__

print(f"pycommence2 {__version__}")

with CommenceSession() as db:
    print(f"Connected to: {db.db_name}")
    print(f"Path: {db.db_path}")
    print(f"Version: {db.db_version}")
    print(f"Shared: {db.db_shared}")

    # List all categories (tables) in the database
    for cat in db.schema.list_categories():
        print(f"  {cat}")
```

## Basic CRUD

### Read rows

```python
with CommenceSession() as db:
    # Read with column selection and limit
    rows = db.read("Contact", columns=["Name", "Email"], max_rows=10)
    for row in rows:
        print(row["Name"], row["Email"])
```

### Add a row

```python
with CommenceSession() as db:
    new_id = db.add("Contact", {
        "Name": "Jane Doe",
        "Email": "jane@example.com",
    })
    print(f"Created row: {new_id}")
```

### Edit a row

```python
with CommenceSession() as db:
    db.edit(row_id, "Contact", {"Email": "jane.doe@example.com"})
```

### Delete a row

```python
with CommenceSession() as db:
    db.delete(row_id, "Contact")
```

## Fluent Queries

The `QueryBuilder` provides a chainable interface for complex reads:

```python
with CommenceSession() as db:
    results = (
        db.query("Contact")
        .columns("Name", "Email", "Phone")
        .where("Name", "Contains", "Smith")
        .sort("Name")
        .limit(20)
        .execute()
    )
    for row in results:
        print(row["Name"])
```

## Async Usage

Use `AsyncCommenceSession` for async frameworks (FastAPI, NiceGUI, etc.):

```python
import asyncio
from pycommence2 import AsyncCommenceSession


async def main():
    async with AsyncCommenceSession() as db:
        name = await db.db_name()
        print(f"Connected to: {name}")

        rows = await db.read("Contact", columns=["Name", "Email"], max_rows=10)
        for row in rows:
            print(row["Name"], row["Email"])


asyncio.run(main())
```

## What's Next?

- [Architecture](architecture.md) — understand the three-layer design
- [Query & Filtering](querying.md) — deep dive into filters, sorts, and the query builder
- [Connections](connections.md) — manage item relationships
- [DDE Operations](dde.md) — direct DDE commands for UI control and more
- [Export & Import](export-import.md) — CSV, JSON, Excel export/import and backup
- [CLI Reference](cli.md) — command-line tools
- [GUI](gui.md) — NiceGUI desktop frontend
- [Async Session](async.md) — use with asyncio / FastAPI
- [MCP Server](mcp.md) — expose Commence to LLM agents
- [API Reference](api/session.md) — full API docs

