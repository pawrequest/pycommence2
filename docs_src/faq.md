# FAQ / Troubleshooting

## Common Issues

### "Could not connect to Commence. Is it running?"

**Cause:** `CommenceSession()` raises `CommenceNotFoundError` when the COM dispatch fails.

**Fix:**

1. Make sure Commence is **running** with a database open.
2. Make sure you are on **Windows** (COM automation is Windows-only).
3. If Commence is running but you still get this error, try restarting Commence.

### COM STA threading errors

**Cause:** Commence.DB is an STA (Single-Threaded Apartment) COM object. All calls must be made from the thread that created the session.

**Symptoms:**

- `pywintypes.com_error` with cryptic HRESULT codes
- Silently corrupted data
- Warning log: `"CommenceDB accessed from thread X but was initialised on Y"`

**Fix:**

- Use `CommenceSession` from a single thread.
- If you need multi-threaded access, create **one session per thread**.
- For async frameworks, consider wrapping in `asyncio.to_thread()` with a dedicated worker thread.

### Maximum 4 filter clauses

**Cause:** Commence limits `ViewFilter` to 4 clauses.

**Symptom:** `ValueError: Commence supports a maximum of 4 filter clauses`

**Fix:** Reduce the number of `.where()` / `.where_connection()` / `.where_connected_field()` calls to 4 or fewer. If you need more complex filtering, consider:

- Using a saved Commence view with the filters pre-configured
- Post-filtering results in Python

### Large data sets are slow

**Cause:** Reading tens of thousands of rows via COM is inherently slower than native SQL databases.

**Tips:**

- Use `max_rows` / `.limit()` to cap result size
- Use filters to reduce the result set before fetching
- Use `.columns()` to select only the fields you need
- For very large exports, consider batching with pagination

### Date/number formats vary between machines

**Cause:** Commence returns data formatted according to the Windows locale.

**Fix:** Use [canonical mode](canonical.md):

```python
rows = db.read("Hire", canonical=True)
# Dates: "yyyymmdd", Numbers: "123456.78", Checkboxes: "TRUE"/"FALSE"
```

### `RowsetError: No row found for ID '...'`

**Cause:** The row ID is invalid or the row was deleted between reading the ID and using it.

**Fix:** Row IDs are session-scoped. They may change between Commence restarts or when rows are deleted and re-added. Always re-query if you get this error.

## Architecture Questions

### Why are there both `session.add()` and `dde.add_item()`?

They use different underlying APIs:

- `session.add()` uses the **cursor/rowset API** — creates an AddRowSet, sets field values, commits. Returns the new row ID. Best for programmatic batch operations.
- `dde.add_item()` uses the **DDE API** — sends an `[AddItem(...)]` command. Simpler but doesn't return a row ID. Best for one-off item creation by name.

### Can I use pycommence-vibes with multiple databases?

Each `CommenceSession` connects to whichever database Commence currently has open. To work with a different database, switch databases in Commence first, then create a new session.

### Is pycommence-vibes thread-safe?

No. COM STA objects are single-threaded by design. Create one `CommenceSession` per thread if you need concurrent access.

