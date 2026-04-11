"""Writer service – create, update, delete rows in any Commence category.

All mutations go through the cursor/rowset API (Add/Edit/DeleteRowSet).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pycommence._com.constants import BOOKMARK_BEGINNING
from pycommence.exceptions import RowsetError

if TYPE_CHECKING:
    from pycommence._com.connection import CommenceDB

log = logging.getLogger(__name__)


class WriterService:
    """Create, update, and delete rows in Commence categories.

    All mutations go through the cursor/rowset API (Add/Edit/DeleteRowSet).
    """

    def __init__(self, db: "CommenceDB") -> None:
        self._db = db

    # -- CREATE --------------------------------------------------------------
    def add_row(
        self,
        category: str,
        fields: dict[str, str],
    ) -> str | None:
        """Add a single row to *category* and return its row ID (if obtainable).

        Args:
            category: Target Commence category.
            fields: Mapping of field_name → value (text form).

        Returns:
            The new row's ID if we can retrieve it via ``CommitGetCursor``,

        Raises:
            RowsetError: If the add operation fails.

        Example::

            new_id = session.add("Contact", {"Name": "Jane Doe"})
        """
        with self._db.get_cursor(category) as cur:
            # We need the columns in the cursor to match the fields we want to set.
            # Using all columns so GetColumnIndex works for any field.
            cur.set_columns_all()

            rs = cur.get_add_rowset(1)
            for field_name, value in fields.items():
                col_idx = rs.get_column_index(field_name)
                rs.modify_row(0, col_idx, value)

            # Commit and try to get the new row's ID
            # CommitGetCursor returns a new cursor for the added rows
            new_cur = rs.commit_get_cursor()
            if new_cur is not None:
                with new_cur:
                    if new_cur.row_count > 0:
                        new_rs = new_cur.get_query_rowset(1)
                        return new_rs.get_row_id(0)
            return None

    def add_rows(
        self,
        category: str,
        rows: list[dict[str, str]],
    ) -> int:
        """Add multiple rows in a single batch.

        Args:
            category: Target Commence category.
            rows: List of field-value dicts, one per row.

        Returns:
            The number of rows added.

        Example::

            count = session.add_many("Contact", [
                {"Name": "Alice"}, {"Name": "Bob"},
            ])
        """
        count = len(rows)
        if count == 0:
            return 0

        with self._db.get_cursor(category) as cur:
            cur.set_columns_all()
            rs = cur.get_add_rowset(count)

            for row_idx, field_values in enumerate(rows):
                for field_name, value in field_values.items():
                    col_idx = rs.get_column_index(field_name)
                    rs.modify_row(row_idx, col_idx, value)

            rs.commit()
        return count

    # -- UPDATE --------------------------------------------------------------
    def edit_row_by_id(
        self,
        category: str,
        row_id: str,
        fields: dict[str, str],
    ) -> None:
        """Edit a single row identified by its unique row ID.

        Args:
            category: Commence category name.
            row_id: Unique row identifier.
            fields: Mapping of field_name → new_value.

        Raises:
            RowsetError: If no row matches the given ID.
        """
        with self._db.get_cursor(category) as cur:
            cur.set_columns_all()
            rs = cur.get_edit_rowset_by_id(row_id)
            if rs.row_count == 0:
                raise RowsetError(f"No row found for ID '{row_id}' in '{category}'")

            for field_name, value in fields.items():
                col_idx = rs.get_column_index(field_name)
                rs.modify_row(0, col_idx, value)

            rs.commit()

    def edit_rows(
        self,
        category: str,
        fields: dict[str, str],
        *,
        filters: list[str] | None = None,
        logic: str | None = None,
        max_rows: int = 100,
    ) -> int:
        """Edit rows matching optional filters.

        Args:
            category: Commence category name.
            fields: Mapping of field_name → new_value applied to all
                matching rows.
            filters: DDE-style filter strings (max 4).
            logic: Filter logic string (e.g. ``"And, Or, And"``).
            max_rows: Safety cap on how many rows can be edited.

        Returns:
            The number of rows edited.
        """
        with self._db.get_cursor(category) as cur:
            cur.set_columns_all()

            if filters:
                for f in filters:
                    cur.set_filter(f)
                if logic:
                    cur.set_logic(logic)

            total = min(cur.row_count, max_rows)
            if total == 0:
                return 0

            cur.seek_row(BOOKMARK_BEGINNING, 0)
            rs = cur.get_edit_rowset(total)

            for row_idx in range(rs.row_count):
                for field_name, value in fields.items():
                    col_idx = rs.get_column_index(field_name)
                    rs.modify_row(row_idx, col_idx, value)

            rs.commit()
            return rs.row_count

    # -- DELETE --------------------------------------------------------------
    def delete_row_by_id(self, category: str, row_id: str) -> None:
        """Delete a single row by its unique row ID.

        Args:
            category: Commence category name.
            row_id: Unique row identifier.

        Raises:
            RowsetError: If no row matches the given ID.
        """
        with self._db.get_cursor(category) as cur:
            rs = cur.get_delete_rowset_by_id(row_id)
            if rs.row_count == 0:
                raise RowsetError(f"No row found for ID '{row_id}' in '{category}'")
            rs.delete_row(0)
            rs.commit()

    def delete_rows(
        self,
        category: str,
        *,
        filters: list[str] | None = None,
        logic: str | None = None,
        max_rows: int = 100,
    ) -> int:
        """Delete rows matching optional filters.

        Args:
            category: Commence category name.
            filters: DDE-style filter strings (max 4).
            logic: Filter logic string (e.g. ``"And, Or, And"``).
            max_rows: Safety cap on how many rows can be deleted.

        Returns:
            The number of rows deleted.
        """
        with self._db.get_cursor(category) as cur:

            if filters:
                for f in filters:
                    cur.set_filter(f)
                if logic:
                    cur.set_logic(logic)

            total = min(cur.row_count, max_rows)
            if total == 0:
                return 0

            cur.seek_row(BOOKMARK_BEGINNING, 0)
            rs = cur.get_delete_rowset(total)

            for row_idx in range(rs.row_count):
                rs.delete_row(row_idx)

            rs.commit()
            return rs.row_count

