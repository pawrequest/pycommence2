"""Unit tests for ImportService — no Commence connection required.

Tests verify CSV/JSON parsing and field mapping logic. Actual writes
to Commence are mocked since these are unit tests.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pycommence.services.import_svc import ImportService


@pytest.fixture
def mock_session() -> MagicMock:
    """A mock CommenceSession that tracks add_many calls."""
    session = MagicMock()
    session.add_many.return_value = 3  # simulate 3 rows added
    return session


@pytest.fixture
def svc(mock_session: MagicMock) -> ImportService:
    return ImportService(mock_session)


@pytest.fixture
def csv_file(tmp_path: Path) -> Path:
    """Create a sample CSV file."""
    path = tmp_path / "contacts.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["Name", "Email", "City"])
        writer.writeheader()
        writer.writerow({"Name": "Alice", "Email": "alice@example.com", "City": "Boston"})
        writer.writerow({"Name": "Bob", "Email": "bob@example.com", "City": "NYC"})
        writer.writerow({"Name": "Carol", "Email": "carol@example.com", "City": "LA"})
    return path


@pytest.fixture
def json_file(tmp_path: Path) -> Path:
    """Create a sample JSON file."""
    path = tmp_path / "contacts.json"
    data = [
        {"Name": "Alice", "Email": "alice@example.com", "City": "Boston"},
        {"Name": "Bob", "Email": "bob@example.com", "City": "NYC"},
        {"Name": "Carol", "Email": "carol@example.com", "City": "LA"},
    ]
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ── CSV import ──────────────────────────────────────────────────────────────

class TestFromCsv:

    def test_basic_import(
        self, svc: ImportService, csv_file: Path, mock_session: MagicMock,
    ) -> None:
        result = svc.from_csv("Contact", csv_file)
        assert result["rows_parsed"] == 3
        assert result["dry_run"] is False
        mock_session.add_many.assert_called()

    def test_field_mapping(
        self, svc: ImportService, csv_file: Path, mock_session: MagicMock,
    ) -> None:
        result = svc.from_csv(
            "Contact", csv_file,
            field_map={"Name": "contactKey", "Email": "emailBusiness"},
        )
        assert result["rows_parsed"] == 3
        # Check that add_many was called with mapped fields
        call_args = mock_session.add_many.call_args
        batch = call_args[0][1]  # second positional arg: rows
        assert "contactKey" in batch[0]
        assert "emailBusiness" in batch[0]
        assert "City" not in batch[0]  # not in field_map → excluded

    def test_max_rows(
        self, svc: ImportService, csv_file: Path,
    ) -> None:
        result = svc.from_csv("Contact", csv_file, max_rows=1)
        assert result["rows_parsed"] == 1

    def test_dry_run(
        self, svc: ImportService, csv_file: Path, mock_session: MagicMock,
    ) -> None:
        result = svc.from_csv("Contact", csv_file, dry_run=True)
        assert result["rows_parsed"] == 3
        assert result["rows_imported"] == 0
        assert result["dry_run"] is True
        mock_session.add_many.assert_not_called()


# ── JSON import ─────────────────────────────────────────────────────────────

class TestFromJson:

    def test_basic_import(
        self, svc: ImportService, json_file: Path, mock_session: MagicMock,
    ) -> None:
        result = svc.from_json("Contact", json_file)
        assert result["rows_parsed"] == 3
        mock_session.add_many.assert_called()

    def test_field_mapping(
        self, svc: ImportService, json_file: Path, mock_session: MagicMock,
    ) -> None:
        result = svc.from_json(
            "Contact", json_file,
            field_map={"Name": "contactKey"},
        )
        call_args = mock_session.add_many.call_args
        batch = call_args[0][1]
        assert "contactKey" in batch[0]

    def test_max_rows(
        self, svc: ImportService, json_file: Path,
    ) -> None:
        result = svc.from_json("Contact", json_file, max_rows=2)
        assert result["rows_parsed"] == 2

    def test_dry_run(
        self, svc: ImportService, json_file: Path, mock_session: MagicMock,
    ) -> None:
        result = svc.from_json("Contact", json_file, dry_run=True)
        assert result["rows_parsed"] == 3
        assert result["rows_imported"] == 0
        mock_session.add_many.assert_not_called()

    def test_invalid_json_raises(
        self, svc: ImportService, tmp_path: Path,
    ) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text('{"not": "an array"}', encoding="utf-8")
        with pytest.raises(ValueError, match="JSON array"):
            svc.from_json("Contact", bad)

