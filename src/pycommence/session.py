"""CommenceSession – the single public entry point for pycommence.

Usage::

    from pycommence import CommenceSession

    with CommenceSession() as session:
        # Schema
        categories = session.schema.list_categories()
        fields = session.schema.get_fields("Contact")

        # Read
        rows = session.read("Contact", columns=["Name", "Email"], max_rows=10)

        # Fluent query
        results = (
            session.query("Contact")
            .where("Name", "Contains", "Smith")
            .sort("Name")
            .limit(20)
            .execute()
        )

        # Create
        new_id = session.add("Contact", {"Name": "Jane Doe", "Email": "jane@example.com"})

        # Update
        session.edit(new_id, "Contact", {"Email": "jane.doe@example.com"})

        # Delete
        session.delete(new_id, "Contact")
"""

from __future__ import annotations

import logging

from pathlib import Path

from pycommence._com.connection import CommenceDB
from pycommence._com.constants import CMC_CURSOR_VIEW
from pycommence.models import RowResult
from pycommence.query import QueryBuilder
from pycommence.services.backup import BackupService
from pycommence.services.connections import ConnectionService
from pycommence.services.dde import DdeService
from pycommence.services.export import ExportService, detect_format
from pycommence.services.import_svc import ImportService
from pycommence.services.reader import ReaderService
from pycommence.services.schema import SchemaService
from pycommence.services.writer import WriterService

log = logging.getLogger(__name__)


class CommenceSession:
    """High-level facade over the Commence COM API.

    Provides schema introspection, CRUD operations, and a fluent
    query builder — all through a single object.

    Example::

        with CommenceSession() as db:
            rows = db.read("Contact", columns=["Name", "Email"], max_rows=10)
            for row in rows:
                print(row["Name"])
    """

    def __init__(self) -> None:
        """Open a COM connection to the running Commence database.

        Raises:
            CommenceNotFoundError: If Commence is not running or no database is open.
        """
        self._db = CommenceDB()
        self._schema = SchemaService(self._db)
        self._reader = ReaderService(self._db)
        self._writer = WriterService(self._db)
        self._connections = ConnectionService(self._db)
        self._dde = DdeService(self._db)
        self._export = ExportService()
        self._backup = BackupService(self)
        self._import = ImportService(self)

    # -- DB metadata ---------------------------------------------------------
    @property
    def db_name(self) -> str:
        """The name of the currently open Commence database."""
        return self._db.name

    @property
    def db_path(self) -> str:
        """The filesystem path to the currently open Commence database."""
        return self._db.path

    @property
    def db_version(self) -> str:
        """The Commence application version string."""
        return self._db.version

    @property
    def db_shared(self) -> bool:
        """Whether the database is in shared (workgroup) mode."""
        return self._db.shared

    # -- sub-service access --------------------------------------------------
    @property
    def schema(self) -> SchemaService:
        """Access schema introspection methods.

        Returns:
            The ``SchemaService`` instance for this session.

        Example::

            categories = db.schema.list_categories()
            fields = db.schema.get_fields("Contact")
        """
        return self._schema

    @property
    def connections(self) -> ConnectionService:
        """Access connection (relationship) operations.

        Returns:
            The ``ConnectionService`` instance for this session.

        Example::

            names = db.connections.get_connected_item_names(
                "Person", "John Smith", "Is Employed by", "Company",
            )
        """
        return self._connections

    @property
    def dde(self) -> DdeService:
        """Access raw DDE execute/request operations.

        Returns:
            The ``DdeService`` instance for this session.

        Example::

            email = db.dde.get_field("Contact", "Jane Doe", "Email")
        """
        return self._dde

    @property
    def export_service(self) -> ExportService:
        """Access the export service for writing data to files.

        Returns:
            The ``ExportService`` instance for this session.

        Example::

            rows = db.read("Contact", max_rows=1000)
            db.export_service.to_csv(rows, "contacts.csv")
        """
        return self._export

    @property
    def backup_service(self) -> BackupService:
        """Access the backup service for full-database snapshots.

        Returns:
            The ``BackupService`` instance for this session.

        Example::

            stats = db.backup_service.backup("./backup")
        """
        return self._backup

    @property
    def import_service(self) -> ImportService:
        """Access the import service for loading data from files.

        Returns:
            The ``ImportService`` instance for this session.

        Example::

            result = db.import_service.from_csv("Contact", "contacts.csv")
        """
        return self._import

    # -- connection shortcuts ------------------------------------------------
    def assign_connection(
        self,
        from_category: str,
        from_item: str,
        connection_name: str,
        to_category: str,
        to_item: str,
    ) -> None:
        """Create a connection between two items.

        Args:
            from_category: Source category name.
            from_item: Source item name (primary key).
            connection_name: Connection name (e.g. ``"Relates to"``).
            to_category: Target category name.
            to_item: Target item name (primary key).

        Raises:
            ConversationError: If the DDE command fails.

        Example::

            db.assign_connection(
                "Person", "John Smith",
                "Is Employed by",
                "Company", "Acme Corp",
            )
        """
        self._connections.assign(
            from_category,
            from_item,
            connection_name,
            to_category,
            to_item,
        )

    def unassign_connection(
        self,
        from_category: str,
        from_item: str,
        connection_name: str,
        to_category: str,
        to_item: str,
    ) -> None:
        """Remove a connection between two items.

        Args:
            from_category: Source category name.
            from_item: Source item name (primary key).
            connection_name: Connection name (e.g. ``"Relates to"``).
            to_category: Target category name.
            to_item: Target item name (primary key).

        Raises:
            ConversationError: If the DDE command fails.

        Example::

            db.unassign_connection(
                "Person", "John Smith",
                "Is Employed by",
                "Company", "Acme Corp",
            )
        """
        self._connections.unassign(
            from_category,
            from_item,
            connection_name,
            to_category,
            to_item,
        )

    # -- READ shortcuts ------------------------------------------------------
    def read(
        self,
        category: str,
        *,
        columns: list[str] | None = None,
        filters: list[str] | None = None,
        logic: str | None = None,
        sort: str | None = None,
        max_rows: int = 500,
        canonical: bool = False,
    ) -> list[RowResult]:
        """Read rows from a category with optional filtering/sorting.

        Args:
            category: Commence category name.
            columns: Specific field names to return. ``None`` → all fields.
            filters: DDE-style filter strings (one per clause, max 4).
            logic: Filter logic string (e.g. ``"And, Or, And"``).
            sort: DDE-style sort string (e.g.
                ``"[ViewSort(Name, Ascending)]"``).
            max_rows: Upper limit on rows returned.
            canonical: If ``True``, return dates as ``yyyymmdd``, numbers
                without locale formatting, times as ``hh:mm``, and
                checkboxes as ``TRUE``/``FALSE``.

        Returns:
            A list of ``RowResult`` objects, each containing a ``columns``
            dict and an optional ``row_id``.

        Example::

            rows = db.read("Contact", columns=["Name", "Email"], max_rows=10)
            for row in rows:
                print(row["Name"], row["Email"])
        """
        return self._reader.read_rows(
            category,
            columns=columns,
            filters=filters,
            logic=logic,
            sort=sort,
            max_rows=max_rows,
            canonical=canonical,
        )

    def read_by_id(
        self,
        category: str,
        row_id: str,
        *,
        columns: list[str] | None = None,
        canonical: bool = False,
    ) -> RowResult:
        """Read a single row by its unique ID.

        Args:
            category: Commence category name.
            row_id: The unique row identifier (obtained from a previous
                read or add operation).
            columns: Specific field names. ``None`` → all fields.
            canonical: If ``True``, use locale-independent formatting.

        Returns:
            A single ``RowResult``.

        Raises:
            RowsetError: If no row matches the given ID.

        Example::

            row = db.read_by_id("Contact", row_id)
            print(row["Email"])
        """
        return self._reader.read_by_id(
            category,
            row_id,
            columns=columns,
            canonical=canonical,
        )

    def query(self, category: str) -> QueryBuilder:
        """Return a fluent QueryBuilder for the given category.

        Args:
            category: Commence category name to query.

        Returns:
            A new ``QueryBuilder`` instance. Chain methods like
            ``.where()``, ``.sort()``, ``.limit()``, then call
            ``.execute()`` to fetch results.

        Example::

            results = (
                db.query("Contact")
                .columns("Name", "Email")
                .where("Name", "Contains", "Smith")
                .limit(20)
                .execute()
            )
        """
        return QueryBuilder(category, self._reader)

    def query_view(self, view_name: str) -> QueryBuilder:
        """Return a fluent QueryBuilder backed by a named view.

        The view's built-in filter, sort, and column set are inherited.
        Additional filters can be layered on top via the builder.

        Args:
            view_name: Name of an existing Commence view.

        Returns:
            A new ``QueryBuilder`` in view-cursor mode.

        Example::

            results = (
                db.query_view("Active Contacts")
                .where("City", "Equal To", "Boston")
                .limit(50)
                .execute()
            )
        """
        return QueryBuilder(view_name, self._reader, mode=CMC_CURSOR_VIEW)

    # -- CREATE shortcut -----------------------------------------------------
    def add(self, category: str, fields: dict[str, str]) -> str | None:
        """Add a single row to a category.

        Args:
            category: Target Commence category.
            fields: Mapping of ``field_name → value`` (all values as strings).

        Returns:
            The new row's ID if obtainable via ``CommitGetCursor``,

            or ``None`` if the ID cannot be determined.

        Example::

            new_id = db.add("Contact", {"Name": "Jane Doe", "Email": "jane@example.com"})
        """
        return self._writer.add_row(category, fields)

    def add_many(self, category: str, rows: list[dict[str, str]]) -> int:
        """Add multiple rows to a category.

        Args:
            category: Target Commence category.
            rows: List of field-value dicts, one per row.

        Returns:
            The number of rows added.

        Example::

            count = db.add_many("Contact", [
                {"Name": "Alice", "Email": "alice@example.com"},
                {"Name": "Bob", "Email": "bob@example.com"},
            ])
        """
        return self._writer.add_rows(category, rows)

    # -- UPDATE shortcut -----------------------------------------------------
    def edit(
        self,
        row_id: str,
        category: str,
        fields: dict[str, str],
    ) -> None:
        """Edit a row by its unique ID.

        Args:
            row_id: The unique row identifier.
            category: Commence category name.
            fields: Mapping of ``field_name → new_value``.

        Raises:
            RowsetError: If no row matches the given ID.

        Example::

            db.edit(row_id, "Contact", {"Email": "new@example.com"})
        """
        self._writer.edit_row_by_id(category, row_id, fields)

    def edit_where(
        self,
        category: str,
        fields: dict[str, str],
        *,
        filters: list[str] | None = None,
        logic: str | None = None,
        max_rows: int = 100,
    ) -> int:
        """Edit rows matching filters.

        Args:
            category: Commence category name.
            fields: Mapping of ``field_name → new_value`` applied to all
                matching rows.
            filters: DDE-style filter strings (max 4).
            logic: Filter logic string (e.g. ``"And, Or, And"``).
            max_rows: Safety cap on how many rows can be edited.

        Returns:
            The number of rows edited.

        Example::

            count = db.edit_where(
                "Contact",
                {"Status": "Inactive"},
                filters=['[ViewFilter(1, F, , "City", "Equal To", "Boston", False)]'],
            )
        """
        return self._writer.edit_rows(
            category,
            fields,
            filters=filters,
            logic=logic,
            max_rows=max_rows,
        )

    # -- DELETE shortcut -----------------------------------------------------
    def delete(self, row_id: str, category: str) -> None:
        """Delete a row by its unique ID.

        Args:
            row_id: The unique row identifier.
            category: Commence category name.

        Raises:
            RowsetError: If no row matches the given ID.

        Example::

            db.delete(row_id, "Contact")
        """
        self._writer.delete_row_by_id(category, row_id)

    def delete_where(
        self,
        category: str,
        *,
        filters: list[str] | None = None,
        logic: str | None = None,
        max_rows: int = 100,
    ) -> int:
        """Delete rows matching filters.

        Args:
            category: Commence category name.
            filters: DDE-style filter strings (max 4).
            logic: Filter logic string (e.g. ``"And, Or, And"``).
            max_rows: Safety cap on how many rows can be deleted.

        Returns:
            The number of rows deleted.

        Example::

            count = db.delete_where(
                "Contact",
                filters=['[ViewFilter(1, F, , "Status", "Equal To", "Archived", False)]'],
                max_rows=50,
            )
        """
        return self._writer.delete_rows(
            category,
            filters=filters,
            logic=logic,
            max_rows=max_rows,
        )

    # -- EXPORT shortcuts ----------------------------------------------------
    def export(
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

        Reads rows from *category* and writes them to *path*.  The format
        is auto-detected from the file extension unless *format* is given.

        Args:
            category: Commence category name.
            path: Output file path (e.g. ``"contacts.csv"``).
            format: Override format — ``"csv"``, ``"json"``, or ``"excel"``.
                Auto-detected from extension if ``None``.
            columns: Specific field names. ``None`` → all fields.
            filters: Optional DDE-style filter strings.
            logic: Filter logic string.
            max_rows: Maximum rows to export.
            canonical: If ``True``, use locale-independent formatting.

        Returns:
            The number of rows exported.

        Example::

            db.export("Hire", "hires.csv", max_rows=5000)
            db.export("Contact", "out.json", columns=["Name", "Email"])
            db.export("Account", "data.xlsx", format="excel")
        """
        fmt = format or detect_format(path)
        rows = self.read(
            category,
            columns=columns,
            filters=filters,
            logic=logic,
            max_rows=max_rows,
            canonical=canonical,
        )
        if fmt == 'csv':
            return self._export.to_csv(rows, path, columns=columns)
        elif fmt == 'json':
            return self._export.to_json(rows, path, columns=columns)
        elif fmt == 'excel':
            return self._export.to_excel(rows, path, columns=columns)
        else:
            raise ValueError(f'Unknown export format: {fmt!r}')

    def backup(
        self,
        output_dir: str | Path,
        *,
        categories: list[str] | None = None,
        max_rows_per_category: int = 50_000,
        canonical: bool = True,
    ) -> dict[str, object]:
        """Export categories to a backup directory with schema sidecar.

        Creates a directory of JSON files (one per category) plus a
        ``_schema.json`` sidecar with field/connection definitions.

        Args:
            output_dir: Target directory path.
            categories: Category names to export. ``None`` → all.
            max_rows_per_category: Row limit per category.
            canonical: If ``True``, use locale-independent formatting.

        Returns:
            A summary dict with ``categories_exported``, ``total_rows``,
            ``files``, ``timestamp``, etc.

        Example::

            stats = db.backup("./backup_2026-04-11")
            stats = db.backup("./partial", categories=["Contact", "Hire"])
        """
        return self._backup.backup(
            output_dir,
            categories=categories,
            max_rows_per_category=max_rows_per_category,
            canonical=canonical,
        )

    def import_csv(
        self,
        category: str,
        path: str | Path,
        *,
        field_map: dict[str, str] | None = None,
        max_rows: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, object]:
        """Import rows from a CSV file into a category.

        Args:
            category: Target Commence category.
            path: Path to the CSV file.
            field_map: Optional ``csv_column → commence_field`` mapping.
            max_rows: Maximum rows to import.
            dry_run: Parse and validate without writing.

        Returns:
            Summary dict with ``rows_parsed``, ``rows_imported``,
            ``errors``, ``dry_run``.

        Example::

            result = db.import_csv("Contact", "contacts.csv")
        """
        return self._import.from_csv(
            category,
            path,
            field_map=field_map,
            max_rows=max_rows,
            dry_run=dry_run,
        )

    def import_json(
        self,
        category: str,
        path: str | Path,
        *,
        field_map: dict[str, str] | None = None,
        max_rows: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, object]:
        """Import rows from a JSON file into a category.

        Args:
            category: Target Commence category.
            path: Path to the JSON file (array of objects).
            field_map: Optional ``json_key → commence_field`` mapping.
            max_rows: Maximum rows to import.
            dry_run: Parse and validate without writing.

        Returns:
            Summary dict with ``rows_parsed``, ``rows_imported``,
            ``errors``, ``dry_run``.

        Example::

            result = db.import_json("Contact", "contacts.json")
        """
        return self._import.from_json(
            category,
            path,
            field_map=field_map,
            max_rows=max_rows,
            dry_run=dry_run,
        )

    # -- BULK shortcuts -------------------------------------------------------
    def upsert(
        self,
        category: str,
        pk_field: str,
        rows: list[dict[str, str]],
    ) -> dict[str, int]:
        """Add-or-update rows based on primary-key match.

        For each row, looks up existing items by *pk_field*. If a match
        is found the row is updated; otherwise a new row is added.

        Args:
            category: Target Commence category.
            pk_field: Field name used as the primary key for matching.
            rows: List of field-value dicts (must include *pk_field*).

        Returns:
            Summary dict with keys ``added``, ``updated``, ``unchanged``.

        Example::

            result = db.upsert("Contact", "Name", [
                {"Name": "Alice", "Email": "alice@new.com"},
                {"Name": "NewPerson", "Email": "new@example.com"},
            ])
        """
        return self._writer.upsert_rows(
            category,
            pk_field,
            rows,
            reader=self._reader,
        )

    def copy_category(
        self,
        from_category: str,
        to_category: str,
        field_map: dict[str, str] | None = None,
        *,
        max_rows: int = 50_000,
    ) -> int:
        """Copy rows from one category to another with optional field mapping.

        Args:
            from_category: Source category name.
            to_category: Target category name.
            field_map: Optional ``source_field → target_field`` mapping.
            max_rows: Maximum rows to copy.

        Returns:
            The number of rows copied.

        Example::

            copied = db.copy_category(
                "OldContacts", "Contact",
                field_map={"FullName": "Name"},
            )
        """
        from pycommence.services.migration import copy_category

        return copy_category(
            self._reader,
            self._writer,
            from_category,
            to_category,
            field_map=field_map,
            max_rows=max_rows,
        )

    # -- WATCH shortcut ------------------------------------------------------
    def watch(
        self,
        category: str,
        *,
        columns: list[str] | None = None,
        filters: list[str] | None = None,
        interval: float = 5.0,
        max_rows: int = 500,
    ):
        """Blocking generator that yields events when rows change.

        Polls *category* at *interval* seconds and diffs against the
        previous snapshot.

        Args:
            category: Commence category name to watch.
            columns: Specific field names. ``None`` → all fields.
            filters: Optional DDE-style filter strings.
            interval: Seconds between polls (default 5).
            max_rows: Maximum rows to track.

        Yields:
            :class:`~pycommence.models.WatchEvent` instances.

        Example::

            for event in db.watch("Hire", interval=5):
                print(event.event_type, event.row["Name"])
        """
        from pycommence.services.watch import PollWatcher

        watcher = PollWatcher(
            self._reader,
            category,
            columns=columns,
            filters=filters,
            interval=interval,
            max_rows=max_rows,
        )
        yield from watcher

    # -- DDE convenience shortcuts -------------------------------------------
    def mark_item(self, category: str, item_name: str) -> None:
        """Mark (highlight) an item in a Commence view via DDE.

        Args:
            category: Commence category name.
            item_name: Item name (primary key) to mark.

        Example::

            db.mark_item("Contact", "Jane Doe")
        """
        self._dde.view_mark_item(category, item_name)

    def get_preference(self, pref_name: str) -> str:
        """Return a Commence preference value via DDE.

        Args:
            pref_name: Preference key (e.g. ``"Me"``).

        Returns:
            The preference value as a string.

        Example::

            me = db.get_preference("Me")
        """
        return self._dde.get_preference(pref_name)

    # -- context manager -----------------------------------------------------
    def close(self) -> None:
        """Release the COM connection.

        Safe to call multiple times. Also called automatically when
        exiting a ``with`` block.
        """
        self._db.close()

    def __enter__(self) -> 'CommenceSession':
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f'<CommenceSession db={self.db_name!r}>'
