"""Reader service – query/read rows from any Commence category via cursor + QueryRowSet."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pycommence._com.constants import BOOKMARK_BEGINNING, CMC_CURSOR_CATEGORY
from pycommence.models import RelatedColumn, RowResult

if TYPE_CHECKING:
    from pycommence._com.connection import CommenceDB

log = logging.getLogger(__name__)

# Default batch size when paging through large result sets
_DEFAULT_BATCH = 200


class ReaderService:
    """Read rows from Commence categories via cursor + QueryRowSet.

    Handles pagination automatically: large result sets are read in
    batches of ``_DEFAULT_BATCH`` (200) rows to stay within Commence's
    per-request data limits.
    """

    def __init__(self, db: "CommenceDB") -> None:
        self._db = db

    def read_rows(
        self,
        category: str,
        *,
        columns: list[str] | None = None,
        related_columns: list[RelatedColumn] | None = None,
        filters: list[str] | None = None,
        logic: str | None = None,
        sort: str | None = None,
        max_rows: int = 500,
        get_ids: bool = True,
        canonical: bool = False,
        mode: int = CMC_CURSOR_CATEGORY,
    ) -> list[RowResult]:
        """Read rows from a category with optional filtering and sorting.

        Results are paginated internally in batches of 200 rows to avoid
        hitting Commence data-size limits.

        Args:
            category: Commence category name (or view name when
                ``mode=CMC_CURSOR_VIEW``).
            columns: Specific field names. ``None`` → all fields.
            related_columns: Connected/indirect fields to include via
                ``SetRelatedColumn``.
            filters: List of DDE-style filter strings (one per clause).
            logic: Filter logic string (e.g. ``"And, And, And"``).
            sort: DDE-style sort string.
            max_rows: Upper limit on rows returned.
            get_ids: Whether to fetch each row's unique ID.
            canonical: If ``True``, return dates as ``yyyymmdd``, numbers
                without locale formatting, times as ``hh:mm``, and
                checkboxes as ``TRUE``/``FALSE``.
            mode: Cursor mode — ``CMC_CURSOR_CATEGORY`` (default) or
                ``CMC_CURSOR_VIEW``.

        Returns:
            A list of ``RowResult`` objects.

        Raises:
            CursorError: If the cursor cannot be created.
        """
        with self._db.get_cursor(category, mode=mode) as cur:
            # columns
            num_direct = 0
            if columns:
                cur.set_columns(columns)
                num_direct = len(columns)
            else:
                cur.set_columns_all()
                # column count will be determined from the rowset

            # related (indirect) columns
            if related_columns:
                # Related columns are appended after the direct columns.
                # If no explicit columns were set, we need to know how many
                # direct columns there are so we can assign the right indices.
                if not columns:
                    # For category cursors with all columns, column_count
                    # gives us the count of direct columns.
                    num_direct = cur.column_count
                for i, rc in enumerate(related_columns):
                    cur.set_related_column(
                        num_direct + i,
                        rc.connection_name,
                        rc.connected_category,
                        rc.field_name,
                    )

            # filters
            if filters:
                for f in filters:
                    cur.set_filter(f)
                if logic:
                    cur.set_logic(logic)

            # sort
            if sort:
                cur.set_sort(sort)

            total = min(cur.row_count, max_rows)
            if total == 0:
                return []

            cur.seek_row(BOOKMARK_BEGINNING, 0)
            results: list[RowResult] = []
            remaining = total

            while remaining > 0:
                batch_size = min(remaining, _DEFAULT_BATCH)
                rs = cur.get_query_rowset(batch_size)
                labels = rs.column_labels()
                for r in range(rs.row_count):
                    row_data = {
                        labels[c]: rs.get_row_value(r, c, canonical=canonical)
                        for c in range(rs.column_count)
                    }
                    row_id = rs.get_row_id(r) if get_ids else None
                    results.append(RowResult(columns=row_data, row_id=row_id))
                remaining -= rs.row_count
                if rs.row_count < batch_size:
                    break  # no more rows

        return results

    def read_by_id(
        self,
        category: str,
        row_id: str,
        *,
        columns: list[str] | None = None,
        canonical: bool = False,
    ) -> RowResult:
        """Read a single row by its unique row ID.

        Args:
            category: Commence category name.
            row_id: Unique row identifier (from a previous read or add).
            columns: Specific field names. ``None`` → all fields.
            canonical: If ``True``, use locale-independent formatting.

        Returns:
            A single ``RowResult``.

        Raises:
            RowsetError: If no row matches the given ID.
        """
        with self._db.get_cursor(category) as cur:
            if columns:
                cur.set_columns(columns)
            else:
                cur.set_columns_all()

            rs = cur.get_query_rowset_by_id(row_id)
            if rs.row_count == 0:
                from pycommence.exceptions import RowsetError
                raise RowsetError(f"No row found for ID '{row_id}' in '{category}'")

            labels = rs.column_labels()
            row_data = {
                labels[c]: rs.get_row_value(0, c, canonical=canonical)
                for c in range(rs.column_count)
            }
            return RowResult(columns=row_data, row_id=row_id)

    def count(
        self,
        category: str,
        *,
        filters: list[str] | None = None,
        logic: str | None = None,
        mode: int = CMC_CURSOR_CATEGORY,
    ) -> int:
        """Return the number of rows in a category, respecting optional filters.

        Args:
            category: Commence category name.
            filters: Optional DDE-style filter strings.
            logic: Optional filter logic string.
            mode: Cursor mode.

        Returns:
            Row count as an integer.
        """
        with self._db.get_cursor(category, mode=mode) as cur:
            if filters:
                for f in filters:
                    cur.set_filter(f)
                if logic:
                    cur.set_logic(logic)
            return cur.row_count

