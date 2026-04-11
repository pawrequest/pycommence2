# Canonical Mode

Commence stores data in locale-dependent text format. Dates, times, numbers, and checkboxes are formatted according to the user's Windows locale settings. This causes problems when:

- Parsing dates/numbers in code
- Comparing values across machines with different locales
- Exporting data for interchange

**Canonical mode** returns data in a standardised, locale-independent format.

## Enabling Canonical Mode

### Via QueryBuilder

```python
results = (
    db.query("Hire")
    .columns("Name", "Booked Date", "Price", "Confirmed")
    .canonical()
    .execute()
)
```

### Via `session.read()`

```python
rows = db.read("Hire", canonical=True)
```

## Format Differences

| Data Type | Normal (locale-dependent) | Canonical |
|-----------|--------------------------|-----------|
| **Date** | `04/11/2026` or `11.04.2026` | `20260411` |
| **Time** | `2:30 PM` or `14:30` | `14:30` |
| **Number** | `1,234.56` or `1.234,56` | `1234.56` |
| **Checkbox** | `Yes`/`No` or `1`/`0` | `TRUE` / `FALSE` |

## When to Use Canonical Mode

✅ **Use canonical mode when:**

- Parsing dates with `datetime.strptime` or similar
- Doing numeric comparisons or calculations
- Exporting data for interchange (CSV, JSON, API)
- Writing code that must work regardless of the user's locale

❌ **Don't use canonical mode when:**

- Displaying data to end users (they expect their locale format)
- The field values are pure text (canonical has no effect on text fields)

## Example: Parsing Canonical Dates

```python
from datetime import datetime

results = (
    db.query("Hire")
    .columns("Name", "Booked Date")
    .canonical()
    .execute()
)

for row in results:
    date_str = row["Booked Date"]  # "20260411"
    if date_str:
        dt = datetime.strptime(date_str, "%Y%m%d")
        print(f"{row['Name']}: {dt.date()}")
```

## How It Works

Under the hood, canonical mode sets the `CMC_FLAG_CANONICAL` flag on the rowset's `GetRowValue` call. This is handled by the `RowsetWrapper` in the `_com` layer — you don't need to manage flags yourself.

