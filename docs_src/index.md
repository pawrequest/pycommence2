# pycommence-vibes

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
- [API Reference](api/session.md) — full API documentation

