"""Migration service — copy data between Commence categories with field mapping."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycommence.services.reader import ReaderService
    from pycommence.services.writer import WriterService

log = logging.getLogger(__name__)


def copy_category(
    reader: "ReaderService",
    writer: "WriterService",
    from_category: str,
    to_category: str,
    field_map: dict[str, str] | None = None,
    *,
    max_rows: int = 50_000,
) -> int:
    """Copy rows from one category to another, optionally mapping field names.

    Reads all rows from *from_category* and writes them to *to_category*.
    If *field_map* is provided, source field names are renamed to target
    field names before writing.

    Args:
        reader: ``ReaderService`` to read from the source.
        writer: ``WriterService`` to write to the target.
        from_category: Source category name.
        to_category: Target category name.
        field_map: Optional mapping of ``source_field → target_field``.
            Fields not in the map are passed through unchanged.
            Set a value to ``None`` to exclude that field.
        max_rows: Maximum rows to copy.

    Returns:
        The number of rows copied.

    Example::

        copied = copy_category(
            reader, writer,
            "OldContacts", "Contact",
            field_map={"FullName": "Name", "E-Mail": "Email"},
        )
    """
    source_rows = reader.read_rows(
        from_category,
        max_rows=max_rows,
        get_ids=False,
    )
    if not source_rows:
        log.info("No rows found in %s", from_category)
        return 0

    mapped_rows: list[dict[str, str]] = []
    for row in source_rows:
        if field_map:
            mapped: dict[str, str] = {}
            for src_field, value in row.columns.items():
                if src_field in field_map:
                    target_field = field_map[src_field]
                    if target_field is not None:
                        mapped[target_field] = value
                else:
                    mapped[src_field] = value
            mapped_rows.append(mapped)
        else:
            mapped_rows.append(row.to_dict())

    count = writer.add_rows(to_category, mapped_rows)
    log.info(
        "Copied %d rows from %s → %s",
        count, from_category, to_category,
    )
    return count

