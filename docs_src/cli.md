# CLI Reference

pycommence includes a command-line interface powered by [click](https://click.palletsprojects.com/) and [rich](https://rich.readthedocs.io/) for working with Commence databases from the terminal.

## Installation

The CLI requires the `cli` optional extra:

```bash
pip install pycommence[cli]
# or
uv add pycommence[cli]
```

## Global Options

```
Usage: pycommence [OPTIONS] COMMAND [ARGS]...

  pycommence — Commence database tools from the command line.

Options:
  -v, --verbose  Enable debug logging.
  --help         Show this message and exit.
```

## Commands

### `info`

Show database name, path, version, and shared status.

```bash
pycommence info
```

Example output:

```
┌─────────────────────┐
│ Commence Database    │
├──────────┬──────────┤
│ Name     │ Radios   │
│ Path     │ C:\...   │
│ Version  │ 6.0.0    │
│ Shared   │ No       │
└──────────┴──────────┘
```

### `schema`

List all categories, or show fields and connections for a specific category.

```bash
# List all categories with row counts
pycommence schema

# Show fields and connections for a category
pycommence schema Contact
```

When given a category name, the output includes:

- **Fields table** — name, type, max chars, and flags (mandatory, combo, shared, recurring)
- **Connections table** — connection name and target category
- **Row count**

### `read`

Read rows from a category with optional filtering, column selection, and output formatting.

```bash
pycommence read <CATEGORY> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-c, --columns TEXT` | Comma-separated column names to include |
| `-f, --filter TEXT` | Filter as `FIELD:QUALIFIER:VALUE` (repeatable) |
| `-l, --limit INT` | Maximum rows to return (default: 50) |
| `--format [table\|json\|csv]` | Output format (default: table) |
| `--canonical` | Use canonical (locale-independent) formatting |

**Examples:**

```bash
# Read 20 contacts as a rich table
pycommence read Contact --limit 20

# Read specific columns as JSON
pycommence read Contact -c "Name,Email,Phone" --format json

# Filter by name, output as CSV
pycommence read Contact -f "Name:Contains:Smith" --format csv

# Multiple filters (AND logic)
pycommence read Hire -f "Status:Equal To:Active" -f "City:Contains:London"

# Canonical mode for locale-independent data
pycommence read Hire -c "Name,Booked Date,Price" --canonical --format json
```

### Filter Syntax

Filters use a colon-delimited format: `FIELD:QUALIFIER:VALUE`

The value portion may itself contain colons — only the first two colons are treated as delimiters.

Supported qualifiers: `Contains`, `Equal To`, `Not Equal To`, `After`, `Before`, `Greater Than`, `Less Than`, `Blank`, `Not Blank`, `Checked`, `Not Checked`, and more. See [Query & Filtering](querying.md#supported-qualifiers) for the full list.

### `count`

Count rows in a category, optionally filtered.

```bash
# Total rows
pycommence count Contact

# Filtered count
pycommence count Hire -f "Status:Equal To:Active"
```

### `export`

Export a category to a file (CSV, JSON, or Excel).

```bash
pycommence export <CATEGORY> <OUTFILE> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-c, --columns TEXT` | Comma-separated column names |
| `-f, --filter TEXT` | Filter as `FIELD:QUALIFIER:VALUE` (repeatable) |
| `-l, --limit INT` | Maximum rows to export (default: 50,000) |
| `--format [csv\|json\|excel]` | Format (auto-detected from extension if omitted) |
| `--canonical / --no-canonical` | Canonical formatting (default: on) |

**Examples:**

```bash
# CSV export (format auto-detected from .csv extension)
pycommence export Contact contacts.csv

# JSON with row limit
pycommence export Hire hires.json --limit 1000

# Excel with specific columns
pycommence export Account data.xlsx --columns "Name,Email,Phone"

# With filter
pycommence export Contact filtered.csv --filter "City:Equal To:Boston"
```

!!! note
    Excel export requires the `export` extra: `pip install pycommence[export]`

### `backup`

Backup categories to a directory with schema metadata.

```bash
pycommence backup <OUTPUT_DIR> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-c, --categories TEXT` | Comma-separated category names (default: all) |
| `-l, --limit INT` | Maximum rows per category (default: 50,000) |
| `--canonical / --no-canonical` | Canonical formatting (default: on) |

**Examples:**

```bash
# Full database backup
pycommence backup ./my_backup

# Selective backup
pycommence backup ./partial --categories "Contact,Hire"
```

The backup directory contains:

- One JSON file per category (e.g. `Contact.json`, `Hire.json`)
- `_schema.json` — field and connection definitions
- `_manifest.json` — backup summary

### `import`

Import rows from a file into a category.

```bash
pycommence import <CATEGORY> <INFILE> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--dry-run` | Parse and validate without writing data |
| `-l, --limit INT` | Maximum rows to import |

Supports CSV (`.csv`) and JSON (`.json`) files. CSV column headers must match Commence field names (or use the Python API's `field_map` for custom mapping).

**Examples:**

```bash
# Import from CSV
pycommence import Contact contacts.csv

# Dry run — validate only, no writes
pycommence import Hire hires.json --dry-run

# Import with row limit
pycommence import Account data.csv --limit 100
```

### `gui`

Launch the NiceGUI desktop frontend.

```bash
pycommence gui [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--no-native` | Run as a web app instead of a native window |
| `--port INT` | Server port (0 = auto) |
| `--reload` | Enable hot-reload (for development) |

**Examples:**

```bash
# Launch as desktop app
pycommence gui

# Launch as web app on port 8080
pycommence gui --no-native --port 8080
```

!!! note
    Requires the `gui` extra: `pip install pycommence[gui]`

See [GUI](gui.md) for full documentation on the desktop frontend.

