# NiceGUI Desktop Frontend

pycommence includes a full desktop GUI application built with [NiceGUI](https://nicegui.io/).
It provides a visual interface for browsing, searching, exporting, and managing
Commence database data.

## Quick Start

```bash
# Install with GUI dependencies
pip install pycommence[gui]

# Launch (Commence must be running)
pycommence gui
```

This opens a native desktop window. To run as a web app instead:

```bash
pycommence gui --no-native --port 8080
```

## Pages

### Dashboard

The landing page shows:
- Database name, path, version, and shared status
- A sortable table of all categories with row counts
- Click any category to jump to the **Category Browser**

### Category Browser

Browse data in any category with:
- **Column picker** — select which fields to display
- **Filter builder** — add up to 4 filter clauses (field, qualifier, value)
- **Paginated table** — click any row to open **Record Detail**

### Record Detail

View and edit a single record:
- All fields displayed with type badges (TEXT, DATE, NUMBER, etc.)
- **Edit mode** must be enabled via the header toggle to save changes
- **Open in Commence** button uses DDE to show the item in the native Commence UI
- Connected items grouped by connection name

### Schema Explorer

Inspect database structure:
- Category picker dropdown
- Fields table with type, max chars, default value, and flags
- Connections table (connection name → target category)
- Row count

### Export Dialog

Export data to files:
- Pick category, columns, format (CSV / JSON / Excel)
- Set max rows and canonical mode
- Full backup feature: export all categories with `_schema.json` sidecar

### DDE Console

Power-user tool for raw DDE commands:
- Text input for DDE Request or Execute commands
- Quick-template buttons for common operations
- Response display area

## Architecture

### COM Threading

Commence COM objects are STA-bound — they must be used from the thread
that created them. NiceGUI, however, runs an async event loop.

The `ComWorker` class solves this by spawning a dedicated daemon thread
that owns the `CommenceSession`. All COM calls from the GUI are
dispatched to this thread via `await worker.run(lambda s: ...)`:

```python
# From any async page handler:
name = await worker.run(lambda s: s.db_name)
rows = await worker.run(lambda s: s.read("Contact", max_rows=10))
```

### Edit Safety

Mutations (edit, delete) are disabled by default. The "Edit mode" toggle
in the header must be explicitly enabled. This prevents accidental data
changes while browsing.

## CLI Options

```
Usage: pycommence gui [OPTIONS]

  Launch the NiceGUI desktop frontend.

Options:
  --no-native  Run as a web app instead of a native window.
  --port INT   Server port (0 = auto).
  --reload     Enable hot-reload (for development).
```

