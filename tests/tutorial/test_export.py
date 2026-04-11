"""Integration tests for export — runs against a live Commence database.

Tests read data from the Tutorial DB and export to temp files.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


from pycommence import CommenceSession


CATEGORY = 'Contact'


class TestExportIntegration:
    def test_export_csv(self, session: CommenceSession, tmp_path: Path) -> None:
        out = tmp_path / 'contacts.csv'
        count = session.export(CATEGORY, out, max_rows=10)
        assert count > 0
        assert out.exists()
        rows = list(csv.DictReader(out.open(encoding='utf-8-sig')))
        assert len(rows) == count

    def test_export_json(self, session: CommenceSession, tmp_path: Path) -> None:
        out = tmp_path / 'contacts.json'
        count = session.export(CATEGORY, out, max_rows=10)
        assert count > 0
        data = json.loads(out.read_text(encoding='utf-8'))
        assert len(data) == count
        assert 'contactKey' in data[0]

    def test_export_with_columns(self, session: CommenceSession, tmp_path: Path) -> None:
        out = tmp_path / 'partial.csv'
        count = session.export(
            CATEGORY,
            out,
            columns=['contactKey', 'firstName'],
            max_rows=5,
        )
        assert count > 0
        rows = list(csv.DictReader(out.open(encoding='utf-8-sig')))
        assert set(rows[0].keys()) == {'contactKey', 'firstName'}


class TestBackupIntegration:
    def test_backup_single_category(self, session: CommenceSession, tmp_path: Path) -> None:
        out_dir = tmp_path / 'backup'
        stats = session.backup(
            out_dir,
            categories=[CATEGORY],
            max_rows_per_category=10,
        )
        assert stats['categories_exported'] == 1
        assert stats['total_rows'] > 0
        # Check files created
        assert (out_dir / '_schema.json').exists()
        assert (out_dir / '_manifest.json').exists()
        # Category data file
        data_files = [f for f in out_dir.iterdir() if not f.name.startswith('_')]
        assert len(data_files) == 1
