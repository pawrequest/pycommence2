"""AsyncCommenceSession — async-friendly wrapper around CommenceSession.

Dispatches every COM call to a dedicated STA thread, making the full
pycommence2 API safe to use from ``asyncio`` code (FastAPI, NiceGUI,
MCP servers, etc.).

Usage::

    async with AsyncCommenceSession() as db:
        print(await db.db_name())
        rows = await db.read("Contact", columns=["Name", "Email"], max_rows=10)
        results = await db.query("Contact", columns=["Name"], limit=20,
                                  filters=[("Name", "Contains", "Smith")])
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pycommence2._thread_dispatch import ThreadDispatcher
from pycommence2.models import RowResult

log = logging.getLogger(__name__)


class AsyncCommenceSession:
    """Async facade over :class:`~pycommence2.session.CommenceSession`.

    All methods ``await`` the result of the corresponding synchronous call
    executed on a dedicated COM thread.

    Example::

        async with AsyncCommenceSession() as db:
            categories = await db.list_categories()
            rows = await db.read("Contact", max_rows=10)
    """

    def __init__(self) -> None:
        self._dispatcher = ThreadDispatcher()

    # -- async context manager -----------------------------------------------

    async def __aenter__(self) -> AsyncCommenceSession:
        self._dispatcher.start()
        if self._dispatcher.startup_error:
            raise self._dispatcher.startup_error
        return self

    async def __aexit__(self, *exc: object) -> None:
        self._dispatcher.stop()

    # -- lifecycle helpers ---------------------------------------------------

    def start(self) -> None:
        """Start the COM worker thread synchronously (non-context-manager usage)."""
        self._dispatcher.start()

    def stop(self) -> None:
        """Stop the COM worker thread."""
        self._dispatcher.stop()

    # -- low-level escape hatch ----------------------------------------------

    async def run(self, fn: Any, *args: Any) -> Any:
        """Execute *fn(session, \\*args)* on the COM thread and ``await`` the result.

        Use this for advanced operations or direct sub-service access::

            fields = await db.run(lambda s: s.schema.get_fields("Contact"))

        Args:
            fn: Callable receiving the sync ``CommenceSession`` as first arg.
            *args: Extra positional arguments forwarded to *fn*.

        Returns:
            Whatever *fn* returns.
        """
        return await self._dispatcher.run(fn, *args)

    # -- DB metadata ---------------------------------------------------------

    async def db_name(self) -> str:
        """The name of the currently open Commence database."""
        return await self._dispatcher.run(lambda s: s.db_name)

    async def db_path(self) -> str:
        """The filesystem path to the currently open Commence database."""
        return await self._dispatcher.run(lambda s: s.db_path)

    async def db_version(self) -> str:
        """The Commence application version string."""
        return await self._dispatcher.run(lambda s: s.db_version)

    async def db_shared(self) -> bool:
        """Whether the database is in shared (workgroup) mode."""
        return await self._dispatcher.run(lambda s: s.db_shared)

    # -- schema shortcuts ----------------------------------------------------

    async def list_categories(self) -> list[str]:
        """List all category names in the database."""
        return await self._dispatcher.run(lambda s: s.schema.list_categories())

    async def get_fields(self, category: str) -> list[Any]:
        """Return field definitions for a category.

        Returns:
            List of :class:`~pycommence2.models.FieldInfo` objects.
        """
        return await self._dispatcher.run(
            lambda s, c: s.schema.get_fields(c),
            category,
        )

    async def get_connections(self, category: str) -> list[Any]:
        """Return connection definitions for a category.

        Returns:
            List of :class:`~pycommence2.models.ConnectionInfo` objects.
        """
        return await self._dispatcher.run(
            lambda s, c: s.schema.get_connection_names(c),
            category,
        )

    async def get_row_count(self, category: str) -> int:
        """Return the number of rows in a category."""
        return await self._dispatcher.run(
            lambda s, c: s.schema.get_row_count(c),
            category,
        )

    # -- READ shortcuts ------------------------------------------------------

    async def read(
        self,
        category: str,
        *,
        columns: list[str] | None = None,
        filters: list[str] | None = None,
        logic: str | None = None,
        sort: str | None = None,
        max_rows: int = 500,
        canonical: bool = True,
    ) -> list[RowResult]:
        """Read rows from a category with optional filtering/sorting.

        All parameters mirror :meth:`CommenceSession.read`.
        """
        return await self._dispatcher.run(
            lambda s: s.read(
                category,
                columns=columns,
                filters=filters,
                logic=logic,
                sort=sort,
                max_rows=max_rows,
                canonical=canonical,
            ),
        )

    async def read_by_id(
        self,
        category: str,
        row_id: str,
        *,
        columns: list[str] | None = None,
        canonical: bool = True,
    ) -> RowResult:
        """Read a single row by its unique ID."""
        return await self._dispatcher.run(
            lambda s: s.read_by_id(
                category,
                row_id,
                columns=columns,
                canonical=canonical,
            ),
        )

    async def query(
        self,
        category: str,
        *,
        columns: list[str] | None = None,
        filters: list[tuple[str, str, str]] | None = None,
        sort: str | None = None,
        limit: int = 500,
        canonical: bool = True,
    ) -> list[RowResult]:
        """Build and execute a query in one call.

        This is a convenience wrapper that constructs a ``QueryBuilder``
        on the COM thread and immediately executes it.

        Args:
            category: Commence category name.
            columns: Field names to return.
            filters: List of ``(field, qualifier, value)`` tuples.
            sort: Field name to sort by.
            limit: Maximum rows.
            canonical: Locale-independent formatting.
        """

        def _run(s: Any) -> list[RowResult]:
            qb = s.query(category)
            if columns:
                qb = qb.columns(*columns)
            if filters:
                for field, qualifier, value in filters:
                    qb = qb.where(field, qualifier, value)
            if sort:
                qb = qb.sort(sort)
            qb = qb.limit(limit)
            if canonical:
                qb = qb.canonical()
            return qb.execute()

        return await self._dispatcher.run(_run)

    async def count(
        self,
        category: str,
        *,
        filters: list[tuple[str, str, str]] | None = None,
    ) -> int:
        """Count rows in a category, optionally filtered.

        Args:
            category: Commence category name.
            filters: List of ``(field, qualifier, value)`` tuples.
        """

        def _run(s: Any) -> int:
            qb = s.query(category)
            if filters:
                for field, qualifier, value in filters:
                    qb = qb.where(field, qualifier, value)
            return qb.count()

        return await self._dispatcher.run(_run)

    # -- CREATE shortcut -----------------------------------------------------

    async def add(self, category: str, fields: dict[str, str]) -> str | None:
        """Add a single row to a category.

        Returns:
            The new row's ID, or ``None``.
        """
        return await self._dispatcher.run(
            lambda s: s.add(category, fields),
        )

    async def add_many(self, category: str, rows: list[dict[str, str]]) -> int:
        """Add multiple rows to a category.

        Returns:
            The number of rows added.
        """
        return await self._dispatcher.run(
            lambda s: s.add_many(category, rows),
        )

    # -- UPDATE shortcut -----------------------------------------------------

    async def edit(
        self,
        row_id: str,
        category: str,
        fields: dict[str, str],
    ) -> None:
        """Edit a row by its unique ID."""
        await self._dispatcher.run(
            lambda s: s.edit(row_id, category, fields),
        )

    async def edit_where(
        self,
        category: str,
        fields: dict[str, str],
        *,
        filters: list[str] | None = None,
        logic: str | None = None,
        max_rows: int = 100,
    ) -> int:
        """Edit rows matching filters.

        Returns:
            The number of rows edited.
        """
        return await self._dispatcher.run(
            lambda s: s.edit_where(
                category,
                fields,
                filters=filters,
                logic=logic,
                max_rows=max_rows,
            ),
        )

    # -- DELETE shortcut -----------------------------------------------------

    async def delete(self, row_id: str, category: str) -> None:
        """Delete a row by its unique ID."""
        await self._dispatcher.run(
            lambda s: s.delete(row_id, category),
        )

    async def delete_where(
        self,
        category: str,
        *,
        filters: list[str] | None = None,
        logic: str | None = None,
        max_rows: int = 100,
    ) -> int:
        """Delete rows matching filters.

        Returns:
            The number of rows deleted.
        """
        return await self._dispatcher.run(
            lambda s: s.delete_where(
                category,
                filters=filters,
                logic=logic,
                max_rows=max_rows,
            ),
        )

    # -- CONNECTION shortcuts ------------------------------------------------

    async def assign_connection(
        self,
        from_category: str,
        from_item: str,
        connection_name: str,
        to_category: str,
        to_item: str,
    ) -> None:
        """Create a connection between two items."""
        await self._dispatcher.run(
            lambda s: s.assign_connection(
                from_category,
                from_item,
                connection_name,
                to_category,
                to_item,
            ),
        )

    async def unassign_connection(
        self,
        from_category: str,
        from_item: str,
        connection_name: str,
        to_category: str,
        to_item: str,
    ) -> None:
        """Remove a connection between two items."""
        await self._dispatcher.run(
            lambda s: s.unassign_connection(
                from_category,
                from_item,
                connection_name,
                to_category,
                to_item,
            ),
        )

    # -- EXPORT shortcuts ----------------------------------------------------

    async def export(
        self,
        category: str,
        path: str | Path,
        *,
        format: str | None = None,
        columns: list[str] | None = None,
        filters: list[str] | None = None,
        logic: str | None = None,
        max_rows: int = 50_000,
        canonical: bool = True,
    ) -> int:
        """Export a category to a file (CSV, JSON, or Excel).

        Returns:
            The number of rows exported.
        """
        return await self._dispatcher.run(
            lambda s: s.export(
                category,
                path,
                format=format,
                columns=columns,
                filters=filters,
                logic=logic,
                max_rows=max_rows,
                canonical=canonical,
            ),
        )

    async def backup(
        self,
        output_dir: str | Path,
        *,
        categories: list[str] | None = None,
        max_rows_per_category: int = 50_000,
        canonical: bool = True,
    ) -> dict[str, object]:
        """Export categories to a backup directory with schema sidecar.

        Returns:
            Summary dict.
        """
        return await self._dispatcher.run(
            lambda s: s.backup(
                output_dir,
                categories=categories,
                max_rows_per_category=max_rows_per_category,
                canonical=canonical,
            ),
        )

    async def import_csv(
        self,
        category: str,
        path: str | Path,
        *,
        field_map: dict[str, str] | None = None,
        max_rows: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, object]:
        """Import rows from a CSV file.

        Returns:
            Summary dict.
        """
        return await self._dispatcher.run(
            lambda s: s.import_csv(
                category,
                path,
                field_map=field_map,
                max_rows=max_rows,
                dry_run=dry_run,
            ),
        )

    async def import_json(
        self,
        category: str,
        path: str | Path,
        *,
        field_map: dict[str, str] | None = None,
        max_rows: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, object]:
        """Import rows from a JSON file.

        Returns:
            Summary dict.
        """
        return await self._dispatcher.run(
            lambda s: s.import_json(
                category,
                path,
                field_map=field_map,
                max_rows=max_rows,
                dry_run=dry_run,
            ),
        )

    # -- DDE shortcuts -------------------------------------------------------

    async def dde_get_field(
        self,
        category: str,
        item_name: str,
        field_name: str,
    ) -> str:
        """Read a single field value from an item via DDE."""
        return await self._dispatcher.run(
            lambda s: s.dde.get_field(category, item_name, field_name),
        )

    async def dde_show_item(self, category: str, item_name: str) -> None:
        """Open the detail form for an item in Commence."""
        await self._dispatcher.run(
            lambda s: s.dde.show_item(category, item_name),
        )

    async def dde_fire_trigger(self, trigger_name: str) -> None:
        """Fire a named Commence agent/trigger."""
        await self._dispatcher.run(
            lambda s: s.dde.fire_trigger(trigger_name),
        )

    # -- BULK shortcuts ------------------------------------------------------

    async def upsert(
        self,
        category: str,
        pk_field: str,
        rows: list[dict[str, str]],
    ) -> dict[str, int]:
        """Add-or-update rows based on primary-key match.

        Returns:
            Summary dict with keys ``added``, ``updated``, ``unchanged``.
        """
        return await self._dispatcher.run(
            lambda s: s.upsert(category, pk_field, rows),
        )

    async def copy_category(
        self,
        from_category: str,
        to_category: str,
        field_map: dict[str, str] | None = None,
        *,
        max_rows: int = 50_000,
    ) -> int:
        """Copy rows from one category to another with optional field mapping.

        Returns:
            The number of rows copied.
        """
        return await self._dispatcher.run(
            lambda s: s.copy_category(
                from_category,
                to_category,
                field_map=field_map,
                max_rows=max_rows,
            ),
        )

    # -- WATCH shortcut ------------------------------------------------------

    async def watch(
        self,
        category: str,
        *,
        columns: list[str] | None = None,
        filters: list[str] | None = None,
        interval: float = 5.0,
        max_rows: int = 500,
    ):
        """Async generator that yields WatchEvent objects when rows change.

        Polls the category at *interval* seconds and diffs against the
        previous snapshot.

        Args:
            category: Commence category name.
            columns: Specific field names. ``None`` → all fields.
            filters: Optional DDE-style filter strings.
            interval: Seconds between polls.
            max_rows: Maximum rows to track.

        Yields:
            :class:`~pycommence2.models.WatchEvent` instances.

        Example::

            async for event in db.watch("Hire", interval=5):
                print(event.event_type, event.row["Name"])
        """
        import asyncio
        import hashlib

        prev_snapshot: dict[str, str] = {}  # row_id -> field hash
        prev_rows: dict[str, Any] = {}  # row_id -> RowResult

        while True:
            rows = await self.read(
                category,
                columns=columns,
                filters=filters,
                max_rows=max_rows,
                canonical=True,
            )
            current_snapshot: dict[str, str] = {}
            current_rows: dict[str, Any] = {}

            for row in rows:
                rid = row.row_id or ''
                if not rid:
                    continue
                field_hash = hashlib.md5(str(sorted(row.columns.items())).encode()).hexdigest()
                current_snapshot[rid] = field_hash
                current_rows[rid] = row

            from pycommence2.models import WatchEvent

            # Detect added
            for rid in current_snapshot:
                if rid not in prev_snapshot:
                    yield WatchEvent(event_type='added', row=current_rows[rid])

            # Detect changed
            for rid in current_snapshot:
                if rid in prev_snapshot and current_snapshot[rid] != prev_snapshot[rid]:
                    yield WatchEvent(event_type='changed', row=current_rows[rid])

            # Detect removed
            for rid in prev_snapshot:
                if rid not in current_snapshot:
                    yield WatchEvent(event_type='removed', row=prev_rows[rid])

            prev_snapshot = current_snapshot
            prev_rows = current_rows
            await asyncio.sleep(interval)

    # -- repr ----------------------------------------------------------------

    def __repr__(self) -> str:
        status = 'connected' if self._dispatcher.connected else 'disconnected'
        return f'<AsyncCommenceSession {status}>'
