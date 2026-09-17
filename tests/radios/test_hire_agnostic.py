"""DB-agnostic integration tests against the 'Hire' category.

These tests discover schema at runtime — no hardcoded field names, row counts,
or item values.  They focus on:

* Large-dataset reads (13k+ rows, 120+ wide columns, 30 000-char text fields)
  that may hit COM data-size limits.
* Records with "sketchy" primary-key values (leading spaces, ``/``, ``{``, etc.).
* Paginated / batched reads to verify no data truncation or off-by-one errors.
* Round-trip consistency between DDE and cursor APIs.

Commence must be open with a database that contains a 'Hire' category.
"""

from __future__ import annotations

import logging

import pytest

from pycommence2 import (
    CategoryInfo,
    CommenceSession,
    ConnectionInfo,
    FieldInfo,
    FieldType,
    RowResult,
)

log = logging.getLogger(__name__)

CATEGORY = 'Hire'


# ── Fixtures (session-scoped for speed) ─────────────────────────────────────


@pytest.fixture(scope='module')
def schema_fields(session: CommenceSession) -> list[FieldInfo]:
    """All field definitions for the Hire category (discovered at runtime)."""
    return session.schema.get_fields(CATEGORY)


@pytest.fixture(scope='module')
def field_names(session: CommenceSession) -> list[str]:
    return session.schema.get_field_names(CATEGORY)


@pytest.fixture(scope='module')
def pk_field(schema_fields: list[FieldInfo]) -> str:
    """Return the NAME-type (primary key) field for the category."""
    for f in schema_fields:
        if f.field_type == FieldType.NAME:
            return f.name
    pytest.fail('No NAME-type field found – cannot determine primary key')


@pytest.fixture(scope='module')
def total_rows(session: CommenceSession) -> int:
    return session.schema.get_row_count(CATEGORY)


@pytest.fixture(scope='module')
def large_text_fields(schema_fields: list[FieldInfo]) -> list[str]:
    """Field names whose max_chars ≥ 10 000 (prone to data-size blowouts)."""
    return [f.name for f in schema_fields if f.max_chars >= 10_000]


# ── Schema discovery ────────────────────────────────────────────────────────


class TestSchemaDiscovery:
    """Verify we can introspect the Hire category from any Commence DB that has one."""

    def test_hire_category_listed(self, session: CommenceSession) -> None:
        cats = session.schema.list_categories()
        assert CATEGORY in cats

    def test_category_definition(self, session: CommenceSession) -> None:
        info = session.schema.get_category_definition(CATEGORY)
        assert isinstance(info, CategoryInfo)
        assert info.name == CATEGORY
        assert info.max_items > 0

    def test_field_count_matches_names(
        self,
        session: CommenceSession,
        field_names: list[str],
    ) -> None:
        count = session.schema.get_field_count(CATEGORY)
        assert count == len(field_names)

    def test_fields_have_valid_types(self, schema_fields: list[FieldInfo]) -> None:
        for f in schema_fields:
            assert isinstance(f.field_type, FieldType), f'Bad type on {f.name}'

    def test_has_name_field(self, pk_field: str) -> None:
        """Every category needs a NAME-type primary key."""
        assert pk_field  # non-empty

    def test_connections_discoverable(self, session: CommenceSession) -> None:
        conns = session.schema.get_connection_names(CATEGORY)
        assert isinstance(conns, list)
        for c in conns:
            assert isinstance(c, ConnectionInfo)
            assert c.name
            assert c.to_category

    def test_connection_count_matches(self, session: CommenceSession) -> None:
        count = session.schema.get_connection_count(CATEGORY)
        conns = session.schema.get_connection_names(CATEGORY)
        assert count == len(conns)

    def test_row_count_positive(self, total_rows: int) -> None:
        assert total_rows > 0


# ── Large-data reads (cursor API) ──────────────────────────────────────────


class TestLargeDataReads:
    """Stress-test the cursor/rowset pipeline against a wide, deep category."""

    def test_read_small_batch_all_columns(self, session: CommenceSession) -> None:
        """Read 5 rows with ALL columns – forces the rowset to materialise
        every field including 30 000-char text fields."""
        rows = session.read(CATEGORY, max_rows=5)
        assert len(rows) > 0
        for row in rows:
            assert isinstance(row, RowResult)
            assert row.row_id is not None

    def test_read_small_batch_column_count(
        self,
        session: CommenceSession,
        field_names: list[str],
    ) -> None:
        """Returned columns should be ≥ discovered field count
        (cursor may add connection columns)."""
        rows = session.read(CATEGORY, max_rows=1)
        assert len(rows[0].columns) >= len(field_names)

    def test_read_large_batch_pk_only(
        self,
        session: CommenceSession,
        pk_field: str,
        total_rows: int,
    ) -> None:
        """Read ALL rows but only the PK column — lightweight but tests paging
        over the entire dataset."""
        print(f'\nBatch Size: {total_rows}')
        rows = session.read(CATEGORY, columns=[pk_field], max_rows=total_rows)
        assert len(rows) == total_rows
        # Every row should have a non-None PK value
        for r in rows:
            assert pk_field in r.columns

    def test_read_medium_batch_all_columns(
        self,
        session: CommenceSession,
    ) -> None:
        """Read 200 rows with all columns — a realistic page size that can
        blow up if total cell data exceeds COM buffer limits."""
        print('\nBatch Size: 200')
        rows = session.read(CATEGORY, max_rows=200)
        assert len(rows) == 200

    def test_read_only_large_text_fields(
        self,
        session: CommenceSession,
        pk_field: str,
        large_text_fields: list[str],
    ) -> None:
        """Explicitly select only the high-capacity text fields — maximises
        per-row payload and is the most likely to trigger data-size errors."""
        if not large_text_fields:
            pytest.skip('No large text fields discovered')
        cols = [pk_field] + large_text_fields
        rows = session.read(CATEGORY, columns=cols, max_rows=50)
        assert len(rows) > 0
        for row in rows:
            for col in cols:
                assert col in row.columns, f'Missing column {col!r}'

    def test_read_full_dataset_pk_count(
        self,
        session: CommenceSession,
        pk_field: str,
        total_rows: int,
    ) -> None:
        """Read ALL rows (PK only) via QueryBuilder – ensures pagination works
        end-to-end without losing rows."""
        rows = session.query(CATEGORY).columns(pk_field).limit(total_rows).execute()
        assert len(rows) == total_rows

    def test_canonical_mode_large_batch(self, session: CommenceSession) -> None:
        """Canonical mode should not crash on a big batch."""
        rows = session.query(CATEGORY).canonical(True).limit(50).execute()
        assert len(rows) == 50
        for row in rows:
            assert isinstance(row, RowResult)


# ── Sketchy record names ───────────────────────────────────────────────────


class TestSketchyNames:
    """Records whose Name (PK) starts with a space, or contains ``/``, ``{``,
    ``-``, ``\\``, or other characters that can break quoting in DDE commands
    and cursor filters."""

    @pytest.fixture(scope='class')
    def all_names(self, session: CommenceSession, pk_field: str) -> list[str]:
        """Fetch every PK value in the category (once per class)."""
        rows = session.read(CATEGORY, columns=[pk_field], max_rows=session.schema.get_row_count(CATEGORY))
        return [r[pk_field] for r in rows]

    @pytest.fixture(scope='class')
    def sketchy_names(self, all_names: list[str]) -> list[str]:
        """Names that have at least one "risky" characteristic."""
        risky = []
        for name in all_names:
            if (
                name != name.strip()
                or '/' in name
                or '{' in name
                or '\\' in name
                or '"' in name
                or name.startswith('-')
                or name.startswith(' ')
            ):
                risky.append(name)
        if not risky:
            pytest.skip('No sketchy names found in this dataset')
        return risky

    def test_sketchy_names_exist(self, sketchy_names: list[str]) -> None:
        """Sanity: the fixture actually found some."""
        log.info('Found %d sketchy names (showing first 5): %s', len(sketchy_names), sketchy_names[:5])
        assert len(sketchy_names) > 0

    def test_read_by_id_for_sketchy_rows(
        self,
        session: CommenceSession,
        pk_field: str,
        sketchy_names: list[str],
    ) -> None:
        """Get the row_id via a full read, then read_by_id – should not crash."""
        # Pick up to 10 sketchy names to keep runtime reasonable
        sample = sketchy_names[:10]
        # Get IDs for these rows in one batch
        rows = session.read(CATEGORY, columns=[pk_field], max_rows=len(sample) + 50)
        id_map = {r[pk_field]: r.row_id for r in rows if r[pk_field] in sample}

        for name, row_id in id_map.items():
            assert row_id is not None, f'No row_id for {name!r}'
            result = session.read_by_id(CATEGORY, row_id, columns=[pk_field])
            assert result[pk_field] == name

    def test_query_filter_contains_on_sketchy_rows(
        self,
        session: CommenceSession,
        pk_field: str,
        sketchy_names: list[str],
    ) -> None:
        """Filter with 'Contains' against a substring from a sketchy name."""
        # Pick a name that contains '/' — very common in Hire names like
        # " - 14/09/2006 ref 44"
        slash_names = [n for n in sketchy_names if '/' in n]
        if not slash_names:
            pytest.skip("No names containing '/' found")

        target = slash_names[0]
        # Use a substring that includes the slash
        slash_idx = target.index('/')
        start = max(0, slash_idx - 2)
        substring = target[start : slash_idx + 3]

        rows = session.query(CATEGORY).columns(pk_field).where(pk_field, 'Contains', substring).limit(100).execute()
        matched_names = {r[pk_field] for r in rows}
        assert target in matched_names, f'Expected {target!r} in results for Contains {substring!r}'

    def test_leading_space_names_round_trip(
        self,
        session: CommenceSession,
        pk_field: str,
        sketchy_names: list[str],
    ) -> None:
        """Names that start with a space should survive a read → read_by_id
        round trip without being silently trimmed."""
        space_names = [n for n in sketchy_names if n.startswith(' ')]
        if not space_names:
            pytest.skip('No leading-space names found')

        target = space_names[0]
        rows = session.read(CATEGORY, columns=[pk_field], max_rows=5)
        row = next((r for r in rows if r[pk_field] == target), None)
        if row is None or row.row_id is None:
            pytest.skip(f'Could not find row for {target!r} in first 5 rows')

        result = session.read_by_id(CATEGORY, row.row_id, columns=[pk_field])
        # The value must NOT be trimmed
        assert result[pk_field] == target
        assert result[pk_field].startswith(' ')


# ── DDE vs Cursor consistency ──────────────────────────────────────────────


class TestDdeCursorConsistency:
    """Verify that DDE item-count matches cursor row-count, and that
    DDE field reads agree with cursor reads."""

    def test_item_count_matches_row_count(
        self,
        session: CommenceSession,
        total_rows: int,
    ) -> None:
        dde_count = session.dde.get_item_count(CATEGORY)
        assert dde_count == total_rows

    def test_dde_get_field_matches_cursor(
        self,
        session: CommenceSession,
        pk_field: str,
        field_names: list[str],
    ) -> None:
        """Read one row via cursor, then read the same fields via DDE and compare."""
        # Pick a small non-text field to avoid DDE data-length issues
        small_fields = [f for f in field_names if f != pk_field][:3]
        if not small_fields:
            pytest.skip('Not enough fields')

        cols = [pk_field] + small_fields
        cursor_rows = session.read(CATEGORY, columns=cols, max_rows=1)
        assert cursor_rows
        row = cursor_rows[0]
        item_name = row[pk_field]

        for field in small_fields:
            dde_val = session.dde.get_field(CATEGORY, item_name, field)
            cursor_val = row[field]
            assert dde_val == cursor_val, (
                f"Mismatch on '{field}' for item {item_name!r}: DDE={dde_val!r} vs cursor={cursor_val!r}"
            )


# ── Query builder with runtime schema ──────────────────────────────────────


class TestQueryBuilderAgnostic:
    """Use QueryBuilder features against dynamically discovered fields."""

    def test_sort_by_pk(
        self,
        session: CommenceSession,
        pk_field: str,
    ) -> None:
        """Commence uses Windows locale-aware collation (special chars like
        ``-``, ``?``, ``+`` sort differently from Python).  We verify the sort
        was applied by checking ascending ≠ descending rather than comparing
        against Python's sorted() output."""
        asc = session.query(CATEGORY).columns(pk_field).sort(pk_field, ascending=True).limit(20).execute()
        desc = session.query(CATEGORY).columns(pk_field).sort(pk_field, ascending=False).limit(20).execute()
        asc_names = [r[pk_field] for r in asc]
        desc_names = [r[pk_field] for r in desc]
        # The two orderings must be different (unless ≤20 total rows)
        assert asc_names != desc_names, 'Ascending and descending returned same order'
        assert len(asc_names) == 20

    def test_sort_descending(
        self,
        session: CommenceSession,
        pk_field: str,
    ) -> None:
        """Descending sort should put Z-names first (alphabetically last items)."""
        rows = session.query(CATEGORY).columns(pk_field).sort(pk_field, ascending=False).limit(20).execute()
        names = [r[pk_field] for r in rows]
        # First result should start with a letter from the end of the alphabet
        # (or at least be lexicographically greater than the last)
        first_alpha = names[0][0] if names[0] and names[0][0].isalpha() else ''
        if first_alpha:
            assert first_alpha.upper() >= 'M', f'Descending sort starts with {names[0]!r} – expected late-alphabet'

    def test_count_no_filter(
        self,
        session: CommenceSession,
        total_rows: int,
    ) -> None:
        count = session.query(CATEGORY).count()
        assert count == total_rows

    def test_filter_reduces_count(
        self,
        session: CommenceSession,
        pk_field: str,
        total_rows: int,
    ) -> None:
        """A restrictive filter must return fewer rows than the total."""
        count = session.query(CATEGORY).where(pk_field, 'Equal To', 'ZZZNONEXISTENT999').count()
        assert count < total_rows
        assert count == 0  # this name shouldn't exist

    def test_query_with_date_field_filter(
        self,
        session: CommenceSession,
        schema_fields: list[FieldInfo],
        pk_field: str,
    ) -> None:
        """Find a DATE field and filter 'After' a very old date — should return rows."""
        date_fields = [f for f in schema_fields if f.field_type == FieldType.DATE]
        if not date_fields:
            pytest.skip('No DATE fields in this category')

        date_field = date_fields[0].name
        rows = (
            session.query(CATEGORY)
            .columns(pk_field, date_field)
            .where(date_field, 'After', '01/01/2000')
            .limit(10)
            .execute()
        )
        assert len(rows) > 0

    def test_query_checkbox_field(
        self,
        session: CommenceSession,
        schema_fields: list[FieldInfo],
        pk_field: str,
    ) -> None:
        """Filter on a CHECK_BOX field with 'Checked' qualifier.

        Commence checkboxes use the special qualifiers 'Checked' and
        'Not Checked' (not 'Equal To' + 'TRUE').
        """
        cb_fields = [f for f in schema_fields if f.field_type == FieldType.CHECK_BOX]
        if not cb_fields:
            pytest.skip('No CHECK_BOX fields in this category')

        cb_name = cb_fields[0].name
        rows = session.query(CATEGORY).columns(pk_field, cb_name).where(cb_name, 'Checked', '').limit(10).execute()
        # We can't predict the count, but the call must not error
        assert isinstance(rows, list)

    def test_multiple_filters(
        self,
        session: CommenceSession,
        schema_fields: list[FieldInfo],
        pk_field: str,
    ) -> None:
        """Stack two filters together — should not error."""
        date_fields = [f for f in schema_fields if f.field_type == FieldType.DATE]
        cb_fields = [f for f in schema_fields if f.field_type == FieldType.CHECK_BOX]
        if not date_fields or not cb_fields:
            pytest.skip('Need both a DATE and CHECK_BOX field')

        rows = (
            session.query(CATEGORY)
            .columns(pk_field)
            .where(date_fields[0].name, 'After', '01/01/2020')
            .where(cb_fields[0].name, 'Checked', '')
            .limit(10)
            .execute()
        )
        assert isinstance(rows, list)


# ── Data-size edge cases ───────────────────────────────────────────────────


class TestDataSizeEdgeCases:
    """Specifically target scenarios that can overflow COM buffers or DDE
    response limits."""

    def test_single_row_all_columns_no_crash(
        self,
        session: CommenceSession,
    ) -> None:
        """Read a single row with ALL columns — maximises column count."""
        rows = session.read(CATEGORY, max_rows=1)
        assert len(rows) == 1
        # Should have 120+ columns
        assert len(rows[0].columns) >= 100

    def test_batch_of_10_all_columns(self, session: CommenceSession) -> None:
        """10 rows × 120+ columns including large text — ~3.6 MB potential."""
        rows = session.read(CATEGORY, max_rows=10)
        assert len(rows) == 10

    def test_batch_of_50_all_columns(self, session: CommenceSession) -> None:
        """50 rows × 120+ columns — stress test."""
        rows = session.read(CATEGORY, max_rows=50)
        assert len(rows) == 50

    def test_get_row_as_string(self, session: CommenceSession, pk_field: str) -> None:
        """Verify RowResult values are always str (not None from COM)."""
        rows = session.read(CATEGORY, max_rows=5)
        for row in rows:
            for col_name, value in row.columns.items():
                assert isinstance(value, str), f'Column {col_name!r} has non-str value: {type(value)}'

    def test_read_by_id_all_columns(self, session: CommenceSession) -> None:
        """read_by_id with all columns — single-row but maximum width."""
        rows = session.read(CATEGORY, max_rows=1)
        row_id = rows[0].row_id
        assert row_id is not None

        result = session.read_by_id(CATEGORY, row_id)
        assert len(result.columns) >= 100

    def test_paginated_read_no_data_loss(
        self,
        session: CommenceSession,
        pk_field: str,
    ) -> None:
        """Read 500 rows in one shot and verify no duplicates or missing IDs."""
        rows = session.read(CATEGORY, columns=[pk_field], max_rows=500)
        ids = [r.row_id for r in rows]
        # No None IDs
        assert all(rid is not None for rid in ids)
        # No duplicate IDs
        assert len(set(ids)) == len(ids), f'Duplicate row IDs found: {len(ids)} rows but {len(set(ids))} unique'
