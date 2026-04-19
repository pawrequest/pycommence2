"""Tests for reading data – ReaderService, session.read(), session.read_by_id()."""

from __future__ import annotations

from pycommence import CommenceSession, RowResult
from tests.sample_data import CONTACT_FIELD_NAMES, CONTACT_ITEM_NAMES

CATEGORY = 'Contact'


# ── Basic reads ─────────────────────────────────────────────────────────────


class TestReadAll:
    def test_read_returns_all_contacts(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, max_rows=100)
        assert len(rows) == len(CONTACT_ITEM_NAMES)

    def test_rows_are_row_results(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, max_rows=5)
        assert all(isinstance(r, RowResult) for r in rows)

    def test_row_has_id(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, max_rows=1)
        assert rows[0].row_id is not None
        assert len(rows[0].row_id) > 0


class TestReadWithColumns:
    def test_specific_columns(self, session: CommenceSession) -> None:
        cols = ['contactKey', 'firstName', 'lastName']
        rows = session.read(CATEGORY, columns=cols, max_rows=5)
        assert len(rows) > 0
        for row in rows:
            assert set(row.columns.keys()) == set(cols)

    def test_single_column(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, columns=['contactKey'], max_rows=100)
        names = [r['contactKey'] for r in rows]
        assert sorted(names) == sorted(CONTACT_ITEM_NAMES)


class TestReadWithLimit:
    def test_limit_respected(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, max_rows=3)
        assert len(rows) == 3

    def test_limit_larger_than_total(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, max_rows=9999)
        assert len(rows) == len(CONTACT_ITEM_NAMES)


# ── Known data verification ─────────────────────────────────────────────────


class TestKnownData:
    """Verify specific values we know from the Tutorial DB."""

    def test_gates_bill_exists(self, session: CommenceSession) -> None:
        rows = session.read(
            CATEGORY, columns=['contactKey', 'firstName', 'lastName', 'Title'], max_rows=100
        )
        gates = [r for r in rows if r['contactKey'] == 'Gates.Bill']
        assert len(gates) == 1
        assert gates[0]['firstName'] == 'Bill'
        assert gates[0]['lastName'] == 'Gates'
        assert gates[0]['Title'] == 'Founder of Microsoft'

    def test_gates_email(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, columns=['contactKey', 'emailBusiness'], max_rows=100)
        gates = [r for r in rows if r['contactKey'] == 'Gates.Bill']
        assert gates[0]['emailBusiness'] == 'bill.gates@gatesfoundation.com'

    def test_gates_bus_city(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, columns=['contactKey', 'busCity'], max_rows=100)
        gates = [r for r in rows if r['contactKey'] == 'Gates.Bill']
        assert gates[0]['busCity'] == 'Los Angeles'

    def test_all_item_names_present(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, columns=['contactKey'], max_rows=100)
        names = {r['contactKey'] for r in rows}
        expected = set(CONTACT_ITEM_NAMES)
        assert names == expected


# ── Read by ID ──────────────────────────────────────────────────────────────


class TestReadById:
    def test_read_by_id_returns_row(self, session: CommenceSession) -> None:
        # First get an ID
        rows = session.read(CATEGORY, columns=['contactKey'], max_rows=1)
        row_id = rows[0].row_id
        assert row_id is not None

        # Now read by that ID
        result = session.read_by_id(CATEGORY, row_id, columns=['contactKey'])
        assert isinstance(result, RowResult)
        assert result['contactKey'] == rows[0]['contactKey']

    def test_read_by_id_all_columns(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, columns=['contactKey'], max_rows=1)
        row_id = rows[0].row_id

        result = session.read_by_id(CATEGORY, row_id)
        # Should have many columns (all fields)
        assert len(result.columns) >= len(CONTACT_FIELD_NAMES)


# ── RowResult access ────────────────────────────────────────────────────────


class TestRowResultAccess:
    def test_getitem(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, columns=['contactKey'], max_rows=1)
        row = rows[0]
        # __getitem__ should work
        _ = row['contactKey']

    def test_get_with_default(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, columns=['contactKey'], max_rows=1)
        row = rows[0]
        assert row.get('nonexistent_field', 'fallback') == 'fallback'

    def test_get_existing(self, session: CommenceSession) -> None:
        rows = session.read(CATEGORY, columns=['contactKey'], max_rows=1)
        row = rows[0]
        val = row.get('contactKey', '')
        assert val != ''
