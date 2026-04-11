"""Unit tests for ExportService — no Commence connection required.

Tests operate on in-memory RowResult objects and temp files.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from pycommence.models import FieldInfo, FieldType, RowResult
from pycommence.services.export import ExportService, detect_format


@pytest.fixture
def svc() -> ExportService:
    return ExportService()


@pytest.fixture
def sample_rows() -> list[RowResult]:
    return [
        RowResult(columns={"Name": "Alice", "Email": "alice@example.com", "City": "Boston"}),
        RowResult(columns={"Name": "Bob", "Email": "bob@example.com", "City": "NYC"}),
        RowResult(columns={"Name": "Carol", "Email": "carol@example.com", "City": "LA"}),
    ]


# ── CSV ─────────────────────────────────────────────────────────────────────

class TestToCsv:

    def test_writes_csv(self, svc: ExportService, sample_rows: list[RowResult], tmp_path: Path) -> None:
        out = tmp_path / "test.csv"
        count = svc.to_csv(sample_rows, out)
        assert count == 3
        assert out.exists()
        rows = list(csv.DictReader(out.open(encoding="utf-8-sig")))
        assert len(rows) == 3
        assert rows[0]["Name"] == "Alice"
        assert rows[2]["City"] == "LA"

    def test_csv_column_filter(self, svc: ExportService, sample_rows: list[RowResult], tmp_path: Path) -> None:
        out = tmp_path / "partial.csv"
        svc.to_csv(sample_rows, out, columns=["Name", "Email"])
        rows = list(csv.DictReader(out.open(encoding="utf-8-sig")))
        assert set(rows[0].keys()) == {"Name", "Email"}

    def test_csv_empty_rows(self, svc: ExportService, tmp_path: Path) -> None:
        out = tmp_path / "empty.csv"
        count = svc.to_csv([], out)
        assert count == 0


# ── JSON ────────────────────────────────────────────────────────────────────

class TestToJson:

    def test_writes_json(self, svc: ExportService, sample_rows: list[RowResult], tmp_path: Path) -> None:
        out = tmp_path / "test.json"
        count = svc.to_json(sample_rows, out)
        assert count == 3
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 3
        assert data[0]["Name"] == "Alice"

    def test_json_column_filter(self, svc: ExportService, sample_rows: list[RowResult], tmp_path: Path) -> None:
        out = tmp_path / "partial.json"
        svc.to_json(sample_rows, out, columns=["Name"])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert set(data[0].keys()) == {"Name"}

    def test_json_typed(self, svc: ExportService, tmp_path: Path) -> None:
        rows = [
            RowResult(columns={"Name": "Alice", "Count": "42", "Active": "TRUE"}),
        ]
        fields = [
            FieldInfo(name="Name", field_type=FieldType.TEXT),
            FieldInfo(name="Count", field_type=FieldType.NUMBER),
            FieldInfo(name="Active", field_type=FieldType.CHECK_BOX),
        ]
        out = tmp_path / "typed.json"
        svc.to_json(rows, out, typed=True, fields=fields)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data[0]["Count"] == 42
        assert data[0]["Active"] is True

    def test_json_empty_rows(self, svc: ExportService, tmp_path: Path) -> None:
        out = tmp_path / "empty.json"
        count = svc.to_json([], out)
        assert count == 0


# ── detect_format ───────────────────────────────────────────────────────────

class TestDetectFormat:

    def test_csv(self) -> None:
        assert detect_format("data.csv") == "csv"

    def test_json(self) -> None:
        assert detect_format("data.json") == "json"

    def test_xlsx(self) -> None:
        assert detect_format("data.xlsx") == "excel"

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot detect format"):
            detect_format("data.parquet")

