"""Schema introspection service – discovers categories, fields, connections via DDE conversation.

Results are transparently cached to disk via ``SchemaCache`` for fast
repeated lookups.  The cache is invalidated when Commence's
``METADATA.PIM`` file changes.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import TYPE_CHECKING

from pycommence.cache import SchemaCache
from pycommence.exceptions import SchemaError
from pycommence.models import (
    CategoryInfo,
    ConnectionInfo,
    FieldInfo,
    FieldType,
)

if TYPE_CHECKING:
    from pycommence._com.connection import CommenceDB

log = logging.getLogger(__name__)

# Delimiter we inject into DDE requests so we can split reliably
_DELIM = "|"


class SchemaService:
    """Read-only schema introspection powered by ICommenceConversation (DDE requests).

    Schema data is transparently cached to disk.  Use ``invalidate_cache()``
    to force a fresh lookup.
    """

    def __init__(self, db: "CommenceDB") -> None:
        self._db = db
        self._conv = db.get_conversation()
        self._cache = SchemaCache(db.name, db.path)
        self._cache.check_staleness()

    # -- cache management ----------------------------------------------------
    def invalidate_cache(self) -> None:
        """Drop all cached schema data (in-memory and on-disk).

        Call this if you know the database schema has changed.
        """
        self._cache.clear()

    # -- categories ----------------------------------------------------------
    def list_categories(self) -> list[str]:
        """Return all category (table) names in the database.

        Returns:
            Sorted list of category name strings.

        Example::

            categories = db.schema.list_categories()
            # ["Account", "Contact", "Hire", ...]
        """
        cached = self._cache.get_category_names()
        if cached is not None:
            return cached

        raw = self._conv.request(f'[GetCategoryNames("{_DELIM}")]')
        names = [c.strip() for c in raw.split(_DELIM) if c.strip()]
        self._cache.set_category_names(names)
        self._cache.save()
        return names

    def get_category_count(self) -> int:
        """Return the total number of categories in the database.

        Returns:
            Category count as an integer.
        """
        raw = self._conv.request("[GetCategoryCount()]")
        return int(raw.strip())

    def get_category_definition(self, category: str) -> CategoryInfo:
        """Return metadata for a category.

        Parses the ``GetCategoryDefinition`` DDE response into a
        ``CategoryInfo`` dataclass including max items, shared status,
        duplicate and clarify settings.

        Args:
            category: Commence category name.

        Returns:
            A ``CategoryInfo`` instance.

        Raises:
            SchemaError: If the DDE response is unparseable.

        Example::

            info = db.schema.get_category_definition("Hire")
            print(info.max_items, info.has_clarify)
        """
        raw = self._conv.request(f'[GetCategoryDefinition("{category}", "{_DELIM}")]')
        parts = raw.split(_DELIM)
        if len(parts) < 2:
            raise SchemaError(f"Unexpected GetCategoryDefinition response: {raw!r}")

        try:
            max_items = int(parts[0].strip())
            # Strip whitespace/newlines from flags — docs say {C} may be
            # separated from {D} by a newline in some Commence versions.
            flag_str = "".join(parts[1].split()).zfill(10)
            # Named positions from the right: ...{S}{M}{D}{C}
            is_shared = flag_str[-4] == "1"
            # flag_str[-3] is M (max items already parsed from parts[0])
            allows_duplicates = flag_str[-2] == "1"
            has_clarify = flag_str[-1] == "1"
        except (ValueError, IndexError) as exc:
            raise SchemaError(
                f"Failed to parse GetCategoryDefinition flags for "
                f"'{category}': {raw!r}"
            ) from exc

        clarify_sep = parts[2].strip() if len(parts) > 2 else ""
        clarify_field = parts[3].strip() if len(parts) > 3 else ""

        return CategoryInfo(
            name=category,
            max_items=max_items,
            is_shared=is_shared,
            allows_duplicates=allows_duplicates,
            has_clarify=has_clarify,
            clarify_separator=clarify_sep,
            clarify_field=clarify_field,
        )

    # -- fields --------------------------------------------------------------
    def get_field_names(self, category: str) -> list[str]:
        """Return all field names for a category.

        Args:
            category: Commence category name.

        Returns:
            List of field name strings.

        Example::

            names = db.schema.get_field_names("Contact")
            # ["Name", "Email", "Phone", ...]
        """
        cached = self._cache.get_field_names(category)
        if cached is not None:
            return cached

        raw = self._conv.request(f'[GetFieldNames("{category}", "{_DELIM}")]')
        names = [f.strip() for f in raw.split(_DELIM) if f.strip()]
        # Don't save yet — get_fields will save a richer version
        return names

    def get_field_count(self, category: str) -> int:
        """Return the number of fields in a category.

        Args:
            category: Commence category name.

        Returns:
            Field count as an integer.
        """
        raw = self._conv.request(f'[GetFieldCount("{category}")]')
        return int(raw.strip())

    def get_field_definition(self, category: str, field_name: str) -> FieldInfo:
        """Return metadata for a single field.

        Parses the ``GetFieldDefinition`` DDE response into a ``FieldInfo``
        dataclass including type, max chars, flags, and default value.

        Args:
            category: Commence category name.
            field_name: Name of the field to inspect.

        Returns:
            A ``FieldInfo`` instance.

        Raises:
            SchemaError: If the DDE response is unparseable.

        Example::

            field = db.schema.get_field_definition("Contact", "Email")
            print(field.field_type, field.max_chars)
        """
        raw = self._conv.request(
            f'[GetFieldDefinition("{category}", "{field_name}", "{_DELIM}")]'
        )
        parts = raw.split(_DELIM)
        if len(parts) < 3:
            raise SchemaError(
                f"Unexpected GetFieldDefinition response for "
                f"'{category}'.'{field_name}': {raw!r}"
            )

        field_type_code = int(parts[0].strip())
        flags = parts[1].strip().zfill(10)
        # flags: 000000{C}{S}{M}{R}
        is_combo = flags[-4] == "1"
        is_shared = flags[-3] == "1"
        is_mandatory = flags[-2] == "1"
        is_recurring = flags[-1] == "1"

        max_chars = int(parts[2].strip()) if parts[2].strip() else 0
        default = parts[3].strip() if len(parts) > 3 else ""

        return FieldInfo(
            name=field_name,
            field_type=FieldType.from_code(field_type_code),
            max_chars=max_chars,
            default=default,
            is_combo=is_combo,
            is_shared=is_shared,
            is_mandatory=is_mandatory,
            is_recurring=is_recurring,
        )

    def get_fields(self, category: str) -> list[FieldInfo]:
        """Return full ``FieldInfo`` for every field in a category.

        Calls ``get_field_names`` then ``get_field_definition`` for each.
        Results are cached to disk.

        Args:
            category: Commence category name.

        Returns:
            List of ``FieldInfo`` instances, one per field.

        Example::

            for f in db.schema.get_fields("Contact"):
                print(f"{f.name}: {f.field_type.name} (max={f.max_chars})")
        """
        # Try cache
        cached_dicts = self._cache.get_fields(category)
        if cached_dicts is not None:
            return [
                FieldInfo(
                    name=d["name"],
                    field_type=FieldType.from_code(d["field_type"]),
                    max_chars=d.get("max_chars", 0),
                    default=d.get("default", ""),
                    is_combo=d.get("is_combo", False),
                    is_shared=d.get("is_shared", False),
                    is_mandatory=d.get("is_mandatory", False),
                    is_recurring=d.get("is_recurring", False),
                )
                for d in cached_dicts
            ]

        names = self.get_field_names(category)
        fields = [self.get_field_definition(category, n) for n in names]

        # Persist to cache
        self._cache.set_fields(
            category,
            names,
            [asdict(f) for f in fields],
        )
        self._cache.save()
        return fields

    # -- connections ---------------------------------------------------------
    def get_connection_names(self, category: str) -> list[ConnectionInfo]:
        """Return all connections where *category* is the From-category.

        Args:
            category: Commence category name.

        Returns:
            List of ``ConnectionInfo`` instances, each with a ``name``
            and ``to_category``.

        Example::

            for conn in db.schema.get_connection_names("Person"):
                print(f"{conn.name} → {conn.to_category}")
        """
        # Try cache
        cached_dicts = self._cache.get_connections(category)
        if cached_dicts is not None:
            return [
                ConnectionInfo(name=d["name"], to_category=d["to_category"])
                for d in cached_dicts
            ]

        raw = self._conv.request(
            f'[GetConnectionNames("{category}", "{_DELIM}", "::")]'
        )
        connections: list[ConnectionInfo] = []
        for entry in raw.split(_DELIM):
            entry = entry.strip()
            if not entry:
                continue
            if "::" in entry:
                conn_name, to_cat = entry.split("::", 1)
                connections.append(
                    ConnectionInfo(name=conn_name.strip(), to_category=to_cat.strip())
                )
            else:
                # Fallback: if no delimiter between conn/cat, treat whole thing as name
                connections.append(ConnectionInfo(name=entry, to_category=""))

        self._cache.set_connections(
            category,
            [{"name": c.name, "to_category": c.to_category} for c in connections],
        )
        self._cache.save()
        return connections

    def get_connection_count(self, category: str) -> int:
        """Return the number of connections defined for a category.

        Args:
            category: Commence category name.

        Returns:
            Connection count as an integer.
        """
        raw = self._conv.request(f'[GetConnectionCount("{category}")]')
        return int(raw.strip())

    # -- row count via cursor (more reliable than DDE for large sets) --------
    def get_row_count(self, category: str) -> int:
        """Return the number of items (rows) in a category.

        Uses a cursor internally, which is more reliable than DDE for
        large result sets.

        Args:
            category: Commence category name.

        Returns:
            Row count as an integer.

        Example::

            count = db.schema.get_row_count("Hire")
            print(f"{count} rows in Hire")
        """
        with self._db.get_cursor(category) as cur:
            return cur.row_count

    # -- views ---------------------------------------------------------------
    def get_view_names(self, category: str | None = None) -> list[str]:
        """Return saved view names.

        Args:
            category: If provided, return only views for this category.
                If ``None``, return all views in the database.

        Returns:
            List of view name strings.

        Example::

            all_views = db.schema.get_view_names()
            contact_views = db.schema.get_view_names("Contact")
        """
        if category:
            raw = self._conv.request(f'[GetViewNames("{category}", "{_DELIM}")]')
        else:
            raw = self._conv.request(f'[GetViewNames("{_DELIM}")]')
        return [v.strip() for v in raw.split(_DELIM) if v.strip()]

    # -- forms ---------------------------------------------------------------
    def get_form_names(self, category: str) -> list[str]:
        """Return form names defined for a category.

        Args:
            category: Commence category name.

        Returns:
            List of form name strings.

        Example::

            forms = db.schema.get_form_names("Contact")
        """
        raw = self._conv.request(f'[GetFormNames("{category}", "{_DELIM}")]')
        return [f.strip() for f in raw.split(_DELIM) if f.strip()]
