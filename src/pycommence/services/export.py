"""Export service — write RowResult data to CSV, JSON, or Excel files.

Supports streaming large result sets by operating on pre-fetched
``RowResult`` lists.  For direct category-to-file export, use the
convenience method on ``CommenceSession`` or the CLI.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pycommence.models import FieldInfo, RowResult

log = logging.getLogger(__name__)


class ExportService:
    """Export ``RowResult`` data to CSV, JSON, or Excel files.

    Example::

        from pycommence import CommenceSession

        with CommenceSession() as db:
            rows = db.read("Contact", max_rows=5000)
            db.export_service.to_csv(rows, "contacts.csv")
    """

    def to_csv(
        self,
        rows: list[RowResult],
        path: str | Path,
        *,
        columns: list[str] | None = None,
        encoding: str = "utf-8-sig",
    ) -> int:
        """Write rows to a CSV file.

        Args:
            rows: Row data to export.
            path: Output file path (will be created/overwritten).
            columns: Specific column names to include. ``None`` → all
                columns present in the first row.
            encoding: File encoding. Defaults to ``utf-8-sig`` (BOM) for
                Excel compatibility.

        Returns:
            The number of rows written.

        Example::

            svc.to_csv(rows, "contacts.csv")
            svc.to_csv(rows, "partial.csv", columns=["Name", "Email"])
        """
        if not rows:
            log.warning("to_csv: no rows to export")
            return 0

        path = Path(path)
        fieldnames = columns or list(rows[0].columns.keys())

        with path.open("w", newline="", encoding=encoding) as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row.to_dict())

        log.info("Exported %d rows to %s (CSV)", len(rows), path)
        return len(rows)

    def to_json(
        self,
        rows: list[RowResult],
        path: str | Path,
        *,
        columns: list[str] | None = None,
        indent: int = 2,
        typed: bool = False,
        fields: list[FieldInfo] | None = None,
    ) -> int:
        """Write rows to a JSON file as an array of objects.

        Args:
            rows: Row data to export.
            path: Output file path.
            columns: Specific column names to include. ``None`` → all.
            indent: JSON indentation level.
            typed: If ``True``, coerce values to native Python types
                using ``RowResult.to_typed_dict()``. Requires ``fields``.
            fields: Field metadata for type coercion. Required when
                ``typed=True``.

        Returns:
            The number of rows written.

        Example::

            svc.to_json(rows, "contacts.json")
            svc.to_json(rows, "typed.json", typed=True, fields=schema_fields)
        """
        if not rows:
            log.warning("to_json: no rows to export")
            return 0

        path = Path(path)
        data: list[dict[str, Any]] = []
        for row in rows:
            if typed and fields:
                d = row.to_typed_dict(fields)
            else:
                d = row.to_dict()
            if columns:
                d = {k: v for k, v in d.items() if k in columns}
            data.append(d)

        path.write_text(
            json.dumps(data, indent=indent, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        log.info("Exported %d rows to %s (JSON)", len(rows), path)
        return len(rows)

    def to_excel(
        self,
        rows: list[RowResult],
        path: str | Path,
        *,
        columns: list[str] | None = None,
        sheet_name: str = "Sheet1",
    ) -> int:
        """Write rows to an Excel ``.xlsx`` file.

        Requires the ``openpyxl`` package::

            pip install openpyxl

        Args:
            rows: Row data to export.
            path: Output file path (should end in ``.xlsx``).
            columns: Specific column names to include. ``None`` → all.
            sheet_name: Worksheet name.

        Returns:
            The number of rows written.

        Raises:
            ImportError: If ``openpyxl`` is not installed.

        Example::

            svc.to_excel(rows, "contacts.xlsx")
        """
        try:
            from openpyxl import Workbook
        except ImportError:
            raise ImportError(
                "Excel export requires 'openpyxl'.  Install with:\n"
                "  pip install openpyxl"
            )

        if not rows:
            log.warning("to_excel: no rows to export")
            return 0

        path = Path(path)
        fieldnames = columns or list(rows[0].columns.keys())

        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name

        # Header row
        for col_idx, name in enumerate(fieldnames, 1):
            ws.cell(row=1, column=col_idx, value=name)

        # Data rows
        for row_idx, row in enumerate(rows, 2):
            d = row.to_dict()
            for col_idx, name in enumerate(fieldnames, 1):
                ws.cell(row=row_idx, column=col_idx, value=d.get(name, ""))

        wb.save(str(path))
        log.info("Exported %d rows to %s (Excel)", len(rows), path)
        return len(rows)


def detect_format(path: str | Path) -> str:
    """Detect export format from a file extension.

    Args:
        path: File path to inspect.

    Returns:
        Format string: ``"csv"``, ``"json"``, or ``"excel"``.

    Raises:
        ValueError: If the extension is not recognised.
    """
    suffix = Path(path).suffix.lower()
    mapping = {
        ".csv": "csv",
        ".json": "json",
        ".xlsx": "excel",
        ".xls": "excel",
    }
    fmt = mapping.get(suffix)
    if fmt is None:
        raise ValueError(
            f"Cannot detect format from extension '{suffix}'. "
            f"Supported: {', '.join(mapping.keys())}"
        )
    return fmt

