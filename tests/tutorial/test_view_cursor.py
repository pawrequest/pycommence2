"""Tests for view cursor support – CMC_CURSOR_VIEW mode."""

from __future__ import annotations

import pytest

from pycommence2 import CommenceSession, RowResult


class TestQueryView:
    """Test that query_view() opens a view cursor and returns data."""

    def test_query_view_returns_results(self, session: CommenceSession) -> None:
        """Open a known Tutorial view and read rows.

        The Tutorial DB should have views — we pick the first available
        Contact view.
        """
        views = session.schema.get_view_names('Contact')
        if not views:
            pytest.skip('No Contact views available in Tutorial DB')

        view_name = views[0]
        rows = session.query_view(view_name).limit(5).execute()
        rows=tuple(rows)
        assert isinstance(rows, tuple)
        for row in rows:
            assert isinstance(row, RowResult)

    def test_query_view_count(self, session: CommenceSession) -> None:
        """Count on a view cursor should return a non-negative integer."""
        views = session.schema.get_view_names('Contact')
        if not views:
            pytest.skip('No Contact views available in Tutorial DB')

        view_name = views[0]
        count = session.query_view(view_name).count()
        assert isinstance(count, int)
        assert count >= 0

    def test_query_view_with_extra_filter(self, session: CommenceSession) -> None:
        """Layer an additional filter on top of a view cursor."""
        views = session.schema.get_view_names('Contact')
        if not views:
            pytest.skip('No Contact views available in Tutorial DB')

        view_name = views[0]
        all_count = session.query_view(view_name).count()

        # Add a restrictive filter — should return ≤ all_count
        filtered = session.query_view(view_name).where('firstName', 'Equal To', 'ZZZNONEXISTENT999').count()
        assert filtered <= all_count


class TestCanonicalMode:
    """Test that canonical mode returns locale-independent data."""

    def test_canonical_flag_passes_through(self, session: CommenceSession) -> None:
        """Read a row with canonical=True and verify we get data back."""
        rows = session.query('Contact').columns('contactKey', 'firstName').canonical(True).limit(1).execute()
        assert len(rows) == 1
        assert rows[0]['contactKey']

    def test_session_read_canonical(self, session: CommenceSession) -> None:
        rows = session.read('Contact', columns=['contactKey'], max_rows=1, canonical=True)
        assert len(rows) == 1

    def test_session_read_by_id_canonical(self, session: CommenceSession) -> None:
        rows = session.read('Contact', columns=['contactKey'], max_rows=1)
        row_id = rows[0].row_id
        assert row_id is not None
        result = session.read_by_id('Contact', row_id, canonical=True)
        assert result['contactKey']
