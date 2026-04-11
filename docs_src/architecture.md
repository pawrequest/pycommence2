# Architecture

pycommence-vibes is organised into three layers. Each layer has a clear responsibility and only talks to the layer below it.

## Layer Diagram

```
┌─────────────────────────────────────────────────┐
│               Your App / CLI / GUI              │
├─────────────────────────────────────────────────┤
│              CommenceSession (public API)        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  schema   │  │  reader   │  │   writer     │  │
│  │  service  │  │  service  │  │   service    │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│  ┌────┴─────┐  ┌────┴──────┐                    │
│  │connection │  │   dde     │                    │
│  │ service   │  │  service  │                    │
│  └────┬─────┘  └────┬──────┘                    │
├───────┼──────────────┼───────────────┼──────────┤
│       │     _com (internal COM layer)│          │
│  ┌────┴────┐  ┌──────┴───┐  ┌───────┴──────┐   │
│  │Converse │  │  Cursor   │  │   Rowset     │   │
│  │ation    │  │  Wrapper  │  │   Wrapper    │   │
│  └────┬────┘  └────┬─────┘  └──────┬───────┘   │
├───────┼────────────┼───────────────┼────────────┤
│       └────── win32com.client (COM) ────────────│
│                  Commence.DB                    │
└─────────────────────────────────────────────────┘
```

## Layers

### 1. `_com/` — COM Wrappers (internal)

Thin wrappers around the raw COM dispatch objects. This layer:

- Manages COM lifecycle (`CoInitialize` / `CoUninitialize`)
- Translates COM errors into Python exceptions
- Provides typed Python methods for every `ICommenceCursor`, `ICommenceQueryRowSet`, and `ICommenceConversation` method
- Handles NULL checks, retries on transient COM failures, and thread-safety warnings

**You should not import from `_com/` directly.** It is an internal implementation detail.

### 2. `services/` — Business Logic

Service classes that compose COM wrapper calls into useful operations:

| Service | Responsibility |
|---------|----------------|
| `SchemaService` | Category/field/connection introspection via DDE |
| `ReaderService` | Query and read rows via cursor + QueryRowSet |
| `WriterService` | Add, edit, delete rows via cursor + Add/Edit/DeleteRowSet |
| `ConnectionService` | Assign/unassign connections via DDE Execute |
| `DdeService` | Remaining DDE commands: item CRUD, UI, triggers |

### 3. `session.py` — Public API

`CommenceSession` is the **single public entry point**. It:

- Creates the COM connection on init
- Instantiates all services
- Exposes shortcut methods (`read`, `add`, `edit`, `delete`)
- Provides a `QueryBuilder` factory via `.query()` and `.query_view()`
- Acts as a context manager for clean resource cleanup

## Design Decisions

### Why a session object?

COM connections are stateful resources that need cleanup. A session object with context manager support (`with CommenceSession() as db:`) ensures resources are always released.

### Why DDE *and* cursor APIs?

Commence exposes two APIs:

- **Cursor / RowSet API** — for batch reads and writes. Efficient for bulk operations.
- **DDE Conversation API** — for schema introspection, single-item CRUD, connections, UI commands, and triggers.

Some operations are only available via DDE (connections, triggers, `ShowItem`). Some are only efficient via cursors (reading 10,000 rows). pycommence-vibes uses both, choosing the right one for each operation.

### Why services instead of putting everything in the session?

Separation of concerns. The session is a thin facade. Each service owns its own logic and can be tested independently.

