# Async Session

pycommence provides `AsyncCommenceSession` for use in async frameworks like FastAPI, NiceGUI, or any `asyncio`-based application.

## The Problem

Commence COM objects are **STA-bound** (Single Threaded Apartment) — they must be created and called from the same thread. This conflicts with `asyncio`, which runs code on an event loop and must never block.

## The Solution

`AsyncCommenceSession` manages a dedicated background thread that owns the COM connection. Every method dispatches work to that thread and returns an awaitable result. Your async code never blocks and COM rules are respected.

```
┌─────────────────────────────┐
│   Your async code (await)   │
├─────────────────────────────┤
│    AsyncCommenceSession     │
│    ┌─────────────────────┐  │
│    │  ThreadDispatcher    │  │
│    │  (queue + Future)    │  │
│    └────────┬────────────┘  │
│             │               │
│    ┌────────▼────────────┐  │
│    │  COM Worker Thread   │  │
│    │  (CommenceSession)   │  │
│    └─────────────────────┘  │
└─────────────────────────────┘
```

## Installation

No extra dependencies — `AsyncCommenceSession` uses only the Python standard library (`asyncio`, `threading`, `queue`).

```bash
pip install pycommence
```

## Quick Start

```python
import asyncio
from pycommence import AsyncCommenceSession

async def main():
    async with AsyncCommenceSession() as db:
        # Database info
        name = await db.db_name()
        print(f"Connected to: {name}")

        # Read rows
        rows = await db.read("Contact", columns=["Name", "Email"], max_rows=10)
        for row in rows:
            print(row["Name"], row["Email"])

        # Fluent query (built and executed in one call)
        results = await db.query(
            "Contact",
            columns=["Name", "Email"],
            filters=[("Name", "Contains", "Smith")],
            sort="Name",
            limit=20,
        )

asyncio.run(main())
```

## API Overview

`AsyncCommenceSession` mirrors the sync `CommenceSession` API. Every method is `async` and returns an awaitable:

### Database Metadata

```python
name = await db.db_name()
path = await db.db_path()
version = await db.db_version()
shared = await db.db_shared()
```

### Schema

```python
categories = await db.list_categories()
fields = await db.get_fields("Contact")
connections = await db.get_connections("Contact")
count = await db.get_row_count("Contact")
```

### Read

```python
# Simple read
rows = await db.read("Contact", columns=["Name", "Email"], max_rows=10)

# Read by ID
row = await db.read_by_id("Contact", row_id)

# Query with filters
results = await db.query(
    "Contact",
    columns=["Name", "Email"],
    filters=[("City", "Equal To", "Boston")],
    limit=50,
    canonical=True,
)

# Count
n = await db.count("Contact", filters=[("Status", "Equal To", "Active")])
```

### Create / Update / Delete

```python
# Add
row_id = await db.add("Contact", {"Name": "Jane Doe", "Email": "jane@example.com"})
count = await db.add_many("Contact", [{"Name": "A"}, {"Name": "B"}])

# Edit
await db.edit(row_id, "Contact", {"Email": "new@example.com"})
count = await db.edit_where("Contact", {"Status": "Inactive"}, filters=[...])

# Delete
await db.delete(row_id, "Contact")
count = await db.delete_where("Contact", filters=[...])
```

### Connections

```python
await db.assign_connection("Person", "John", "Relates to", "Company", "Acme")
await db.unassign_connection("Person", "John", "Relates to", "Company", "Acme")
```

### Export / Import

```python
count = await db.export("Contact", "contacts.csv")
stats = await db.backup("./backup")
result = await db.import_csv("Contact", "data.csv")
result = await db.import_json("Contact", "data.json")
```

### DDE Shortcuts

```python
email = await db.dde_get_field("Contact", "Jane Doe", "Email")
await db.dde_show_item("Contact", "Jane Doe")
await db.dde_fire_trigger("Nightly Sync")
```

## Escape Hatch: `run()`

For operations not covered by the convenience methods, use `run()` to execute any callable on the COM thread:

```python
async with AsyncCommenceSession() as db:
    # Access sub-services directly
    fields = await db.run(lambda s: s.schema.get_fields("Contact"))

    # Complex query builder
    results = await db.run(lambda s: (
        s.query("Contact")
        .columns("Name", "Email")
        .where("Name", "Contains", "Smith")
        .related_column("Relates to", "Company", "Phone")
        .sort("Name")
        .limit(50)
        .execute()
    ))
```

## Use with FastAPI

```python
from fastapi import FastAPI
from pycommence import AsyncCommenceSession

app = FastAPI()
db: AsyncCommenceSession | None = None

@app.on_event("startup")
async def startup():
    global db
    db = AsyncCommenceSession()
    await db.__aenter__()

@app.on_event("shutdown")
async def shutdown():
    if db:
        await db.__aexit__(None, None, None)

@app.get("/contacts")
async def get_contacts(limit: int = 20):
    rows = await db.read("Contact", columns=["Name", "Email"], max_rows=limit)
    return [row.to_dict() for row in rows]
```

## Lifecycle

You can use `AsyncCommenceSession` as an async context manager or manage it manually:

```python
# Context manager (recommended)
async with AsyncCommenceSession() as db:
    ...

# Manual lifecycle
db = AsyncCommenceSession()
db.start()          # spawns COM thread synchronously
...
db.stop()           # shuts down COM thread
```

## Thread Safety

`AsyncCommenceSession` is safe to use from any async task — all COM operations are serialised on the dedicated worker thread. However, you should only create **one** `AsyncCommenceSession` per application (it creates one COM connection to Commence).

