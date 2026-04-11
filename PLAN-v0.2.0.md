# pycommence v0.2.0 — Release Plan

> Fix all identified flaws, expose missing Commence DBAPI/DDE surface area, and harden the library.
>
> **Backward compatibility is preserved**: existing public signatures are unchanged; new parameters use defaults matching v0.1.0 behavior.

---

## Phase 1 — Bug Fixes & Quick Wins

*No new files. Pure fixes to existing code. Zero risk of breaking existing callers.*

### 1.1 Fix `QueryBuilder.count()` to respect filters
**File:** `src/pycommence/query.py`, `src/pycommence/services/reader.py`

`count()` currently calls `self._reader.count(self._category)` which opens a bare cursor — **ignoring all accumulated filters and logic**. 

**Fix:**
- Add a `count(category, filters, logic)` overload to `ReaderService` that opens a cursor, applies filters/logic, then returns `cur.row_count`.
- Update `QueryBuilder.count()` to pass `self._filters` and `self._logic`.

### 1.2 Forward `logic` param in `session.read()`
**File:** `src/pycommence/session.py`

`CommenceSession.read()` accepts `filters` and `sort` but does **not** accept or forward a `logic` parameter, even though `ReaderService.read_rows()` supports it.

**Fix:** Add `logic: str | None = None` parameter and pass it through.

### 1.3 Guard `close()` against double-close
**File:** `src/pycommence/_com/connection.py`

Calling `close()` twice crashes (`AttributeError` + COM `CoUninitialize` imbalance).

**Fix:** Add `self._closed = False` flag; make `close()` no-op when already closed.

### 1.4 Wrap `CommitGetCursor` in `RowsetWrapper`
**Files:** `src/pycommence/_com/rowset.py`, `src/pycommence/services/writer.py`

`WriterService.add_row()` calls `rs.raw.CommitGetCursor(0)` directly, bypassing the wrapper.

**Fix:**
- Add `commit_get_cursor() -> CursorWrapper | None` to `RowsetWrapper`.
- Update `WriterService.add_row()` to use the wrapper method.

### 1.5 Clean up dead code in models
**File:** `src/pycommence/models.py`

`FilterClause.to_filter_string()` and `SortSpec.to_sort_string()` are never called by anything.

**Fix:** Remove the `to_filter_string()` and `to_sort_string()` methods. Keep the dataclasses themselves as they're valid descriptors/documentation. Alternatively, wire `QueryBuilder` to use them — but inline string building is simpler and the models add an unnecessary indirection layer.

### 1.6 Fix `set_columns_all()` misleading no-op
**File:** `src/pycommence/_com/cursor.py`, `src/pycommence/services/writer.py`

`set_columns_all()` is documented as setting all columns but is actually a no-op. Works by accident for `CMC_CURSOR_CATEGORY` (which defaults to all fields).

**Fix:**
- Add clear docstring: *"No-op for category-mode cursors which already include all fields. Do NOT call on view cursors — use set_columns() explicitly instead."*
- In writer methods, remove redundant calls to `set_columns_all()` where only `get_column_index()` is needed (add/edit/delete rowsets inherit the full column set from the category cursor regardless).

---

## Phase 2 — COM Layer: Missing Cursor & Rowset Methods

*Complete the low-level wrapper coverage. Every documented DBAPI method gets a Python wrapper.*

### 2.1 Add view-linking cursor methods
**File:** `src/pycommence/_com/cursor.py`

Add three methods matching the DBAPI docs:

```python
def set_active_item(self, category_name: str, row_id: str) -> None:
    """Set active item for view cursors using a view linking filter."""

def set_active_date(self, date_str: str) -> None:
    """Set active date for view cursors using a view linking filter.
    Supports AI date values like 'today'."""

def set_active_date_range(self, start_date: str, end_date: str) -> None:
    """Set active date range for view cursors using a view linking filter."""
```

### 2.2 Add `SeekRowApprox`
**File:** `src/pycommence/_com/cursor.py`

```python
def seek_row_approx(self, numerator: int, denominator: int) -> int:
    """Seek to an approximate position in the cursor."""
```

### 2.3 Add `GetFieldToFile`
**File:** `src/pycommence/_com/rowset.py`

```python
def get_field_to_file(self, row: int, col: int, filename: str, canonical: bool = False) -> int:
    """Save field value to file. Returns file size in bytes, or 0 if no data."""
```

### 2.4 Expose canonical data mode to users
**Files:** `reader.py`, `query.py`, `session.py`

Thread a `canonical: bool = False` parameter from the public API all the way down:
- `CommenceSession.read(..., canonical=False)`
- `CommenceSession.read_by_id(..., canonical=False)`
- `QueryBuilder.canonical(val=True) -> QueryBuilder` (chain method)
- `ReaderService.read_rows(..., canonical=False)` → passes to `rs.get_row_value(r, c, canonical=canonical)`

This gives users consistent `yyyymmdd` dates, `hh:mm` times, `123456.78` numbers, and `TRUE`/`FALSE` checkboxes regardless of locale.

---

## Phase 3 — View Cursors & Related Columns

*Unlock the two most-requested read-path features: view-based queries and connected/indirect field reads.*

### 3.1 Support `CMC_CURSOR_VIEW` mode
**Files:** `session.py`, `reader.py`, `query.py`

**Changes:**
- `CommenceDB.get_cursor()` already accepts `mode` — no change needed there.
- Add `session.query_view(view_name: str) -> QueryBuilder` that creates a `QueryBuilder` in view mode.
- Add `mode: int = CMC_CURSOR_CATEGORY` to `ReaderService.read_rows()`.
- `QueryBuilder.__init__` gains `_mode` attribute, set by factory methods.

**View cursors** inherit the view's filter, sort, and column set. Users can layer additional filters via the builder.

### 3.2 Expose `SetRelatedColumn` in the read path
**Files:** `models.py`, `query.py`, `reader.py`

**New model:**
```python
@dataclass(frozen=True, slots=True)
class RelatedColumn:
    """A connected/indirect field to include in query results."""
    connection_name: str
    connected_category: str
    field_name: str
```

**QueryBuilder addition:**
```python
def related_column(self, connection: str, category: str, field: str) -> QueryBuilder:
    """Include a connected field in the result set."""
```

**ReaderService change:**
When `related_columns` are specified, after setting regular columns, call `cur.set_related_column()` for each related column, assigning them sequential column indices after the regular columns.

---

## Phase 4 — Connection CRUD & DDE Execute Commands

*The biggest functional gap: Commence connections (relationships) and DDE execute operations.*

### 4.1 Create `ConnectionService`
**New file:** `src/pycommence/services/connections.py`

Uses `ConversationWrapper.execute()` with DDE commands:

```python
class ConnectionService:
    def assign(self, from_cat, from_item, conn_name, to_cat, to_item) -> None:
        """[AssignConnection(FromCat, FromItem, ConnName, ToCat, ToItem)]"""

    def unassign(self, from_cat, from_item, conn_name, to_cat, to_item) -> None:
        """[UnassignConnection(FromCat, FromItem, ConnName, ToCat, ToItem)]"""

    def get_connected_item_names(self, from_cat, from_item, conn_name, to_cat) -> list[str]:
        """[GetConnectedItemNames(...)] via DDE Request"""

    def get_connected_item_count(self, from_cat, from_item, conn_name, to_cat) -> int:
        """[GetConnectedItemCount(...)] via DDE Request"""

    def get_connected_item_field(self, from_cat, from_item, conn_name, to_cat, field) -> list[str]:
        """[GetConnectedItemField(...)] via DDE Request"""
```

### 4.2 Create `DdeService` for remaining Execute commands
**New file:** `src/pycommence/services/dde.py`

Wraps the most useful DDE Execute and Request commands not covered by the cursor/rowset API:

```python
class DdeService:
    # Item operations via DDE (alternative to cursor path)
    def add_item(self, category, item_name, clarify_value=None) -> None
    def edit_item(self, category, item_name, field, value) -> None
    def delete_item(self, category, item_name) -> None
    def append_text(self, category, item_name, field, text) -> None

    # UI operations
    def show_item(self, category, item_name, form_name=None) -> None
    def show_view(self, view_name, force_new=False) -> None

    # Triggers
    def fire_trigger(self, trigger_name, *args) -> None

    # Field operations
    def get_field(self, category, item_name, field) -> str
    def get_fields(self, category, item_name, *fields) -> list[str]
    def get_field_to_file(self, category, item_name, field, filename) -> None

    # Additional schema (not in SchemaService yet)
    def get_item_names(self, category) -> list[str]
    def get_item_count(self, category) -> int
    def get_database_definition(self) -> dict
```

### 4.3 Wire into `CommenceSession`
**File:** `src/pycommence/session.py`

```python
@property
def connections(self) -> ConnectionService: ...

@property
def dde(self) -> DdeService: ...

# Convenience shortcuts
def assign_connection(self, from_cat, from_item, conn_name, to_cat, to_item) -> None: ...
def unassign_connection(self, from_cat, from_item, conn_name, to_cat, to_item) -> None: ...
```

---

## Phase 5 — Robustness, DX & Polish

### 5.1 Fix fragile `GetCategoryDefinition` parsing
**File:** `src/pycommence/services/schema.py`

Replace the `zfill(10)` + negative-index approach with explicit positional parsing. The documented format is `000000{S}{M}{D}{C}` (10 chars). Parse the last 4 characters by name:

```python
s, m, d, c = flag_str[-4], flag_str[-3], flag_str[-2], flag_str[-1]
```

Handle the edge case where `{C}` may be separated by `\n` from `{D}` (strip whitespace from the flags string before parsing). Wrap in try/except → `SchemaError`.

### 5.2 COM retry decorator
**New file:** `src/pycommence/_com/retry.py`

```python
import functools, time, pywintypes

def com_retry(max_retries=3, delay=0.5):
    """Decorator that retries COM calls on transient failures."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except pywintypes.com_error as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay * (attempt + 1))
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

Apply to:
- `ConversationWrapper.request()` and `.execute()`
- `RowsetWrapper.commit()`
- `CommenceDB.__init__()` (the Dispatch call)

### 5.3 Thread-safety documentation and guard
**File:** `src/pycommence/_com/connection.py`

Add module-level docstring warning about COM STA threading. Add optional `_check_thread()` helper that logs a warning if COM objects are accessed from a non-main thread:

```python
import threading
_INIT_THREAD = None

def _check_thread():
    if _INIT_THREAD and threading.current_thread() != _INIT_THREAD:
        log.warning("CommenceDB accessed from thread %s but was initialized on %s. "
                     "COM STA objects are not thread-safe.", ...)
```

### 5.4 Update exports and version
**Files:** `__init__.py`, `pyproject.toml`

- Export new public symbols: `RelatedColumn`, `ConnectionService`, `DdeService`
- Bump `version = "0.2.0"`

### 5.5 New and updated tests
**New files:**
- `tests/test_connections.py` — assign/unassign connections against Tutorial DB (Contact → Account)
- `tests/test_dde.py` — DDE execute commands (add_item, edit_item, show_view, fire_trigger)
- `tests/test_view_cursor.py` — open a view cursor, read data, verify it inherits view filter/sort

**Updated files:**
- `tests/test_query.py` — test `count()` with filters, `related_column()`, `canonical()`, `query_view()`
- `tests/test_read.py` — test `canonical=True` returns consistent format
- `tests/test_crud.py` — test `CommitGetCursor` wrapper path

---

## Implementation Order & Dependencies

```
Phase 1 (no dependencies — pure fixes)
  ├─ 1.1  Fix count()
  ├─ 1.2  Forward logic param
  ├─ 1.3  Guard double-close
  ├─ 1.4  Wrap CommitGetCursor
  ├─ 1.5  Clean dead code
  └─ 1.6  Fix set_columns_all docs

Phase 2 (depends on Phase 1.4 for rowset changes)
  ├─ 2.1  View-linking methods
  ├─ 2.2  SeekRowApprox
  ├─ 2.3  GetFieldToFile
  └─ 2.4  Canonical mode

Phase 3 (depends on Phase 2.4 for canonical threading)
  ├─ 3.1  View cursor support
  └─ 3.2  Related columns

Phase 4 (independent of Phases 2-3, depends on Phase 1.3)
  ├─ 4.1  ConnectionService
  ├─ 4.2  DdeService
  └─ 4.3  Session wiring

Phase 5 (depends on all above)
  ├─ 5.1  Fix flag parsing
  ├─ 5.2  COM retry
  ├─ 5.3  Thread safety
  ├─ 5.4  Exports + version bump
  └─ 5.5  Tests
```

Phases 1–3 form the **cursor/read path** track.  
Phase 4 is the **DDE/connection** track (can be done in parallel with Phases 2–3).  
Phase 5 is **polish** that should come last.

---

## Files Changed/Created Summary

| File | Action | Phase |
|---|---|---|
| `src/pycommence/query.py` | Modify | 1, 2, 3 |
| `src/pycommence/session.py` | Modify | 1, 2, 3, 4 |
| `src/pycommence/services/reader.py` | Modify | 1, 2, 3 |
| `src/pycommence/_com/connection.py` | Modify | 1, 5 |
| `src/pycommence/_com/rowset.py` | Modify | 1, 2 |
| `src/pycommence/_com/cursor.py` | Modify | 1, 2 |
| `src/pycommence/models.py` | Modify | 1, 3 |
| `src/pycommence/services/writer.py` | Modify | 1 |
| `src/pycommence/services/schema.py` | Modify | 5 |
| `src/pycommence/__init__.py` | Modify | 5 |
| `pyproject.toml` | Modify | 5 |
| `src/pycommence/services/connections.py` | **Create** | 4 |
| `src/pycommence/services/dde.py` | **Create** | 4 |
| `src/pycommence/_com/retry.py` | **Create** | 5 |
| `tests/test_connections.py` | **Create** | 5 |
| `tests/test_dde.py` | **Create** | 5 |
| `tests/test_view_cursor.py` | **Create** | 5 |
| `tests/test_query.py` | Modify | 5 |
| `tests/test_read.py` | Modify | 5 |
| `tests/test_crud.py` | Modify | 5 |

---

## Deferred to v0.3.0

- Niche DDE commands: `MergeTemplateCreate`, `MergeTemplateSave`, `LogPhoneCall`, `CheckInFormScript`, `CheckOutFormScript`, `PromoteItemToShared`, `GetCallerID`, `GetPreference`
- Shared/Local filter qualifier in `QueryBuilder.where()`
- Item marking support (`GetMarkItem`, `ViewMarkItem`, `MarkActiveItem`)
- `GetViewToFile` HTML export
- Clarified item name helpers (build/parse clarified names with separator)
- Async/background-thread COM support via `CoInitializeEx(COINIT_MULTITHREADED)` 

