"""Tests for PollWatcher and WatchEvent."""

from __future__ import annotations

from unittest.mock import MagicMock


from pycommence.models import RowResult, WatchEvent
from pycommence.services.watch import PollWatcher


# ---------------------------------------------------------------------------
# WatchEvent model
# ---------------------------------------------------------------------------


class TestWatchEvent:
    """Basic WatchEvent dataclass tests."""

    def test_create_event(self):
        row = RowResult(columns={'Name': 'Alice'}, row_id='r1')
        ev = WatchEvent(event_type='added', row=row)
        assert ev.event_type == 'added'
        assert ev.row['Name'] == 'Alice'

    def test_default_row(self):
        ev = WatchEvent(event_type='removed')
        assert ev.row is not None
        assert len(ev.row) == 0


# ---------------------------------------------------------------------------
# PollWatcher._diff
# ---------------------------------------------------------------------------


class TestPollWatcherDiff:
    """Test the static diff logic without actual polling."""

    def test_detect_added_row(self):
        prev_snap: dict[str, str] = {}
        prev_rows: dict[str, RowResult] = {}
        row = RowResult(columns={'Name': 'Alice'}, row_id='r1')
        curr_snap = {'r1': 'hash1'}
        curr_rows = {'r1': row}

        events = PollWatcher._diff(prev_snap, prev_rows, curr_snap, curr_rows)

        assert len(events) == 1
        assert events[0].event_type == 'added'
        assert events[0].row['Name'] == 'Alice'

    def test_detect_changed_row(self):
        row_old = RowResult(columns={'Name': 'Alice', 'Email': 'old@a.com'}, row_id='r1')
        row_new = RowResult(columns={'Name': 'Alice', 'Email': 'new@a.com'}, row_id='r1')

        prev_snap = {'r1': 'hash_old'}
        prev_rows = {'r1': row_old}
        curr_snap = {'r1': 'hash_new'}
        curr_rows = {'r1': row_new}

        events = PollWatcher._diff(prev_snap, prev_rows, curr_snap, curr_rows)

        assert len(events) == 1
        assert events[0].event_type == 'changed'
        assert events[0].row['Email'] == 'new@a.com'

    def test_detect_removed_row(self):
        row = RowResult(columns={'Name': 'Alice'}, row_id='r1')
        prev_snap = {'r1': 'hash1'}
        prev_rows = {'r1': row}
        curr_snap: dict[str, str] = {}
        curr_rows: dict[str, RowResult] = {}

        events = PollWatcher._diff(prev_snap, prev_rows, curr_snap, curr_rows)

        assert len(events) == 1
        assert events[0].event_type == 'removed'
        assert events[0].row['Name'] == 'Alice'

    def test_no_change(self):
        row = RowResult(columns={'Name': 'Alice'}, row_id='r1')
        snap = {'r1': 'hash1'}
        rows = {'r1': row}

        events = PollWatcher._diff(snap, rows, snap, rows)

        assert len(events) == 0

    def test_mixed_events(self):
        row_a = RowResult(columns={'Name': 'Alice'}, row_id='r1')
        row_b = RowResult(columns={'Name': 'Bob'}, row_id='r2')
        row_c = RowResult(columns={'Name': 'Charlie'}, row_id='r3')

        prev_snap = {'r1': 'h1', 'r2': 'h2'}
        prev_rows = {'r1': row_a, 'r2': row_b}

        # r1 unchanged, r2 removed, r3 added
        curr_snap = {'r1': 'h1', 'r3': 'h3'}
        curr_rows = {'r1': row_a, 'r3': row_c}

        events = PollWatcher._diff(prev_snap, prev_rows, curr_snap, curr_rows)

        types = {ev.event_type for ev in events}
        assert 'added' in types
        assert 'removed' in types
        assert 'changed' not in types
        assert len(events) == 2


# ---------------------------------------------------------------------------
# PollWatcher.poll_once
# ---------------------------------------------------------------------------


class TestPollWatcherPollOnce:
    """Test poll_once method with a mocked reader."""

    def _make_watcher(self, reader_rows: list[RowResult]) -> PollWatcher:
        reader = MagicMock()
        reader.read_rows.return_value = reader_rows
        return PollWatcher(reader, 'Contact', interval=1)

    def test_first_poll_all_added(self):
        rows = [
            RowResult(columns={'Name': 'Alice'}, row_id='r1'),
            RowResult(columns={'Name': 'Bob'}, row_id='r2'),
        ]
        watcher = self._make_watcher(rows)

        events, snap, row_map = watcher.poll_once({}, {})

        assert len(events) == 2
        assert all(e.event_type == 'added' for e in events)
        assert 'r1' in snap
        assert 'r2' in snap

    def test_second_poll_no_change(self):
        rows = [RowResult(columns={'Name': 'Alice'}, row_id='r1')]
        watcher = self._make_watcher(rows)

        # First poll
        events1, snap1, rows1 = watcher.poll_once({}, {})
        assert len(events1) == 1

        # Second poll — same data
        events2, snap2, rows2 = watcher.poll_once(snap1, rows1)
        assert len(events2) == 0

    def test_poll_detects_removal(self):
        row = RowResult(columns={'Name': 'Alice'}, row_id='r1')

        # First poll has one row
        reader = MagicMock()
        reader.read_rows.return_value = [row]
        watcher = PollWatcher(reader, 'Contact', interval=1)

        events1, snap1, rows1 = watcher.poll_once({}, {})
        assert len(events1) == 1

        # Second poll — empty
        reader.read_rows.return_value = []
        events2, snap2, rows2 = watcher.poll_once(snap1, rows1)
        assert len(events2) == 1
        assert events2[0].event_type == 'removed'
