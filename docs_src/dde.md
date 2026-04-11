# DDE Operations

The `DdeService` provides access to Commence DDE Execute and Request commands that are not covered by the cursor/rowset API. These are useful for:

- Single-item CRUD (simpler than cursor path for one-off operations)
- UI control (open forms, switch views)
- Firing triggers/agents
- Reading individual field values

## When to Use DDE vs Cursor

| Operation | Use DDE | Use Cursor |
|-----------|---------|------------|
| Read one field from one item | ✅ `dde.get_field()` | Overkill |
| Read 1000 rows | Slow | ✅ `session.read()` |
| Add one item by name | ✅ `dde.add_item()` | ✅ `session.add()` |
| Add 100 items | Slow | ✅ `session.add_many()` |
| Edit one field on one item | ✅ `dde.edit_item()` | ✅ `session.edit()` |
| Assign a connection | ✅ `connections.assign()` | Not possible |
| Open an item in Commence UI | ✅ `dde.show_item()` | Not possible |
| Fire a trigger/agent | ✅ `dde.fire_trigger()` | Not possible |
| Schema introspection | ✅ `schema.*` (uses DDE internally) | N/A |

## Accessing the DDE Service

```python
with CommenceSession() as db:
    dde = db.dde
```

## Item CRUD via DDE

### Add an item

```python
with CommenceSession() as db:
    db.dde.add_item("Contact", "Jane Doe")

    # With clarify value (for categories that allow duplicate names)
    db.dde.add_item("Contact", "Jane Doe", clarify_value="Boston")
```

### Edit a single field

```python
with CommenceSession() as db:
    db.dde.edit_item("Contact", "Jane Doe", "Email", "jane@example.com")
```

### Delete an item

```python
with CommenceSession() as db:
    db.dde.delete_item("Contact", "Jane Doe")
```

### Append text to a field

Useful for Notes or other large text fields:

```python
with CommenceSession() as db:
    db.dde.append_text("Contact", "Jane Doe", "Notes", "\n2026-04-11: Called back.")
```

## Reading Fields

### Single field

```python
with CommenceSession() as db:
    email = db.dde.get_field("Contact", "Jane Doe", "Email")
    print(email)
```

### Multiple fields at once

```python
with CommenceSession() as db:
    values = db.dde.get_fields("Contact", "Jane Doe", "Name", "Email", "Phone")
    print(values)  # ["Jane Doe", "jane@example.com", "555-0100"]
```

### Save field to file

```python
with CommenceSession() as db:
    db.dde.get_field_to_file("Contact", "Jane Doe", "Photo", "C:\\photos\\jane.jpg")
```

## Item Enumeration

### List all item names

```python
with CommenceSession() as db:
    names = db.dde.get_item_names("Contact")
    for name in names:
        print(name)
```

### Count items

```python
with CommenceSession() as db:
    count = db.dde.get_item_count("Contact")
    print(f"{count} contacts")
```

## UI Commands

### Open an item's detail form

```python
with CommenceSession() as db:
    db.dde.show_item("Contact", "Jane Doe")

    # Open with a specific form
    db.dde.show_item("Contact", "Jane Doe", form_name="Contact Detail")
```

### Open a view

```python
with CommenceSession() as db:
    db.dde.show_view("Active Contacts")
```

## Triggers

Fire a named Commence agent/trigger:

```python
with CommenceSession() as db:
    db.dde.fire_trigger("Nightly Sync")
```

## Database Metadata

```python
with CommenceSession() as db:
    info = db.dde.get_database_definition()
    print(info)
    # {"name": "Radios", "path": "C:\\...", "version": "...",
    #  "registered_user": "...", "shared": "0"}
```

