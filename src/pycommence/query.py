"""Fluent QueryBuilder for constructing Commence queries with a Pythonic API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycommence._com.constants import CMC_CURSOR_CATEGORY
from pycommence.models import RelatedColumn, RowResult

if TYPE_CHECKING:
    from pycommence.services.reader import ReaderService


class QueryBuilder:
    """Chainable query builder that constructs filter/sort/column specs
    and delegates execution to a ReaderService.

    Usage::

        results = (
            session.query("Contact")
            .columns("Name", "Email", "Phone")
            .where("Name", "Contains", "Smith")
            .sort("Name", ascending=True)
            .limit(50)
            .execute()
        )
    """

    def __init__(
        self,
        category: str,
        reader: 'ReaderService',
        *,
        mode: int = CMC_CURSOR_CATEGORY,
    ) -> None:
        self._category = category
        self._reader = reader
        self._mode = mode
        self._columns: list[str] | None = None
        self._related_columns: list[RelatedColumn] = []
        self._filters: list[str] = []
        self._filter_counter = 0
        self._logic: str | None = None
        self._sort_pairs: list[tuple[str, str]] = []
        self._max_rows: int = 500
        self._get_ids: bool = True
        self._canonical: bool = False

    # -- column selection ----------------------------------------------------
    def columns(self, *fields: str) -> 'QueryBuilder':
        """Select specific columns to return.

        If not called, all fields in the category are returned.

        Args:
            *fields: One or more field names to include in results.

        Returns:
            This ``QueryBuilder`` (for chaining).

        Example::

            db.query("Contact").columns("Name", "Email", "Phone")
        """
        self._columns = list(fields)
        return self

    # -- filtering -----------------------------------------------------------
    def where(
        self,
        field: str,
        qualifier: str,
        value: str = '',
        case_sensitive: bool = False,
    ) -> 'QueryBuilder':
        """Add a field filter clause (FilterType=F).

        Args:
            field: Field name to filter on.
            qualifier: Comparison operator — e.g. ``"Contains"``,
                ``"Equal To"``, ``"After"``, ``"Checked"``.
            value: Value to compare against. Leave empty for qualifiers
                like ``"Blank"``, ``"Checked"``, or ``"Not Checked"``.
            case_sensitive: Whether comparison is case-sensitive.

        Returns:
            This ``QueryBuilder`` (for chaining).

        Raises:
            ValueError: If more than 4 filter clauses are added
                (Commence hard limit).

        Example::

            db.query("Contact").where("Name", "Contains", "Smith")
            db.query("Hire").where("Closed", "Checked", "")
        """
        self._filter_counter += 1
        if self._filter_counter > 4:
            raise ValueError('Commence supports a maximum of 4 filter clauses')
        cs = 'True' if case_sensitive else 'False'
        clause = (
            f'[ViewFilter({self._filter_counter}, F, , "{field}", "{qualifier}", "{value}", {cs})]'
        )
        self._filters.append(clause)
        return self

    def where_connection(
        self,
        connection_name: str,
        connected_category: str,
        item_name: str,
        *,
        not_flag: bool = False,
    ) -> 'QueryBuilder':
        """Add a 'Connection To Item' filter clause (CTI).

        Filters rows that are (or are not) connected to a specific item.

        Args:
            connection_name: Connection name (e.g. ``"Is Employed by"``).
            connected_category: Category of the connected item.
            item_name: Primary key of the connected item.
            not_flag: If ``True``, negate the filter (items *not*
                connected).

        Returns:
            This ``QueryBuilder`` (for chaining).

        Raises:
            ValueError: If more than 4 filter clauses are added.

        Example::

            db.query("Person").where_connection(
                "Is Employed by", "Company", "Acme Corp",
            )
        """
        self._filter_counter += 1
        if self._filter_counter > 4:
            raise ValueError('Commence supports a maximum of 4 filter clauses')
        nf = 'Not' if not_flag else ''
        clause = (
            f'[ViewFilter({self._filter_counter}, CTI, {nf}, '
            f'"{connection_name}", "{connected_category}", "{item_name}")]'
        )
        self._filters.append(clause)
        return self

    def where_connected_field(
        self,
        connection_name: str,
        connected_category: str,
        field: str,
        qualifier: str,
        value: str = '',
        case_sensitive: bool = False,
        *,
        not_flag: bool = False,
    ) -> 'QueryBuilder':
        """Add a 'Connection To Category Field' filter clause (CTCF).

        Filters rows based on a field value in a connected item.

        Args:
            connection_name: Connection name (e.g. ``"Is Employed by"``).
            connected_category: Category of the connected item.
            field: Field name in the connected category to filter on.
            qualifier: Comparison operator (e.g. ``"Contains"``).
            value: Value to compare against.
            case_sensitive: Whether comparison is case-sensitive.
            not_flag: If ``True``, negate the filter.

        Returns:
            This ``QueryBuilder`` (for chaining).

        Raises:
            ValueError: If more than 4 filter clauses are added.

        Example::

            db.query("Person").where_connected_field(
                "Is Employed by", "Company",
                "State", "Contains", "NJ",
            )
        """
        self._filter_counter += 1
        if self._filter_counter > 4:
            raise ValueError('Commence supports a maximum of 4 filter clauses')
        nf = 'Not' if not_flag else ''
        cs = 'True' if case_sensitive else 'False'
        clause = (
            f'[ViewFilter({self._filter_counter}, CTCF, {nf}, '
            f'"{connection_name}", "{connected_category}", '
            f'"{field}", "{qualifier}", "{value}", {cs})]'
        )
        self._filters.append(clause)
        return self

    def raw_filter(self, filter_string: str) -> 'QueryBuilder':
        """Add a raw DDE-style filter string (escape hatch).

        Use this when the high-level ``where`` methods don't cover your
        use case — for example, shared/local filter qualifiers or
        unusual syntax.

        Args:
            filter_string: A complete ``[ViewFilter(...)]`` string.

        Returns:
            This ``QueryBuilder`` (for chaining).

        Example::

            db.query("Person").raw_filter(
                '[ViewFilter(1, F, , "Name", "Contains", "Smith", False)]'
            )
        """
        self._filter_counter += 1
        self._filters.append(filter_string)
        return self

    def related_column(
        self,
        connection: str,
        category: str,
        field: str,
    ) -> 'QueryBuilder':
        """Include a connected/indirect field in the result set.

        Uses ``ICommenceCursor.SetRelatedColumn`` under the hood.

        Args:
            connection: Connection name (e.g. ``"Relates to"``).
            category: Connected category name (e.g. ``"Account"``).
            field: Field name in the connected category.

        Returns:
            This ``QueryBuilder`` (for chaining).

        Example::

            db.query("Person")
                .columns("Name")
                .related_column("Is Employed by", "Company", "Phone")
        """
        self._related_columns.append(RelatedColumn(connection, category, field))
        return self

    def conjunction(self, logic: str) -> 'QueryBuilder':
        """Set the filter logic for combining multiple filter clauses.

        By default, Commence uses AND between all clauses. Use this to
        mix AND/OR.

        Args:
            logic: Comma-separated logic string, e.g. ``"And, Or, And"``.
                One operator per gap between consecutive clauses.

        Returns:
            This ``QueryBuilder`` (for chaining).

        Example::

            db.query("Contact")
                .where("City", "Equal To", "Boston")
                .where("City", "Equal To", "NYC")
                .conjunction("Or")
        """
        self._logic = logic
        return self

    # -- sorting -------------------------------------------------------------
    def sort(self, field: str, ascending: bool = True) -> 'QueryBuilder':
        """Add a sort field. Call multiple times to add up to 4 sort fields.

        Args:
            field: Field name to sort by.
            ascending: Sort direction. ``True`` (default) for A→Z / old→new.

        Returns:
            This ``QueryBuilder`` (for chaining).

        Example::

            db.query("Contact").sort("LastName").sort("FirstName")
            db.query("Hire").sort("Booked Date", ascending=False)
        """
        direction = 'Ascending' if ascending else 'Descending'
        self._sort_pairs.append((field, direction))
        return self

    # -- limits --------------------------------------------------------------
    def limit(self, n: int) -> 'QueryBuilder':
        """Set the maximum number of rows to return.

        Defaults to 500 if not called.

        Args:
            n: Maximum row count.

        Returns:
            This ``QueryBuilder`` (for chaining).
        """
        self._max_rows = n
        return self

    def with_ids(self, val: bool = True) -> 'QueryBuilder':
        """Control whether each ``RowResult`` includes a ``row_id``.

        Row IDs are required for subsequent ``edit()`` / ``delete()``
        calls. Enabled by default.

        Args:
            val: ``True`` to fetch row IDs (default), ``False`` to skip.

        Returns:
            This ``QueryBuilder`` (for chaining).
        """
        self._get_ids = val
        return self

    def canonical(self, val: bool = True) -> 'QueryBuilder':
        """Enable canonical data format (locale-independent).

        Dates become ``yyyymmdd``, times ``hh:mm`` (24-hr), numbers
        ``123456.78``, and checkboxes ``TRUE``/``FALSE``.

        Args:
            val: ``True`` to enable (default), ``False`` to disable.

        Returns:
            This ``QueryBuilder`` (for chaining).
        """
        self._canonical = val
        return self

    # -- execute -------------------------------------------------------------
    def execute(self) -> list[RowResult]:
        """Run the query and return results.

        Assembles the accumulated columns, filters, sort, and options
        into a single ``ReaderService.read_rows`` call.

        Returns:
            A list of ``RowResult`` objects. Each has a ``.columns``
            dict and an optional ``.row_id``.

        Raises:
            CursorError: If the cursor cannot be created.
            FilterError: If a filter string is malformed.

        Example::

            results = (
                db.query("Contact")
                .columns("Name", "Email")
                .where("Name", "Contains", "Smith")
                .limit(20)
                .execute()
            )
        """
        # Build the [ViewSort(...)] string from accumulated sort pairs
        sort_str: str | None = None
        if self._sort_pairs:
            inner = ', '.join(f'{f}, {d}' for f, d in self._sort_pairs[:4])
            sort_str = f'[ViewSort({inner})]'

        return self._reader.read_rows(
            self._category,
            columns=self._columns,
            related_columns=self._related_columns or None,
            filters=self._filters or None,
            logic=self._logic,
            sort=sort_str,
            max_rows=self._max_rows,
            get_ids=self._get_ids,
            canonical=self._canonical,
            mode=self._mode,
        )

    def count(self) -> int:
        """Return only the count of matching rows (without fetching data).

        Respects accumulated filters and logic.

        Returns:
            The number of rows that match the current filter criteria.

        Example::

            n = db.query("Contact").where("Status", "Equal To", "Active").count()
        """
        return self._reader.count(
            self._category,
            filters=self._filters or None,
            logic=self._logic,
            mode=self._mode,
        )
