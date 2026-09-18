"""Data models for pycommence2 – pure Python dataclasses, no COM references."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, time
from enum import IntEnum
from typing import Any


# ---------------------------------------------------------------------------
# Field type enum – values match Commence GetFieldDefinition responses
# ---------------------------------------------------------------------------
class FieldType(IntEnum):
    """Commence field data types.

    Integer values match the codes returned by the
    ``GetFieldDefinition`` DDE command.
    """

    TEXT = 0
    NUMBER = 1
    DATE = 2
    TELEPHONE = 3
    CHECK_BOX = 7
    NAME = 11
    DATA_FILE = 12
    IMAGE = 13
    TIME = 14
    EXCEL_CELL = 15
    CALCULATION = 20
    SEQUENCE = 21
    SELECTION = 22
    EMAIL = 23
    URL = 24

    @classmethod
    def from_code(cls, code: int) -> FieldType:
        """Convert a raw integer code to a ``FieldType``.

        Falls back to ``TEXT`` for unrecognised codes.

        Args:
            code: Integer field-type code from Commence.

        Returns:
            The matching ``FieldType`` member.
        """
        try:
            return cls(code)
        except ValueError:
            return cls.TEXT  # graceful fallback for unknown types


# ---------------------------------------------------------------------------
# Schema models
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class FieldInfo:
    """Metadata about a single field in a Commence category.

    Attributes:
        name: Field name.
        field_type: Data type (see ``FieldType``).
        max_chars: Maximum character length (0 if unlimited).
        default: Default value string (empty if none).
        is_combo: Whether the field uses a combo-box (predefined values).
        is_shared: Whether the field is shared in workgroup mode.
        is_mandatory: Whether the field is required.
        is_recurring: Whether the field participates in recurrence.
    """

    name: str
    field_type: FieldType
    max_chars: int = 0
    default: str = ''
    is_combo: bool = False
    is_shared: bool = False
    is_mandatory: bool = False
    is_recurring: bool = False


@dataclass(frozen=True, slots=True)
class ConnectionInfo:
    """A connection from one category to another.

    Attributes:
        name: Connection name (e.g. ``"Is Employed by"``).
        to_category: Target category name (e.g. ``"Company"``).
    """

    name: str
    to_category: str


@dataclass(frozen=True, slots=True)
class CategoryInfo:
    """Metadata about a Commence category (table).

    Attributes:
        name: Category name.
        max_items: Maximum number of items allowed.
        is_shared: Whether the category is shared in workgroup mode.
        allows_duplicates: Whether duplicate item names are allowed.
        has_clarify: Whether a clarify field is configured.
        clarify_separator: Separator character for clarified names.
        clarify_field: Name of the clarify field (if any).
    """

    name: str
    max_items: int = 32_000
    is_shared: bool = False
    allows_duplicates: bool = False
    has_clarify: bool = False
    clarify_separator: str = ''
    clarify_field: str = ''


# ---------------------------------------------------------------------------
# Row / result models
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class RowResult:
    """A single row of data returned from a query.

    Supports dict-style access via ``row["FieldName"]`` and safe
    access via ``row.get("FieldName", default)``.

    Attributes:
        columns: Mapping of field names to string values.
        row_id: Unique row identifier (for subsequent edit/delete).
            May be ``None`` if IDs were not requested.
    """

    columns: dict[str, str] = field(default_factory=dict)
    row_id: str | None = None

    def __getitem__(self, key: str) -> str:
        """Get a field value by name. Raises ``KeyError`` if missing."""
        return self.columns[key]

    def __contains__(self, key: object) -> bool:
        """Check if a field name exists in this row.

        Example::

            if "Email" in row:
                print(row["Email"])
        """
        return key in self.columns

    def __iter__(self) -> Iterator[str]:
        """Iterate over field names.

        Example::

            for field_name in row:
                print(field_name, row[field_name])
        """
        return iter(self.columns)

    def __len__(self) -> int:
        """Return the number of columns in this row."""
        return len(self.columns)

    def get(self, key: str, default: str = '') -> str:
        """Get a field value by name, returning *default* if missing."""
        return self.columns.get(key, default)

    def keys(self) -> list[str]:
        """Return field names as a list."""
        return list(self.columns.keys())

    def values(self) -> list[str]:
        """Return field values as a list."""
        return list(self.columns.values())

    def items(self) -> list[tuple[str, str]]:
        """Return ``(field_name, value)`` pairs as a list."""
        return list(self.columns.items())

    def to_dict(self) -> dict[str, str]:
        """Return columns as a plain dict.

        Returns:
            A shallow copy of the ``columns`` mapping.

        Example::

            data = row.to_dict()
            json.dumps(data)
        """
        return dict(self.columns)

    def to_typed_dict(self, fields: list[FieldInfo]) -> dict[str, Any]:
        """Coerce string values to Python types based on field metadata.

        Requires **canonical mode** data for reliable parsing of dates,
        numbers, and booleans.

        Args:
            fields: List of ``FieldInfo`` for this category (from
                ``schema.get_fields()``).

        Returns:
            A dict mapping field names to typed values:
            ``int``/``float`` for NUMBER/CALCULATION, ``bool`` for
            CHECK_BOX, ``date`` for DATE, ``time`` for TIME, and
            ``str`` for everything else.  Empty strings become ``None``
            for non-text types.

        Example::

            fields = db.schema.get_fields("Hire")
            rows = db.query("Hire").canonical().limit(10).execute()
            typed = rows[0].to_typed_dict(fields)
            # {"Booked Date": date(2026, 4, 11), "Price": 1234.56, ...}
        """
        field_map = {f.name: f for f in fields}
        result: dict[str, Any] = {}
        for col_name, raw in self.columns.items():
            fi = field_map.get(col_name)
            if fi is None:
                result[col_name] = raw
                continue
            result[col_name] = _coerce_value(raw, fi.field_type)
        return result


ResultTuple = tuple[RowResult, ...]


def _coerce_value(raw: str, ft: FieldType) -> Any:
    """Convert a raw string value to a Python type based on field type."""
    if not raw:
        # Empty string → None for non-text types, "" for text
        if ft in (
            FieldType.TEXT,
            FieldType.NAME,
            FieldType.EMAIL,
            FieldType.URL,
            FieldType.TELEPHONE,
            FieldType.SELECTION,
        ):
            return raw
        return None

    if ft in (FieldType.NUMBER, FieldType.CALCULATION):
        try:
            if '.' in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            return raw

    if ft == FieldType.CHECK_BOX:
        return raw.upper() in ('TRUE', 'YES', '1')

    if ft == FieldType.DATE:
        # Canonical format: yyyymmdd
        try:
            if len(raw) == 8 and raw.isdigit():
                return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
        except (ValueError, IndexError):
            pass
        return raw

    if ft == FieldType.TIME:
        # Canonical format: hh:mm
        try:
            if ':' in raw:
                parts = raw.split(':')
                return time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            pass
        return raw

    if ft == FieldType.SEQUENCE:
        try:
            return int(raw)
        except ValueError:
            return raw

    return raw


# ---------------------------------------------------------------------------
# Watch event model
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class WatchEvent:
    """An event emitted by the poll-based watcher when a row changes.

    Attributes:
        event_type: One of ``"added"``, ``"changed"``, or ``"removed"``.
        row: The :class:`RowResult` associated with the event.
            For ``"removed"`` events this is the last-seen snapshot.
    """

    event_type: str  # "added", "changed", "removed"
    row: RowResult = field(default_factory=lambda: RowResult())


# ---------------------------------------------------------------------------
# Filter / Sort descriptors  (used by QueryBuilder)
# ---------------------------------------------------------------------------
class FilterType:
    """Constants for Commence ViewFilter type codes.

    Attributes:
        FIELD: Field filter (``"F"``).
        CONNECTION_TO_ITEM: Connection to a specific item (``"CTI"``).
        CONNECTION_TO_CATEGORY_TO_ITEM: Indirect connection (``"CTCTI"``).
        CONNECTION_TO_CATEGORY_FIELD: Connection field filter (``"CTCF"``).
    """

    FIELD = 'F'
    CONNECTION_TO_ITEM = 'CTI'
    CONNECTION_TO_CATEGORY_TO_ITEM = 'CTCTI'
    CONNECTION_TO_CATEGORY_FIELD = 'CTCF'


@dataclass(slots=True)
class FilterClause:
    """Describes one ViewFilter clause (1-4).

    Attributes:
        clause_number: Position in the filter list (1–4).
        filter_type: One of ``"F"``, ``"CTI"``, ``"CTCTI"``, ``"CTCF"``.
        not_flag: If ``True``, negate the filter.
        params: Additional parameters (field, qualifier, value, etc.).
    """

    clause_number: int  # 1-4
    filter_type: str  # F, CTI, CTCTI, CTCF
    not_flag: bool = False
    params: tuple[str, ...] = ()


@dataclass(slots=True)
class SortSpec:
    """Describes sort criteria (up to 4 fields).

    Attributes:
        fields: List of ``(field_name, ascending)`` tuples.
            Maximum 4 entries.
    """

    fields: list[tuple[str, bool]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RelatedColumn:
    """A connected/indirect field to include in query results.

    Maps to ``ICommenceCursor.SetRelatedColumn``.

    Attributes:
        connection_name: Connection name (e.g. ``"Relates to"``).
        connected_category: Target category (e.g. ``"Account"``).
        field_name: Field in the connected category.

    Example::

        RelatedColumn("Relates to", "Account", "accountKey")
    """

    connection_name: str
    connected_category: str
    field_name: str
