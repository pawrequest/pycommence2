# Export & Import

pycommence provides comprehensive export and import capabilities for moving
data in and out of Commence databases.

## Exporting Data

### Quick Export via Session

The easiest way to export data is the `session.export()` convenience method:

```python
from pycommence import CommenceSession

with CommenceSession() as db:
    # Auto-detect format from extension
    db.export("Contact", "contacts.csv")
    db.export("Hire", "hires.json", max_rows=5000)
    db.export("Account", "data.xlsx")  # requires openpyxl

    # With filters and column selection
    db.export(
        "Contact", "boston_contacts.csv",
        columns=["Name", "Email", "Phone"],
        filters=['[ViewFilter(1, F, , "City", "Equal To", "Boston", False)]'],
    )
```

### ExportService for Fine-Grained Control

For more control, use the `ExportService` directly:

```python
with CommenceSession() as db:
    rows = db.read("Contact", max_rows=1000, canonical=True)

    # CSV with specific columns
    db.export_service.to_csv(rows, "partial.csv", columns=["Name", "Email"])

    # JSON with type coercion
    fields = db.schema.get_fields("Contact")
    db.export_service.to_json(
        rows, "typed.json", typed=True, fields=fields,
    )

    # Excel with custom sheet name
    db.export_service.to_excel(rows, "report.xlsx", sheet_name="Contacts")
```

### Supported Formats

| Format | Extension | Extra Required | Notes |
|--------|-----------|----------------|-------|
| CSV    | `.csv`    | None           | UTF-8 BOM for Excel compatibility |
| JSON   | `.json`   | None           | Array of objects, optional type coercion |
| Excel  | `.xlsx`   | `openpyxl`     | `pip install pycommence[export]` |

## Backup & Restore

### Full Database Backup

The `backup()` method exports all (or selected) categories to a directory
with a schema metadata sidecar:

```python
with CommenceSession() as db:
    stats = db.backup("./backup_2026-04-11")
    print(f"Exported {stats['categories_exported']} categories")
    print(f"Total rows: {stats['total_rows']}")
```

This creates:

```
backup_2026-04-11/
  _manifest.json      # summary of the backup
  _schema.json        # field/connection definitions for all categories
  Contact.json        # data for each category
  Hire.json
  Account.json
  ...
```

### Selective Backup

```python
with CommenceSession() as db:
    db.backup(
        "./partial_backup",
        categories=["Contact", "Hire"],
        max_rows_per_category=10_000,
    )
```

## Importing Data

### From CSV

```python
with CommenceSession() as db:
    # Direct import — CSV headers match Commence field names
    result = db.import_csv("Contact", "contacts.csv")
    print(f"Imported {result['rows_imported']} / {result['rows_parsed']} rows")

    # With field mapping
    result = db.import_csv(
        "Contact", "external_data.csv",
        field_map={"full_name": "Name", "email_addr": "Email"},
    )
```

### From JSON

```python
with CommenceSession() as db:
    result = db.import_json("Contact", "contacts.json")
```

### Dry Run

Validate data before committing:

```python
with CommenceSession() as db:
    result = db.import_csv("Contact", "data.csv", dry_run=True)
    print(f"Would import {result['rows_parsed']} rows")
    # No data written
```

## CLI Commands

### Export

```bash
# CSV export
pycommence export Contact contacts.csv

# JSON with row limit
pycommence export Hire hires.json --limit 1000

# Excel with specific columns
pycommence export Account data.xlsx --columns "Name,Email,Phone"

# With filter
pycommence export Contact filtered.csv --filter "City:Equal To:Boston"
```

### Backup

```bash
# Full database backup
pycommence backup ./my_backup

# Selective backup
pycommence backup ./partial --categories "Contact,Hire"
```

### Import

```bash
# Import from CSV
pycommence import Contact contacts.csv

# Dry run (validate only)
pycommence import Hire hires.json --dry-run

# Import with row limit
pycommence import Account data.csv --limit 100
```

