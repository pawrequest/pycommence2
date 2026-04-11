# Connections

Commence databases use **connections** (relationships) to link items across categories. For example, a "Person" might be connected to a "Company" via an "Is Employed by" connection.

## Listing Connections

Discover what connections exist for a category:

```python
with CommenceSession() as db:
    for conn in db.schema.get_connection_names("Person"):
        print(f"  {conn.name} → {conn.to_category}")
    # Output:
    #   Is Employed by → Company
    #   Relates to → Person
    #   Owns → Vehicle
```

## Querying Connected Items

### Get connected item names

```python
with CommenceSession() as db:
    names = db.connections.get_connected_item_names(
        "Person", "John Smith",
        "Is Employed by", "Company",
    )
    print(names)  # ["Acme Corp", "Beta Inc"]
```

### Get connected item count

```python
with CommenceSession() as db:
    count = db.connections.get_connected_item_count(
        "Person", "John Smith",
        "Is Employed by", "Company",
    )
    print(f"Employed by {count} companies")
```

### Get a field from connected items

```python
with CommenceSession() as db:
    phones = db.connections.get_connected_item_field(
        "Person", "John Smith",
        "Is Employed by", "Company",
        "Phone",
    )
    print(phones)  # ["555-0100", "555-0200"]
```

## Assigning Connections

Create a connection between two items:

```python
with CommenceSession() as db:
    db.assign_connection(
        "Person", "John Smith",
        "Is Employed by",
        "Company", "Acme Corp",
    )
```

Or use the service directly:

```python
with CommenceSession() as db:
    db.connections.assign(
        "Person", "John Smith",
        "Is Employed by",
        "Company", "Acme Corp",
    )
```

## Unassigning Connections

Remove a connection between two items:

```python
with CommenceSession() as db:
    db.unassign_connection(
        "Person", "John Smith",
        "Is Employed by",
        "Company", "Acme Corp",
    )
```

## Filtering by Connection

You can also filter query results based on connections. See [Query & Filtering](querying.md#connection-filters) for details.

```python
with CommenceSession() as db:
    # People connected to Acme Corp
    results = (
        db.query("Person")
        .where_connection("Is Employed by", "Company", "Acme Corp")
        .execute()
    )

    # People whose employer is in NJ
    results = (
        db.query("Person")
        .where_connected_field(
            "Is Employed by", "Company", "State", "Contains", "NJ"
        )
        .execute()
    )
```

## How Connections Work in Commence

!!! note "DDE Only"
    Connections cannot be created or deleted through the cursor/rowset API — they **must** use DDE Execute commands. pycommence-vibes handles this automatically via the `ConnectionService`.

- Connections are defined at the category level by a Commence administrator
- Each connection has a **name**, a **from-category**, and a **to-category**
- An item can have zero or more connected items through each connection
- Connection names are not unique globally — they are scoped to a from/to category pair

