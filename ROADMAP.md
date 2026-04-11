# pycommence-vibes — Development Roadmap

> Post-v0.2.0 plan.  Everything in [PLAN-v0.2.0.md](PLAN-v0.2.0.md) is shipped.

## Why this order?

| # | Phase | Rationale |
|---|-------|-----------|
| 1 | **Documentation** | Locks the public API. Exposes naming inconsistencies *before* anyone builds on them. Enables contributors. Zero new runtime deps. |
| 2 | **Packaging & Polish** | Makes the library installable, cacheable, type-safe. Small wins that matter for trust. |
| 3 | **CLI** | First *user-facing* deliverable. Proves the API works end-to-end. Doubles as docs-by-example. |
| 4 | **Export / Import** | Most-requested missing feature for a DB tool. CLI and GUI both consume it. |
| 5 | **NiceGUI Frontend** | Needs a stable, documented, well-typed API underneath. Needs export. Benefits from every prior phase. |
| 6 | **Advanced** | MCP server, async wrapper, remaining DBAPI surface. |

**Docs before GUI?  Yes.**  A GUI built on an undocumented, shifting API creates a maintenance nightmare.  Writing docs first forces us to name things well, spot gaps, and stabilise.  The GUI then writes itself against a clean surface.

---

## Phase 1 — Documentation  `v0.2.1` ✅

### 1.1  MkDocs site with Material theme ✅
Create `docs/` source directory.  Pages:

| Page | Content |
|------|---------|
| **Getting Started** | Install, open Commence, hello-world script |
| **Architecture** | Layer diagram (already in README), design decisions |
| **API Reference** | Auto-generated from docstrings via `mkdocstrings[python]` |
| **Query & Filtering** | `where()`, `where_connection()`, `where_connected_field()`, checkbox (`"Checked"`), logic |
| **Connections** | `assign_connection`, `unassign_connection`, `get_connected_item_names` |
| **DDE Operations** | When to use DDE vs cursor, `get_field`, `add_item`, `fire_trigger` |
| **Canonical Mode** | What it does, when to use it, examples |
| **FAQ / Troubleshooting** | COM STA threading, data-size limits, Commence collation quirks |

Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
docs = ["mkdocs-material>=9.0", "mkdocstrings[python]>=0.25"]
```

### 1.2  CHANGELOG.md ✅
Track v0.1.0 → v0.2.0 changes in [Keep a Changelog](https://keepachangelog.com/) format.

### 1.3  Expand docstrings ✅
Every public method gets `Args` / `Returns` / `Raises` / `Example` sections.  Priority targets:
- `CommenceSession` (all shortcut methods)
- `QueryBuilder` (all chainable methods)
- `ConnectionService`
- `DdeService`

### 1.4  README examples for new features ✅
Add sections for: view cursors (`query_view`), related columns, canonical mode, DDE, connections.  The README is currently missing these.

---

## Phase 2 — Packaging & Polish  `v0.2.2` ✅

### 2.1  Publishing readiness ✅
- `LICENSE` file (MIT)
- `py.typed` marker in `src/pycommence_vibes/` (PEP 561)
- `__version__` via `importlib.metadata` in `__init__.py`
- `[project.urls]` in `pyproject.toml` (Homepage, Docs, Repository)

### 2.2  Persistent schema cache with staleness detection ✅

Schema rarely changes (adding a field to a category is a rare admin action).
But serving stale schema is worse than no cache at all — wrong field names
cause silent data corruption.  We need a **layered invalidation strategy**.

#### Storage

New module: `src/pycommence_vibes/cache.py`

```python
from platformdirs import user_cache_dir
CACHE_DIR = Path(user_cache_dir("pycommence"))
# One JSON file per database, keyed by hash of (db_name, db_path):
#   ~/.cache/pycommence/Radios_a3f7c1.json
```

Add `platformdirs` to dependencies (tiny, cross-platform, no transitive deps).

Cached file structure:
```json
{
  "db_name": "Radios",
  "db_path": "C:\\ProgramData\\Commence\\...",
  "metadata_mtime": "2026-04-10T21:26:12",
  "category_count": 57,
  "category_names": ["Account", "Hire", ...],
  "categories": {
    "Hire": {
      "field_count": 120,
      "field_names": ["Name", "Booked Date", ...],
      "fields": [ ... ],
      "connections": [ ... ]
    }
  }
}
```

#### Staleness detection — 3 layers

| Layer | Cost | What it checks | When it runs |
|-------|------|----------------|--------------|
| **L0 — DB identity** | Free | `(db_name, db_path)` matches cache file | Session init |
| **L1 — METADATA.PIM mtime** | 1 stat() call | Commence stores schema in `METADATA.PIM` (~14 MB). If its `LastWriteTime` hasn't changed since the cache was written, the schema is identical. | Session init |
| **L2 — Lightweight fingerprint** | 1 DDE call | `GetCategoryCount()` — if count differs from cache, categories were added/removed → full invalidation. | Session init (only if L1 unavailable) |
| **L3 — Per-category field count** | 1 DDE call per category | `GetFieldCount(cat)` — if count differs from cached count for that specific category, re-fetch that category only. | On first access to a category's fields |

**Flow on `CommenceSession.__init__`:**

```
1. Load cache file for this (db_name, db_path)
2. If no cache file → cold start, no cache
3. stat() METADATA.PIM at db_path:
   a. mtime == cached mtime → TRUST ENTIRE CACHE (fast path)
   b. mtime differs → mark cache as "stale-suspect"
   c. stat() fails (file locked, path wrong) → fall through to L2
4. If stale-suspect:
   a. GetCategoryCount() — if count changed → FULL INVALIDATION
   b. Count same → categories probably just had data changes, not schema.
      Keep cache but enable L3 per-category checks.
```

**On `get_fields(category)` / `get_field_names(category)`:**

```
1. If cache is fully trusted (L1 passed) → return cached, zero DDE calls
2. If stale-suspect → GetFieldCount(category):
   a. Matches cached count → return cached fields
   b. Differs → re-fetch that category, update cache
3. If no cache → fetch from DDE, populate cache, write to disk
```

#### API surface

```python
class SchemaService:
    def get_fields(self, category: str, *, use_cache: bool = True) -> list[FieldInfo]: ...
    def clear_cache(self) -> None:
        """Drop in-memory and on-disk cache. Next call fetches fresh from Commence."""
    def warm_cache(self, categories: list[str] | None = None) -> None:
        """Pre-fetch and cache schema for given categories (or all). Useful at startup."""
```

#### Why METADATA.PIM mtime works

Commence stores all category/field/connection definitions in `METADATA.PIM`
(observed: 14 MB, path `{db_path}/METADATA.PIM`).  It is rewritten when
schema changes (add/remove field, add/remove category, change connection).
It is **not** rewritten for data-only changes (add/edit/delete rows).  This
makes it an ideal schema-change sentinel — one `os.stat()` call replaces
dozens of DDE round-trips.

#### Edge cases

| Scenario | Handling |
|----------|----------|
| Commence not running at cache-check time | Impossible — `CommenceSession.__init__` already requires a live COM connection |
| METADATA.PIM path changes between versions | Key cache on `(db_name, db_path)` — different path = different cache file |
| User switches to a different database | Different `db_name`/`db_path` → different cache file, no conflict |
| Schema changed while session is open | Won't detect mid-session. `clear_cache()` is the escape hatch. Document this. |
| Shared/replicated DB with remote schema changes | METADATA.PIM mtime updates on sync. If sync hasn't happened, stale risk exists — document as known limitation. |
| Cache file corrupted / unparseable | Catch `json.JSONDecodeError`, delete cache file, proceed uncached |

### 2.3  `RowResult` ergonomics ✅
- `to_dict() -> dict[str, str]`
- `__contains__` for `"field" in row`
- `__iter__` for key-value pairs
- `to_typed_dict(fields: list[FieldInfo])` — coerce values to `int`/`float`/`bool`/`date` based on field type metadata

### 2.4  Thread `logic` param through `edit_where` / `delete_where` ✅
`session.edit_where()` and `session.delete_where()` accept `filters` but not `logic`.  Add it.

---

## Phase 3 — CLI  `v0.3.0` ✅

Replace the stub `main()` with a real CLI using `click` + `rich`.

### Commands
| Command | Description |
|---------|-------------|
| `pycommence schema` | List all categories |
| `pycommence schema <category>` | Show fields + connections for a category |
| `pycommence read <category>` | Read rows (`--columns`, `--filter`, `--limit`, `--format json\|csv\|table`) |
| `pycommence count <category>` | Row count (with optional `--filter`) |
| `pycommence export <category> <outfile>` | Export to CSV/JSON/Excel |
| `pycommence info` | DB name, path, version, shared status |
| `pycommence gui` | Launch NiceGUI frontend (Phase 5) |

Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
cli = ["click>=8.0", "rich>=13.0"]
```

---

## Phase 4 — Export & Import  `v0.3.1`

### 4.1  `ExportService`
New `src/pycommence_vibes/services/export.py`:

```python
class ExportService:
    def to_csv(self, rows: list[RowResult], path: str) -> None: ...
    def to_json(self, rows: list[RowResult], path: str) -> None: ...
    def to_excel(self, rows: list[RowResult], path: str) -> None: ...  # optional openpyxl
```

Wire into session:
```python
session.export("Hire", "hires.csv", format="csv", max_rows=5000)
```

### 4.2  `BackupService`
Export all categories (or selected) to a directory of JSON files with schema metadata sidecar:
```
backup/
  _schema.json          # categories, fields, connections
  Contact.json
  Hire.json
  ...
```

### 4.3  Import (stretch)
`from_csv()` / `from_json()` that map rows back to `session.add_many()`.

---

## Phase 5 — NiceGUI Frontend  `v0.4.0`

### 5.1  Architecture
- New package: `src/pycommence_vibes/gui/`
- Uses `CommenceSession` directly — no separate backend
- Runs via `ui.run(native=True)` for desktop-app feel
- Launched by `pycommence gui` CLI command

### 5.2  Pages

| Page | Features |
|------|----------|
| **Dashboard** | DB name/path/version, category list with row counts, quick-nav |
| **Category Browser** | `ui.table` with server-side pagination, column picker, sort, filter builder |
| **Record Detail** | View/edit single row, show connections, open in Commence UI |
| **Schema Explorer** | Field definitions table, connections tree diagram |
| **Export Dialog** | Pick category, columns, filters → export to CSV/JSON/Excel |
| **DDE Console** | Raw DDE request/execute with response display (power-user tool) |

### 5.3  Design principles
- **Read-only by default.**  Edit/delete require explicit unlock toggle to prevent accidental data loss.
- **Server-side pagination.**  Never load 13k rows into the browser.  Delegate to `ReaderService` batching.
- **Responsive tables.**  Use `ui.table` with virtual scroll, not `ui.aggrid` (simpler, fewer deps).
- **Minimal state.**  Each page re-queries on navigation.  No client-side cache to go stale.

---

## Phase 6 — Advanced Features  `v0.5.0+`

### 6.1  MCP server
Expose `read`, `query`, `schema`, `add`, `edit`, `delete`, `connections` as MCP tools, allowing LLM agents to interact with Commence databases.  New module `src/pycommence_vibes/mcp_server.py`.  (There's already an external MCP server — this would be built-in.)

### 6.2  Async wrapper
COM is STA-bound.  Create `AsyncCommenceSession` that dispatches all calls to a dedicated thread via `asyncio.to_thread()`:
```python
async with AsyncCommenceSession() as db:
    rows = await db.read("Hire", max_rows=100)
```
Enables use in async frameworks (FastAPI, NiceGUI's async handlers).

### 6.3  Remaining DBAPI surface
Deferred items from PLAN-v0.2.0:
- Item marking (`GetMarkItem`, `ViewMarkItem`, `MarkActiveItem`)
- `GetViewToFile` HTML export
- Shared/local filter qualifiers
- Clarified item name helpers
- Form script management (`CheckInFormScript`, `CheckOutFormScript`)
- `MergeTemplate` commands
- `GetPreference`, `GetCallerID`

### 6.4  Bulk operations
- `session.upsert(category, pk_field, rows)` — add-or-update based on PK match
- `session.copy_category(from_cat, to_cat, field_map)` — data migration helper
- Parallel batch reads via thread pool (multiple cursors)

### 6.5  Notifications / watch
- Poll-based change detection: `session.watch("Hire", interval=5)` yields new/changed rows
- Could use DDE `FireTrigger` integration for event-driven updates

---

## Version Summary

| Version | Codename | Key deliverable |
|---------|----------|-----------------|
| **0.2.1** | *Docs* | MkDocs site, CHANGELOG, expanded docstrings |
| **0.2.2** | *Polish* | `py.typed`, persistent schema cache (METADATA.PIM staleness), `RowResult` improvements, publishing metadata |
| **0.3.0** | *CLI* | `click` + `rich` CLI with read/schema/count/info commands |
| **0.3.1** | *Export* | CSV/JSON/Excel export, backup service |
| **0.4.0** | *GUI* | NiceGUI desktop app — browse, search, export, view schema |
| **0.5.0** | *Advanced* | MCP server, async wrapper, remaining DBAPI, bulk ops |

---

## Dependency Map

```
Phase 1 (Docs)
  └── no deps — start immediately

Phase 2 (Polish)
  ├── benefits from Phase 1 (docstrings inform API choices)
  └── adds platformdirs dep for persistent cache (2.2)

Phase 3 (CLI)
  ├── depends on Phase 2.3 (RowResult.to_dict for JSON output)
  ├── depends on Phase 2.2 (schema cache makes `schema` command instant)
  └── depends on Phase 1 (docs provide --help text)

Phase 4 (Export)
  └── depends on Phase 3 (CLI export command wraps ExportService)

Phase 5 (GUI)
  ├── depends on Phase 4 (export dialog)
  ├── depends on Phase 2.2 (schema cache critical for responsive UI)
  └── depends on Phase 1 (stable documented API)

Phase 6 (Advanced)
  └── independent tracks, can start anytime after Phase 2
```

