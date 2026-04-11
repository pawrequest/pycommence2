"""Wrapper around ICommenceCursor – manages columns, filters, sorts, and rowset creation."""

from __future__ import annotations

import logging
from typing import Any

from pycommence._com.constants import (
    BOOKMARK_BEGINNING,
    CMC_FLAG_ALL,
)
from pycommence._com.rowset import RowsetWrapper
from pycommence.exceptions import CursorError, RowsetError

log = logging.getLogger(__name__)


class CursorWrapper:
    """Thin, deterministic wrapper around ICommenceCursor."""

    def __init__(self, raw_cursor: Any) -> None:
        self._cur = raw_cursor

    @property
    def category(self) -> str:
        return self._cur.Category

    @property
    def column_count(self) -> int:
        val = self._cur.ColumnCount
        if val == -1:
            raise CursorError("ColumnCount returned -1")
        return val

    @property
    def row_count(self) -> int:
        val = self._cur.RowCount
        if val == -1:
            raise CursorError("RowCount returned -1")
        return val

    @property
    def shared(self) -> bool:
        return bool(self._cur.Shared)

    def set_columns(self, fields: list[str]) -> None:
        for idx, name in enumerate(fields):
            if not self._cur.SetColumn(idx, name, 0):
                raise CursorError(f"SetColumn({idx}, '{name}') failed")

    def set_columns_all(self) -> None:
        """No-op for category-mode cursors which already include all fields.

        When a cursor is opened in ``CMC_CURSOR_CATEGORY`` mode the default
        column set already contains every supported field, so no ``SetColumn``
        call is required.  Do **not** call this on view cursors — use
        :meth:`set_columns` explicitly instead.
        """

    def set_related_column(
        self, col_index: int, connection_name: str,
        connected_category: str, field_name: str,
    ) -> None:
        if not self._cur.SetRelatedColumn(
            col_index, connection_name, connected_category, field_name, 0
        ):
            raise CursorError(
                f"SetRelatedColumn({col_index}, '{connection_name}', "
                f"'{connected_category}', '{field_name}') failed"
            )

    def set_filter(self, filter_text: str) -> None:
        if not self._cur.SetFilter(filter_text, 0):
            raise CursorError(f"SetFilter failed: {filter_text}")

    def set_logic(self, logic_text: str) -> None:
        if not self._cur.SetLogic(logic_text, 0):
            raise CursorError(f"SetLogic failed: {logic_text}")

    def set_sort(self, sort_text: str) -> None:
        if not self._cur.SetSort(sort_text, 0):
            raise CursorError(f"SetSort failed: {sort_text}")

    def seek_row(self, bookmark: int = BOOKMARK_BEGINNING, rows: int = 0) -> int:
        result = self._cur.SeekRow(bookmark, rows)
        if result == -1:
            raise CursorError(f"SeekRow({bookmark}, {rows}) failed")
        return result

    def seek_row_approx(self, numerator: int, denominator: int) -> int:
        """Seek to an approximate position in the cursor.

        Args:
            numerator: Numerator of the fractional position.
            denominator: Denominator of the fractional position.

        Returns:
            The actual row number seeked to.
        """
        result = self._cur.SeekRowApprox(numerator, denominator)
        if result == -1:
            raise CursorError(f"SeekRowApprox({numerator}, {denominator}) failed")
        return result

    # -- view-linking methods ------------------------------------------------
    def set_active_item(self, category_name: str, row_id: str) -> None:
        """Set active item for view cursors using a view linking filter.

        Args:
            category_name: Category of the active item.
            row_id: Row ID of the active item.
        """
        if not self._cur.SetActiveItem(category_name, row_id, 0):
            raise CursorError(
                f"SetActiveItem('{category_name}', '{row_id}') failed"
            )

    def set_active_date(self, date_str: str) -> None:
        """Set active date for view cursors using a view linking filter.

        Supports AI date values like ``'today'``.

        Args:
            date_str: Date string or AI date value.
        """
        if not self._cur.SetActiveDate(date_str, 0):
            raise CursorError(f"SetActiveDate('{date_str}') failed")

    def set_active_date_range(self, start_date: str, end_date: str) -> None:
        """Set active date range for view cursors using a view linking filter.

        Args:
            start_date: Start of the date range.
            end_date: End of the date range.
        """
        if not self._cur.SetActiveDateRange(start_date, end_date, 0):
            raise CursorError(
                f"SetActiveDateRange('{start_date}', '{end_date}') failed"
            )

    # -- rowset factories ----------------------------------------------------
    def get_query_rowset(self, count: int, flags: int = 0) -> RowsetWrapper:
        raw = self._cur.GetQueryRowSet(count, flags)
        if raw is None:
            raise RowsetError(f"GetQueryRowSet({count}) returned NULL")
        return RowsetWrapper(raw)

    def get_query_rowset_by_id(self, row_id: str, flags: int = 0) -> RowsetWrapper:
        raw = self._cur.GetQueryRowSetByID(row_id, flags)
        if raw is None:
            raise RowsetError(f"GetQueryRowSetByID('{row_id}') returned NULL")
        return RowsetWrapper(raw)

    def get_add_rowset(self, count: int = 1, flags: int = 0) -> RowsetWrapper:
        raw = self._cur.GetAddRowSet(count, flags)
        if raw is None:
            raise RowsetError(f"GetAddRowSet({count}) returned NULL")
        return RowsetWrapper(raw)

    def get_edit_rowset(self, count: int = 1, flags: int = 0) -> RowsetWrapper:
        raw = self._cur.GetEditRowSet(count, flags)
        if raw is None:
            raise RowsetError(f"GetEditRowSet({count}) returned NULL")
        return RowsetWrapper(raw)

    def get_edit_rowset_by_id(self, row_id: str, flags: int = 0) -> RowsetWrapper:
        raw = self._cur.GetEditRowSetByID(row_id, flags)
        if raw is None:
            raise RowsetError(f"GetEditRowSetByID('{row_id}') returned NULL")
        return RowsetWrapper(raw)

    def get_delete_rowset(self, count: int = 1, flags: int = 0) -> RowsetWrapper:
        raw = self._cur.GetDeleteRowSet(count, flags)
        if raw is None:
            raise RowsetError(f"GetDeleteRowSet({count}) returned NULL")
        return RowsetWrapper(raw)

    def get_delete_rowset_by_id(self, row_id: str, flags: int = 0) -> RowsetWrapper:
        raw = self._cur.GetDeleteRowSetByID(row_id, flags)
        if raw is None:
            raise RowsetError(f"GetDeleteRowSetByID('{row_id}') returned NULL")
        return RowsetWrapper(raw)

    def __enter__(self) -> "CursorWrapper":
        return self

    def __exit__(self, *exc: object) -> None:
        self._cur = None

    @property
    def raw(self) -> Any:
        return self._cur

