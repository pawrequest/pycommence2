"""Tests for bulk operations — upsert, copy_category."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from pycommence2.models import RowResult


# ---------------------------------------------------------------------------
# WriterService.upsert_rows
# ---------------------------------------------------------------------------


class TestUpsertRows:
    """Unit tests for WriterService.upsert_rows."""

    def _make_writer(self):
        from pycommence2.services.writer import WriterService

        db = MagicMock()
        writer = WriterService(db)
        return writer

    def _make_reader(self, existing_rows: list[RowResult] | None = None):
        reader = MagicMock()
        reader.read_rows.return_value = existing_rows or []
        return reader

    def test_upsert_adds_new_row(self):
        writer = self._make_writer()
        reader = self._make_reader(existing_rows=[])
        writer.add_row = MagicMock(return_value='new-id')
        writer.edit_row_by_id = MagicMock()

        result = writer.upsert_rows(
            'Contact',
            'Name',
            [{'Name': 'Alice', 'Email': 'alice@example.com'}],
            reader=reader,
        )

        assert result['added'] == 1
        assert result['updated'] == 0
        assert result['unchanged'] == 0
        writer.add_row.assert_called_once()
        writer.edit_row_by_id.assert_not_called()

    def test_upsert_updates_existing_row(self):
        existing = [RowResult(columns={'Name': 'Alice'}, row_id='r1')]
        writer = self._make_writer()
        reader = self._make_reader(existing_rows=existing)
        writer.add_row = MagicMock()
        writer.edit_row_by_id = MagicMock()

        result = writer.upsert_rows(
            'Contact',
            'Name',
            [{'Name': 'Alice', 'Email': 'alice@new.com'}],
            reader=reader,
        )

        assert result['added'] == 0
        assert result['updated'] == 1
        writer.edit_row_by_id.assert_called_once_with(
            'Contact',
            'r1',
            {'Email': 'alice@new.com'},
        )
        writer.add_row.assert_not_called()

    def test_upsert_mixed_add_and_update(self):
        writer = self._make_writer()
        writer.add_row = MagicMock(return_value='new-id')
        writer.edit_row_by_id = MagicMock()

        # First call (Alice) returns existing, second (Bob) returns empty
        reader = MagicMock()
        reader.read_rows.side_effect = [
            [RowResult(columns={'Name': 'Alice'}, row_id='r1')],
            [],
        ]

        result = writer.upsert_rows(
            'Contact',
            'Name',
            [
                {'Name': 'Alice', 'Email': 'alice@new.com'},
                {'Name': 'Bob', 'Email': 'bob@example.com'},
            ],
            reader=reader,
        )

        assert result['added'] == 1
        assert result['updated'] == 1

    def test_upsert_empty_rows(self):
        writer = self._make_writer()
        reader = self._make_reader()

        result = writer.upsert_rows('Contact', 'Name', [], reader=reader)

        assert result == {'added': 0, 'updated': 0, 'unchanged': 0}

    def test_upsert_skips_empty_pk(self):
        writer = self._make_writer()
        reader = self._make_reader()
        writer.add_row = MagicMock()

        result = writer.upsert_rows(
            'Contact',
            'Name',
            [{'Email': 'no-name@example.com'}],  # No "Name" field
            reader=reader,
        )

        assert result == {'added': 0, 'updated': 0, 'unchanged': 0}
        writer.add_row.assert_not_called()


# ---------------------------------------------------------------------------
# Migration: copy_category
# ---------------------------------------------------------------------------


class TestCopyCategory:
    """Unit tests for migration.copy_category."""

    def test_copy_with_field_map(self):
        from pycommence2.services.migration import copy_category

        reader = MagicMock()
        reader.read_rows.return_value = [
            RowResult(columns={'FullName': 'Alice', 'E-Mail': 'a@b.com'}),
            RowResult(columns={'FullName': 'Bob', 'E-Mail': 'b@c.com'}),
        ]
        writer = MagicMock()
        writer.add_rows.return_value = 2

        count = copy_category(
            reader,
            writer,
            'OldContacts',
            'Contact',
            field_map={'FullName': 'Name', 'E-Mail': 'Email'},
        )

        assert count == 2
        writer.add_rows.assert_called_once()
        rows_written = writer.add_rows.call_args[0][1]
        assert rows_written[0] == {'Name': 'Alice', 'Email': 'a@b.com'}
        assert rows_written[1] == {'Name': 'Bob', 'Email': 'b@c.com'}

    def test_copy_no_field_map(self):
        from pycommence2.services.migration import copy_category

        reader = MagicMock()
        reader.read_rows.return_value = [
            RowResult(columns={'Name': 'Alice', 'Email': 'a@b.com'}),
        ]
        writer = MagicMock()
        writer.add_rows.return_value = 1

        count = copy_category(reader, writer, 'Source', 'Target')

        assert count == 1
        rows_written = writer.add_rows.call_args[0][1]
        assert rows_written[0] == {'Name': 'Alice', 'Email': 'a@b.com'}

    def test_copy_empty_source(self):
        from pycommence2.services.migration import copy_category

        reader = MagicMock()
        reader.read_rows.return_value = []
        writer = MagicMock()

        count = copy_category(reader, writer, 'Empty', 'Target')

        assert count == 0
        writer.add_rows.assert_not_called()


# ---------------------------------------------------------------------------
# Session-level shortcuts
# ---------------------------------------------------------------------------


class TestSessionUpsert:
    """Test session.upsert() delegates correctly."""

    def test_upsert_delegates(self):
        from pycommence2.session import CommenceSession

        with patch('pycommence2.session.CommenceDB') as MockDB:
            mock_db = MagicMock()
            MockDB.return_value = mock_db

            session = CommenceSession.__new__(CommenceSession)
            session._db = mock_db
            session._writer = MagicMock()
            session._reader = MagicMock()
            session._writer.upsert_rows.return_value = {
                'added': 1,
                'updated': 0,
                'unchanged': 0,
            }

            result = session.upsert('Contact', 'Name', [{'Name': 'Test'}])

            assert result['added'] == 1
            session._writer.upsert_rows.assert_called_once()
