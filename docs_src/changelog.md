# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] — 2026-04-11

### Added
- **NiceGUI Desktop Frontend** — full GUI application launched via `pycommence gui`:
  - **Dashboard** — database info (name, path, version, shared status), category list with row counts, click-to-browse navigation.
  - **Category Browser** — server-side paginated table with column picker, interactive filter builder (up to 4 clauses), click-through to record detail.
  - **Record Detail** — view/edit individual rows with field type badges, save changes (requires edit-mode toggle), show connected items by connection, open item in Commence via DDE.
  - **Schema Explorer** — category picker with fields table (name, type, max chars, flags) and connections table.
  - **Export Dialog** — pick category, columns, format (CSV/JSON/Excel), max rows, output path; also includes full-backup UI with schema sidecar.
  - **DDE Console** — raw DDE Request/Execute with quick-template buttons and response display. Power-user tool.
- **COM Worker Thread** (`gui/state.py`) — dedicated daemon thread that owns the `CommenceSession`, bridges NiceGUI's async event loop with Commence's STA-bound COM via `await worker.run(lambda s: ...)`.
- **Edit-mode safety toggle** — mutations disabled by default; explicit "Edit mode" switch in the header prevents accidental data changes.
- **`pycommence gui` CLI command** — supports `--no-native`, `--port`, `--reload` options.
- `gui` optional dependency group: `nicegui>=2.0`, `pywebview>=5.0`.

### Changed
- Version bumped to 0.4.0.

## [0.3.1] — 2026-04-11

### Added
- **ExportService** — `to_csv()`, `to_json()`, `to_excel()` for writing `RowResult` data to files:
  - CSV with BOM-encoded UTF-8 for Excel compatibility.
  - JSON with optional type coercion via `to_typed_dict()`.
  - Excel via optional `openpyxl` dependency.
  - `detect_format()` helper auto-detects format from file extension.
- **BackupService** — full-database snapshot to a directory:
  - One JSON file per category.
  - `_schema.json` sidecar with field/connection definitions.
  - `_manifest.json` summary file.
  - Selective category backup via `categories` parameter.
- **ImportService** — `from_csv()` and `from_json()` to load data into Commence:
  - Field mapping support (`csv_column → commence_field`).
  - Dry-run mode for validation without writes.
  - Batched inserts for reliable large imports.
- **Session convenience methods**: `session.export()`, `session.backup()`, `session.import_csv()`, `session.import_json()`.
- **CLI commands**:
  - `pycommence export <category> <outfile>` — export to CSV/JSON/Excel with `--columns`, `--filter`, `--limit`, `--format`, `--canonical`.
  - `pycommence backup <output_dir>` — backup categories with schema sidecar.
  - `pycommence import <category> <infile>` — import from CSV/JSON with `--dry-run`, `--limit`.
- `export` optional dependency group: `openpyxl>=3.1` (for Excel export).

### Changed
- Version bumped to 0.3.1.
- CLI `export` command now fully functional (was a stub in v0.3.0).

## [0.3.0] — 2026-04-11

### Added
- **CLI** — `pycommence` command-line interface powered by `click` + `rich`:
  - `pycommence info` — database name, path, version, shared status
  - `pycommence schema` — list all categories with row counts
  - `pycommence schema <category>` — show fields, connections, and row count
  - `pycommence read <category>` — read rows with `--columns`, `--filter`, `--limit`, `--format` (table/json/csv), `--canonical`
  - `pycommence count <category>` — row count with optional `--filter`
  - `pycommence export` / `pycommence gui` — stub commands for future phases
- `cli` optional dependency group: `click>=8.0`, `rich>=13.0`.
- Filter syntax for CLI: `FIELD:QUALIFIER:VALUE` (colon-delimited).

### Changed
- Version bumped to 0.3.0.

## [0.2.2] — 2026-04-11

### Added
- **Persistent schema cache** — `SchemaCache` with disk-backed JSON storage under `platformdirs.user_cache_dir()`. METADATA.PIM mtime used as primary staleness sentinel. Transparent integration in `SchemaService`.
- **`RowResult` ergonomics** — `__contains__`, `__iter__`, `__len__`, `keys()`, `values()`, `items()`, `to_dict()`, `to_typed_dict(fields)` for dict-like usage and automatic type coercion of canonical-mode data.
- **`__version__`** — exposed via `importlib.metadata` (`from pycommence import __version__`).
- **`logic` parameter** threaded through `edit_where()` / `delete_where()` for combining filter clauses on mutations.
- `project.urls` in `pyproject.toml` (Homepage, Docs, Repository, Changelog).
- `platformdirs>=4.0` dependency for cross-platform cache directory resolution.
- MIT `LICENSE` file.
- `py.typed` marker for PEP 561 type-checker support.

### Changed
- Version bumped to 0.2.2.

## [0.2.1] — 2026-04-11

### Added
- MkDocs documentation site with Material theme
- API reference auto-generated from docstrings via mkdocstrings
- User guide pages: Getting Started, Architecture, Query & Filtering, Connections, DDE Operations, Canonical Mode, FAQ
- CHANGELOG.md
- Expanded docstrings with Args/Returns/Raises/Example sections on all public methods
- README examples for view cursors, related columns, canonical mode, DDE operations, and connections

## [0.2.0] — 2026-04-10

### Added
- **View cursors** — `session.query_view(view_name)` creates a `QueryBuilder` backed by a saved Commence view, inheriting its filter, sort, and column set
- **Related columns** — `QueryBuilder.related_column(connection, category, field)` pulls connected/indirect fields into query results via `SetRelatedColumn`
- **Canonical mode** — `session.read(..., canonical=True)` and `QueryBuilder.canonical()` return dates as `yyyymmdd`, times as `hh:mm`, numbers without locale formatting, and checkboxes as `TRUE`/`FALSE`
- **ConnectionService** — `session.connections.assign()`, `.unassign()`, `.get_connected_item_names()`, `.get_connected_item_count()`, `.get_connected_item_field()` for managing Commence connections via DDE
- **DdeService** — `session.dde` exposes DDE Execute/Request commands: `add_item`, `edit_item`, `delete_item`, `append_text`, `get_field`, `get_fields`, `get_field_to_file`, `get_item_names`, `get_item_count`, `show_item`, `show_view`, `fire_trigger`, `get_database_definition`
- **Session shortcuts** — `session.assign_connection()` and `session.unassign_connection()` convenience methods
- **COM retry decorator** — `_com/retry.py` with `@com_retry` for transient COM failure recovery
- **Thread-safety warnings** — `CommenceDB._check_thread()` logs a warning when COM objects are accessed from a non-init thread
- **Filter logic** — `session.read()` now accepts `logic` parameter for combining filter clauses
- **QueryBuilder.count()** — respects accumulated filters and logic
- `CommenceDB.close()` guard against double-close
- `RowsetWrapper.commit_get_cursor()` — wraps `CommitGetCursor` COM method
- `CursorWrapper` view-linking methods: `set_active_item()`, `set_active_date()`, `set_active_date_range()`
- `CursorWrapper.seek_row_approx()` — approximate cursor positioning
- `RowsetWrapper.get_field_to_file()` — save field value to disk
- New exports in `__init__.py`: `RelatedColumn`, `ConnectionService`, `DdeService`
- New tests: `test_connections.py`, `test_dde.py`, `test_view_cursor.py`

### Changed
- `WriterService.add_row()` now uses wrapped `commit_get_cursor()` instead of raw COM access
- `SchemaService.get_category_definition()` flag parsing hardened with named positions and `SchemaError` on failure

### Fixed
- `QueryBuilder.count()` was ignoring accumulated filters — now passes filters and logic to `ReaderService.count()`
- `set_columns_all()` documented as no-op for category cursors, clarified usage

### Removed
- Dead code: `FilterClause.to_filter_string()` and `SortSpec.to_sort_string()` methods

## [0.1.0] — 2026-04-01

### Added
- Initial release
- `CommenceSession` — single public entry point with context manager
- `SchemaService` — list categories, fields, connections, views, forms via DDE
- `ReaderService` — read rows with filtering, sorting, column selection, pagination
- `WriterService` — add, edit, delete rows via cursor/rowset API
- `QueryBuilder` — fluent chainable query interface
- `_com/` layer — COM wrappers for `ICommenceDB`, `ICommenceCursor`, `ICommenceQueryRowSet`, `ICommenceConversation`
- Data models: `FieldInfo`, `FieldType`, `ConnectionInfo`, `CategoryInfo`, `RowResult`, `FilterClause`, `SortSpec`
- Exception hierarchy: `CommenceError`, `CommenceNotFoundError`, `CursorError`, `RowsetError`, `SchemaError`, `ConversationError`, `FilterError`
