# Query & Filtering

pycommence provides two ways to read data: the `session.read()` shortcut and the fluent `QueryBuilder`.

## Simple Reads

```python
with CommenceSession() as db:
    # All columns, up to 500 rows (default)
    rows = db.read("Contact")

    # Specific columns, limited rows
    rows = db.read("Contact", columns=["Name", "Email"], max_rows=10)
```

## QueryBuilder

The `QueryBuilder` provides a chainable interface for constructing complex queries:

```python
with CommenceSession() as db:
    results = (
        db.query("Contact")
        .columns("Name", "Email", "Phone")
        .where("Name", "Contains", "Smith")
        .sort("Name")
        .limit(20)
        .execute()
    )
```

Every method returns `self`, so you can chain calls in any order before calling `.execute()`.

## Field Filters (`.where()`)

Filter on any field with a qualifier:

```python
# Text contains
db.query("Contact").where("Name", "Contains", "Smith")

# Exact match
db.query("Contact").where("Email", "Equal To", "jane@example.com")

# Date comparisons
db.query("Hire").where("Booked Date", "After", "2026-01-01")
db.query("Hire").where("Booked Date", "Before", "2026-12-31")

# Checkbox fields — use "Checked" or "Not Checked" as the qualifier
db.query("Contact").where("Active", "Checked", "")
db.query("Contact").where("Active", "Not Checked", "")

# Case-sensitive comparison
db.query("Contact").where("Name", "Equal To", "SMITH", case_sensitive=True)
```

### Supported Qualifiers

| Qualifier | Applicable Types |
|-----------|------------------|
| `"Contains"` | Text, Name, Email, URL |
| `"Does Not Contain"` | Text, Name, Email, URL |
| `"Equal To"` | All types |
| `"Not Equal To"` | All types |
| `"After"` | Date, Time |
| `"Before"` | Date, Time |
| `"Between"` | Date, Number |
| `"Greater Than"` | Number |
| `"Less Than"` | Number |
| `"Blank"` | All types (value ignored) |
| `"Not Blank"` | All types (value ignored) |
| `"Checked"` | Checkbox (value must be `""`) |
| `"Not Checked"` | Checkbox (value must be `""`) |

## Connection Filters

### Connection To Item (`.where_connection()`)

Filter rows that are (or are not) connected to a specific item:

```python
# People employed by Acme Corp
db.query("Person").where_connection("Is Employed by", "Company", "Acme Corp")

# People NOT employed by Acme Corp
db.query("Person").where_connection("Is Employed by", "Company", "Acme Corp", not_flag=True)
```

### Connection To Category Field (`.where_connected_field()`)

Filter rows based on a field value in a connected item:

```python
# People whose employer is in NJ
db.query("Person").where_connected_field(
    "Is Employed by", "Company", "State", "Contains", "NJ"
)
```

## Combining Filters

Commence supports up to **4 filter clauses**. By default they are combined with AND. Use `.conjunction()` to change the logic:

```python
results = (
    db.query("Contact")
    .where("City", "Equal To", "New York")
    .where("Status", "Equal To", "Active")
    .where("Name", "Contains", "A")
    .conjunction("And, Or, And")
    .execute()
)
```

The logic string defines the operators between consecutive filter clauses. For 3 filters, you need 2 operators (though Commence accepts 3 for consistency).

## Raw Filters

For advanced or non-standard filter syntax, use the escape hatch:

```python
results = (
    db.query("Person")
    .raw_filter('[ViewFilter(1, F, , "Name", "Contains", "Smith", False)]')
    .execute()
)
```

## Sorting

```python
# Single sort
db.query("Contact").sort("Name")

# Descending
db.query("Contact").sort("Name", ascending=False)

# Multiple sort fields (up to 4)
db.query("Contact").sort("LastName").sort("FirstName")
```

## Related Columns

Pull fields from connected items into your query results:

```python
results = (
    db.query("Person")
    .columns("Name", "Email")
    .related_column("Is Employed by", "Company", "Company Name")
    .related_column("Is Employed by", "Company", "Phone")
    .execute()
)

for row in results:
    print(row["Name"], row["Company Name"])
```

Related columns appear in the result set alongside regular columns. They are added via `ICommenceCursor.SetRelatedColumn` under the hood.

## View Cursors

Query against a saved Commence view, inheriting its built-in filter, sort, and column set:

```python
results = (
    db.query_view("Active Contacts")
    .limit(100)
    .execute()
)
```

You can layer additional filters on top of the view's built-in filter:

```python
results = (
    db.query_view("Active Contacts")
    .where("City", "Equal To", "Boston")
    .limit(50)
    .execute()
)
```

## Counting Rows

Get a count without fetching data:

```python
# Count with filters
count = (
    db.query("Contact")
    .where("Status", "Equal To", "Active")
    .count()
)
print(f"{count} active contacts")
```

## Canonical Mode

Enable locale-independent data formatting:

```python
results = (
    db.query("Hire")
    .columns("Name", "Booked Date", "Price", "Confirmed")
    .canonical()
    .execute()
)

# Dates → "yyyymmdd"
# Times → "hh:mm" (24-hour)
# Numbers → "123456.78" (no locale grouping)
# Checkboxes → "TRUE" / "FALSE"
```

See [Canonical Mode](canonical.md) for more details.

## Working with Results

Each row is a `RowResult` with dict-like access:

```python
for row in results:
    # Dict-style access
    name = row["Name"]

    # Safe access with default
    email = row.get("Email", "N/A")

    # Membership test
    if "Email" in row:
        print(row["Email"])

    # Iterate field names
    for field_name in row:
        print(f"{field_name} = {row[field_name]}")

    # Number of columns
    print(f"{len(row)} columns")

    # Row ID (unique identifier for updates/deletes)
    print(row.row_id)

    # Convert to plain dict (e.g. for JSON serialisation)
    import json
    print(json.dumps(row.to_dict()))
```

### Typed Conversion

When using [canonical mode](canonical.md), you can convert string values to
native Python types based on field metadata:

```python
with CommenceSession() as db:
    fields = db.schema.get_fields("Hire")
    rows = (
        db.query("Hire")
        .canonical()
        .limit(10)
        .execute()
    )

    for row in rows:
        typed = row.to_typed_dict(fields)
        # DATE fields → datetime.date
        # TIME fields → datetime.time
        # NUMBER/CALCULATION fields → int or float
        # CHECK_BOX fields → bool
        # Everything else → str
        print(typed["Booked Date"])  # date(2026, 4, 11)
        print(typed["Price"])        # 1234.56
        print(typed["Confirmed"])    # True
```

