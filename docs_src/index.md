# pycommence

A clean, modern Python library for **Commence database** CRUD operations and schema introspection via COM automation.

## Features

- **Single entry point** — `CommenceSession` is all you need
- **Fluent queries** — chainable `QueryBuilder` with `.where()`, `.sort()`, `.limit()`
- **Full CRUD** — add, read, edit, delete rows with one-liner shortcuts
- **Schema introspection** — list categories, fields, connections, views, forms
- **Connection management** — assign/unassign item relationships via DDE
- **DDE operations** — direct DDE execute/request for UI control, triggers, and more
- **View cursors** — query against saved Commence views
- **Related columns** — pull connected/indirect fields into query results
- **Canonical mode** — locale-independent data format for dates, numbers, booleans
- **Export & Import** — CSV, JSON, and Excel export/import with backup support
- **CLI** — `click` + `rich` command-line interface for read, schema, export, backup, import
- **GUI** — NiceGUI desktop app for browsing, searching, exporting, and managing data
- **Async support** — `AsyncCommenceSession` for use in `asyncio` frameworks (FastAPI, NiceGUI, etc.)

## Quick Example

```python
from pycommence import CommenceSession

with CommenceSession() as db:
    # Read 10 contacts
    rows = db.read("Contact", columns=["Name", "Email"], max_rows=10)
    for row in rows:
        print(row["Name"], row["Email"])

    # Fluent query
    results = (
        db.query("Contact")
        .columns("Name", "Email", "Phone")
        .where("Name", "Contains", "Smith")
        .sort("Name")
        .limit(20)
        .execute()
    )
```

## Requirements

| Requirement | Details |
|-------------|---------|
| **Python** | 3.13+ |
| **OS** | Windows (COM automation) |
| **Commence** | Must be running with a database open |

## Next Steps

- [Getting Started](getting-started.md) — install and run your first script
- [Architecture](architecture.md) — understand the layer design
- [CLI Reference](cli.md) — command-line tools
- [GUI](gui.md) — desktop frontend
- [Async Session](async.md) — use with asyncio frameworks
- [API Reference](api/session.md) — full API documentation

