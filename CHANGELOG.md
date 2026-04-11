# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- `[project.scripts]` entry point changed from `pycommence-vibes` → `pycommence`.
- `main()` in `__init__.py` now delegates to the click CLI group.

## [0.2.2] — 2026-04-11

### Added
- **Persistent schema cache** — `SchemaCache` with disk-backed JSON storage under `platformdirs.user_cache_dir()`. METADATA.PIM mtime used as primary staleness sentinel. Transparent integration in `SchemaService` — `get_fields()`, `get_connection_names()`, and `list_categories()` now cache to disk automatically.
- **`RowResult` ergonomics** — `__contains__`, `__iter__`, `__len__`, `keys()`, `values()`, `items()`, `to_dict()`, `to_typed_dict(fields)` for dict-like usage and automatic type coercion of canonical-mode data.
- **`__version__`** — exposed via `importlib.metadata` (`from pycommence_vibes import __version__`).
- **`logic` parameter** threaded through `edit_where()` / `delete_where()` (session and writer) for combining filter clauses on mutations.
- `project.urls` in `pyproject.toml` (Homepage, Docs, Repository, Changelog).
- `platformdirs>=4.0` dependency for cross-platform cache directory resolution.
- MIT `LICENSE` file.
- `py.typed` marker for PEP 561 type-checker support.
- `SchemaService.invalidate_cache()` method for explicit cache invalidation.

### Changed
- Version bumped to 0.2.2.
- `SchemaService.__init__` now creates a `SchemaCache` and runs staleness detection on startup.

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

