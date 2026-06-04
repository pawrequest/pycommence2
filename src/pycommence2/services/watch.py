"""Poll-based watch service — detect row additions, changes, and removals.

Provides both a sync blocking generator and an async generator for
monitoring changes to a Commence category.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import TYPE_CHECKING, Generator

from pycommence2.models import RowResult, WatchEvent

if TYPE_CHECKING:
    from pycommence2.services.reader import ReaderService

log = logging.getLogger(__name__)


class PollWatcher:
    """Periodically reads rows from a category and diffs against the last snapshot.

    Yields :class:`~pycommence2.models.WatchEvent` objects for rows that have
    been added, changed, or removed since the previous poll.

    Usage (sync)::

        watcher = PollWatcher(reader, "Hire", interval=5)
        for event in watcher:
            print(event.event_type, event.row["Name"])

    The watcher tracks rows by their ``row_id`` and detects changes by
    hashing all column values.  It is **not** aware of changes made by
    other processes between polls — it only sees the state at each poll.

    Args:
        reader: ``ReaderService`` to read rows.
        category: Commence category name to watch.
        columns: Specific field names. ``None`` → all fields.
        filters: Optional DDE-style filter strings.
        interval: Seconds between polls (default 5).
        max_rows: Maximum rows to track per poll (default 500).
    """

    def __init__(
        self,
        reader: 'ReaderService',
        category: str,
        *,
        columns: list[str] | None = None,
        filters: list[str] | None = None,
        interval: float = 5.0,
        max_rows: int = 500,
    ) -> None:
        self._reader = reader
        self._category = category
        self._columns = columns
        self._filters = filters
        self._interval = interval
        self._max_rows = max_rows

    def _read_snapshot(self) -> tuple[dict[str, str], dict[str, RowResult]]:
        """Read current rows and return (id→hash, id→RowResult) dicts."""
        rows = self._reader.read_rows(
            self._category,
            columns=self._columns,
            filters=self._filters,
            max_rows=self._max_rows,
            get_ids=True,
            canonical=True,
        )
        snapshot: dict[str, str] = {}
        row_map: dict[str, RowResult] = {}
        for row in rows:
            rid = row.row_id
            if not rid:
                continue
            field_hash = hashlib.md5(str(sorted(row.columns.items())).encode()).hexdigest()
            snapshot[rid] = field_hash
            row_map[rid] = row
        return snapshot, row_map

    @staticmethod
    def _diff(
        prev_snapshot: dict[str, str],
        prev_rows: dict[str, RowResult],
        curr_snapshot: dict[str, str],
        curr_rows: dict[str, RowResult],
    ) -> list[WatchEvent]:
        """Compare two snapshots and return a list of events."""
        events: list[WatchEvent] = []

        for rid in curr_snapshot:
            if rid not in prev_snapshot:
                events.append(WatchEvent(event_type='added', row=curr_rows[rid]))
            elif curr_snapshot[rid] != prev_snapshot[rid]:
                events.append(WatchEvent(event_type='changed', row=curr_rows[rid]))

        for rid in prev_snapshot:
            if rid not in curr_snapshot:
                events.append(WatchEvent(event_type='removed', row=prev_rows[rid]))

        return events

    def __iter__(self) -> Generator[WatchEvent, None, None]:
        """Blocking generator — yields events until interrupted.

        Example::

            for event in PollWatcher(reader, "Hire", interval=5):
                print(event)
        """
        prev_snapshot: dict[str, str] = {}
        prev_rows: dict[str, RowResult] = {}

        while True:
            curr_snapshot, curr_rows = self._read_snapshot()
            events = self._diff(prev_snapshot, prev_rows, curr_snapshot, curr_rows)

            for ev in events:
                yield ev

            prev_snapshot = curr_snapshot
            prev_rows = curr_rows
            time.sleep(self._interval)

    def poll_once(
        self,
        prev_snapshot: dict[str, str],
        prev_rows: dict[str, RowResult],
    ) -> tuple[list[WatchEvent], dict[str, str], dict[str, RowResult]]:
        """Do a single poll and return (events, new_snapshot, new_rows).

        Useful for testing or manual poll loops.
        """
        curr_snapshot, curr_rows = self._read_snapshot()
        events = self._diff(prev_snapshot, prev_rows, curr_snapshot, curr_rows)
        return events, curr_snapshot, curr_rows
