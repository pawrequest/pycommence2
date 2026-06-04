"""Backup service — export multiple categories with schema metadata sidecar.

Creates a directory of JSON files (one per category) plus a
``_schema.json`` sidecar containing category/field/connection definitions.
Useful for full-database snapshots and data migration.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycommence2.session import CommenceSession

log = logging.getLogger(__name__)


class BackupService:
    """Export categories and schema to a structured backup directory.

    Example::

        from pycommence2 import CommenceSession

        with CommenceSession() as db:
            stats = db.backup("./backup_2026-04-11")
            print(f"Backed up {stats['categories_exported']} categories")
    """

    def __init__(self, session: 'CommenceSession') -> None:
        self._session = session

    def backup(
        self,
        output_dir: str | Path,
        *,
        categories: list[str] | None = None,
        max_rows_per_category: int = 50_000,
        canonical: bool = True,
        include_schema: bool = True,
    ) -> dict[str, object]:
        """Export categories to a backup directory.

        Creates the output directory if it doesn't exist.  Each category
        is exported as a JSON file; a ``_schema.json`` sidecar contains
        field and connection definitions for all exported categories.

        Args:
            output_dir: Target directory path.
            categories: Category names to export. ``None`` → all categories.
            max_rows_per_category: Row limit per category.
            canonical: If ``True``, use locale-independent data formatting.
            include_schema: If ``True``, write ``_schema.json`` sidecar.

        Returns:
            A summary dict with keys: ``db_name``, ``db_path``,
            ``timestamp``, ``categories_exported``, ``total_rows``,
            ``files``.

        Example::

            stats = svc.backup("./my_backup")
            stats = svc.backup("./partial", categories=["Contact", "Hire"])
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        session = self._session
        all_cats = categories or session.schema.list_categories()

        timestamp = datetime.now(tz=timezone.utc).isoformat()
        total_rows = 0
        files: list[str] = []
        schema_data: dict[str, object] = {
            'db_name': session.db_name,
            'db_path': session.db_path,
            'timestamp': timestamp,
            'categories': {},
        }

        for cat_name in all_cats:
            log.info('Backing up category: %s', cat_name)
            try:
                rows = session.read(
                    cat_name,
                    max_rows=max_rows_per_category,
                    canonical=canonical,
                )
            except Exception as exc:
                log.warning("Failed to read category '%s': %s", cat_name, exc)
                continue

            # Write data file
            data_file = output_dir / f'{_safe_filename(cat_name)}.json'
            row_dicts = [r.to_dict() for r in rows]
            data_file.write_text(
                json.dumps(row_dicts, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
            total_rows += len(rows)
            files.append(data_file.name)
            log.info('  → %d rows → %s', len(rows), data_file.name)

            # Collect schema
            if include_schema:
                try:
                    fields = session.schema.get_fields(cat_name)
                    connections = session.schema.get_connection_names(cat_name)
                    schema_data['categories'][cat_name] = {  # type: ignore[index]
                        'row_count': len(rows),
                        'fields': [asdict(f) for f in fields],
                        'connections': [asdict(c) for c in connections],
                    }
                except Exception as exc:
                    log.warning("Failed to get schema for '%s': %s", cat_name, exc)

        # Write schema sidecar
        if include_schema:
            schema_file = output_dir / '_schema.json'
            schema_file.write_text(
                json.dumps(schema_data, indent=2, ensure_ascii=False, default=str),
                encoding='utf-8',
            )
            files.append('_schema.json')
            log.info('Schema sidecar written: %s', schema_file)

        summary = {
            'db_name': session.db_name,
            'db_path': session.db_path,
            'timestamp': timestamp,
            'categories_exported': len(all_cats),
            'total_rows': total_rows,
            'files': files,
        }

        # Write summary manifest
        manifest_file = output_dir / '_manifest.json'
        manifest_file.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )

        log.info(
            'Backup complete: %d categories, %d rows → %s',
            len(all_cats),
            total_rows,
            output_dir,
        )
        return summary


def _safe_filename(name: str) -> str:
    """Convert a category name to a safe filename (no path separators)."""
    return name.replace('/', '_').replace('\\', '_').replace(':', '_').replace(' ', '_')
