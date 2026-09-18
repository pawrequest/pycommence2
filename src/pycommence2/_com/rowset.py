"""Unified wrapper for all Commence rowset types (Query/Add/Edit/Delete)."""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from pycommence2._com.constants import CMC_FLAG_CANONICAL, CMC_FLAG_FIELD_NAME
from pycommence2._com.retry import com_retry
from pycommence2.exceptions import RowsetError

if TYPE_CHECKING:
    from pycommence2._com.cursor import CursorWrapper

log = logging.getLogger(__name__)


class RowsetWrapper:
    """Duck-typed wrapper that works with Query, Add, Edit, and Delete rowsets.

    All four rowset types share: RowCount, ColumnCount, GetRowValue,
    GetColumnLabel, GetColumnIndex, GetRow.
    Add/Edit additionally have ModifyRow + Commit.
    Delete additionally has DeleteRow + Commit.
    Query/Edit/Delete have GetRowID.
    """

    def __init__(self, raw_rowset: Any) -> None:
        self._rs = raw_rowset

    # -- shared properties ---------------------------------------------------
    @property
    def row_count(self) -> int:
        val = self._rs.RowCount
        if val == -1:
            raise RowsetError('RowCount returned -1')
        return val

    @property
    def column_count(self) -> int:
        val = self._rs.ColumnCount
        if val == -1:
            raise RowsetError('ColumnCount returned -1')
        return val

    # -- shared read methods -------------------------------------------------
    def get_row_value(self, row: int, col: int, canonical: bool = True) -> str:
        flags = CMC_FLAG_CANONICAL if canonical else 0
        val = self._rs.GetRowValue(row, col, flags)
        if val is None:
            raise RowsetError(f'GetRowValue({row}, {col}) returned NULL')
        return val

    def get_column_label(self, col: int, field_name: bool = False) -> str:
        flags = CMC_FLAG_FIELD_NAME if field_name else 0
        val = self._rs.GetColumnLabel(col, flags)
        if val is None:
            raise RowsetError(f'GetColumnLabel({col}) returned NULL')
        return val

    def get_column_index(self, label: str, field_name: bool = True) -> int:
        flags = CMC_FLAG_FIELD_NAME if field_name else 0
        idx = self._rs.GetColumnIndex(label, flags)
        if idx == -1:
            raise RowsetError(f"GetColumnIndex('{label}') returned -1 (not found)")
        return idx

    def get_row(self, row: int, delim: str = '\t', canonical: bool = True) -> str:
        flags = CMC_FLAG_CANONICAL if canonical else 0
        val = self._rs.GetRow(row, delim, flags)
        if val is None:
            raise RowsetError(f'GetRow({row}) returned NULL')
        return val

    def get_row_id(self, row: int) -> str:
        val = self._rs.GetRowID(row, 0)
        if val is None:
            raise RowsetError(f'GetRowID({row}) returned NULL')
        return val

    def get_shared(self, row: int) -> bool:
        return bool(self._rs.GetShared(row))

    def get_field_to_file(
        self,
        row: int,
        col: int,
        filename: str,
        canonical: bool = True,
    ) -> int:
        """Save a field value to a file.

        Args:
            row: Row index.
            col: Column index.
            filename: Destination file path.
            canonical: If ``True``, use canonical data format.

        Returns:
            File size in bytes, or 0 if no data.
        """
        flags = CMC_FLAG_CANONICAL if canonical else 0
        result = self._rs.GetFieldToFile(row, col, filename, flags)
        if result is None:
            raise RowsetError(f"GetFieldToFile({row}, {col}, '{filename}') returned NULL")
        return result

    # -- labels helper -------------------------------------------------------
    def column_labels(self, field_name: bool = True) -> list[str]:
        """Return all column labels as a list."""
        return [self.get_column_label(i, field_name=field_name) for i in range(self.column_count)]

    # -- modify methods (Add / Edit rowsets) ---------------------------------
    def modify_row(self, row: int, col: int, value: str) -> None:
        result = self._rs.ModifyRow(row, col, value, 0)
        if result != 0:
            raise RowsetError(f"ModifyRow({row}, {col}, '{value[:50]}...') failed")

    @com_retry()
    def commit(self) -> None:
        result = self._rs.Commit(0)
        if result != 0:
            raise RowsetError('Commit() failed')

    # -- delete method (Delete rowsets) --------------------------------------
    def delete_row(self, row: int) -> None:
        result = self._rs.DeleteRow(row, 0)
        if result != 0:
            raise RowsetError(f'DeleteRow({row}) failed')

    # -- commit-get-cursor (Add rowsets) ------------------------------------
    def commit_get_cursor(self) -> CursorWrapper | None:
        """Commit the rowset and return a cursor over the newly added rows.

        Returns ``None`` if the underlying COM call fails or is unsupported.
        """
        raw_cursor = self._rs.CommitGetCursor(0)
        if raw_cursor is None:
            return None
        from pycommence2._com.cursor import CursorWrapper

        return CursorWrapper(raw_cursor)

    @property
    def raw(self) -> Any:
        return self._rs
