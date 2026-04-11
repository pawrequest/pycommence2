"""Import service — load data from CSV or JSON files into Commence categories.

Reads rows from external files and feeds them to ``CommenceSession.add_many()``
for insertion.  Supports field mapping and dry-run mode.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pycommence.session import CommenceSession

log = logging.getLogger(__name__)


class ImportService:
    """Import data from CSV or JSON files into Commence categories.

    Example::

        from pycommence import CommenceSession

        with CommenceSession() as db:
            result = db.import_service.from_csv("Contact", "contacts.csv")
            print(f"Imported {result['rows_imported']} rows")
    """

    def __init__(self, session: 'CommenceSession') -> None:
        self._session = session

    def from_csv(
        self,
        category: str,
        path: str | Path,
        *,
        field_map: dict[str, str] | None = None,
        encoding: str = 'utf-8-sig',
        max_rows: int | None = None,
        batch_size: int = 50,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Import rows from a CSV file into a Commence category.

        Args:
            category: Target Commence category.
            path: Path to the CSV file.
            field_map: Optional mapping of ``csv_column → commence_field``.
                If ``None``, CSV headers are used as field names directly.
            encoding: File encoding.
            max_rows: Maximum rows to import. ``None`` → all rows.
            batch_size: Number of rows per ``add_many()`` call.
            dry_run: If ``True``, parse and validate but don't write.

        Returns:
            A summary dict with keys: ``rows_parsed``, ``rows_imported``,
            ``errors``, ``dry_run``.

        Example::

            result = svc.from_csv("Contact", "contacts.csv")
            result = svc.from_csv(
                "Contact", "import.csv",
                field_map={"full_name": "Name", "email_addr": "Email"},
            )
        """
        path = Path(path)
        rows: list[dict[str, str]] = []

        with path.open('r', encoding=encoding) as fh:
            reader = csv.DictReader(fh)
            for i, csv_row in enumerate(reader):
                if max_rows is not None and i >= max_rows:
                    break
                if field_map:
                    mapped = {field_map[k]: v for k, v in csv_row.items() if k in field_map}
                else:
                    mapped = {k: v for k, v in csv_row.items() if k is not None}
                rows.append(mapped)

        return self._do_import(category, rows, batch_size=batch_size, dry_run=dry_run)

    def from_json(
        self,
        category: str,
        path: str | Path,
        *,
        field_map: dict[str, str] | None = None,
        max_rows: int | None = None,
        batch_size: int = 50,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Import rows from a JSON file into a Commence category.

        The JSON file must contain an array of objects (each object is
        a row with ``field_name: value`` entries).

        Args:
            category: Target Commence category.
            path: Path to the JSON file.
            field_map: Optional mapping of ``json_key → commence_field``.
            max_rows: Maximum rows to import. ``None`` → all.
            batch_size: Number of rows per ``add_many()`` call.
            dry_run: If ``True``, parse and validate but don't write.

        Returns:
            A summary dict with keys: ``rows_parsed``, ``rows_imported``,
            ``errors``, ``dry_run``.

        Example::

            result = svc.from_json("Contact", "contacts.json")
        """
        path = Path(path)
        raw = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw, list):
            raise ValueError(f'Expected a JSON array, got {type(raw).__name__}')

        rows: list[dict[str, str]] = []
        limit = max_rows if max_rows is not None else len(raw)
        for item in raw[:limit]:
            if not isinstance(item, dict):
                continue
            if field_map:
                mapped = {field_map[k]: str(v) for k, v in item.items() if k in field_map}
            else:
                mapped = {k: str(v) for k, v in item.items()}
            rows.append(mapped)

        return self._do_import(category, rows, batch_size=batch_size, dry_run=dry_run)

    def _do_import(
        self,
        category: str,
        rows: list[dict[str, str]],
        *,
        batch_size: int = 50,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Internal: add rows to Commence in batches.

        Args:
            category: Target category.
            rows: Parsed row dicts.
            batch_size: Rows per commit batch.
            dry_run: Skip actual writes if True.

        Returns:
            Summary dict.
        """
        total_parsed = len(rows)
        if dry_run:
            log.info(
                "Dry run: parsed %d rows for '%s' (no data written)",
                total_parsed,
                category,
            )
            return {
                'rows_parsed': total_parsed,
                'rows_imported': 0,
                'errors': [],
                'dry_run': True,
            }

        total_imported = 0
        errors: list[str] = []

        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            try:
                count = self._session.add_many(category, batch)
                total_imported += count
                log.debug(
                    "Imported batch %d–%d (%d rows) into '%s'",
                    i,
                    i + len(batch) - 1,
                    count,
                    category,
                )
            except Exception as exc:
                msg = f'Batch {i}–{i + len(batch) - 1} failed: {exc}'
                log.error(msg)
                errors.append(msg)

        log.info(
            "Import complete: %d/%d rows into '%s' (%d errors)",
            total_imported,
            total_parsed,
            category,
            len(errors),
        )
        return {
            'rows_parsed': total_parsed,
            'rows_imported': total_imported,
            'errors': errors,
            'dry_run': False,
        }
