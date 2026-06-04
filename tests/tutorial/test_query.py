"""Tests for the fluent QueryBuilder API."""

from __future__ import annotations

import pytest

from pycommence2 import CommenceSession, QueryBuilder, RowResult
from tests.sample_data import CONTACT_ITEM_NAMES

CATEGORY = 'Contact'


class TestQueryBuilderBasic:
    def test_query_returns_builder(self, session: CommenceSession) -> None:
        qb = session.query(CATEGORY)
        assert isinstance(qb, QueryBuilder)

    def test_execute_returns_rows(self, session: CommenceSession) -> None:
        rows = session.query(CATEGORY).limit(5).execute(resolve=True)
        assert isinstance(rows, tuple)
        assert len(rows) <= 5
        assert all(isinstance(r, RowResult) for r in rows)


class TestQueryWithColumns:
    def test_columns_selection(self, session: CommenceSession) -> None:
        rows = (
            session.query(CATEGORY)
            .columns('contactKey', 'firstName', 'lastName')
            .limit(3)
            .execute()
        )
        for row in rows:
            assert set(row.columns.keys()) == {'contactKey', 'firstName', 'lastName'}


class TestQueryWithFilter:
    def test_where_equal_to(self, session: CommenceSession) -> None:
        rows = (
            session.query(CATEGORY)
            .columns('contactKey', 'firstName')
            .where('firstName', 'Equal To', 'Bill')
            .execute()
        )
        assert len(rows) >= 1
        assert all(r['firstName'] == 'Bill' for r in rows)

    def test_where_contains(self, session: CommenceSession) -> None:
        rows = (
            session.query(CATEGORY)
            .columns('contactKey', 'busCity')
            .where('busCity', 'Contains', 'Los')
            .execute()
        )
        assert len(rows) >= 1
        for row in rows:
            assert 'Los' in row['busCity']

    def test_where_no_results(self, session: CommenceSession) -> None:
        rows = (
            session.query(CATEGORY)
            .columns('contactKey')
            .where('firstName', 'Equal To', 'ZZZNONEXISTENT999')
            .execute()
        )
        assert len(rows) == 0

    def test_filter_gates_by_name(self, session: CommenceSession) -> None:
        rows = (
            session.query(CATEGORY)
            .columns('contactKey', 'lastName', 'busCity')
            .where('lastName', 'Equal To', 'Gates')
            .execute()
        )
        assert len(rows) == 1
        assert rows[0]['contactKey'] == 'Gates.Bill'
        assert rows[0]['busCity'] == 'Los Angeles'

    def test_filter_los_angeles_contacts(self, session: CommenceSession) -> None:
        """Gates and Nadella are both in Los Angeles."""
        rows = (
            session.query(CATEGORY)
            .columns('contactKey', 'busCity')
            .where('busCity', 'Equal To', 'Los Angeles')
            .execute()
        )
        names = {r['contactKey'] for r in rows}
        assert 'Gates.Bill' in names
        assert 'Nadella.Satya' in names


class TestQueryWithSort:
    def test_sort_ascending(self, session: CommenceSession) -> None:
        rows = (
            session.query(CATEGORY)
            .columns('contactKey')
            .sort('contactKey', ascending=True)
            .execute()
        )
        names = [r['contactKey'] for r in rows]
        assert names == sorted(names)

    def test_sort_descending(self, session: CommenceSession) -> None:
        rows = (
            session.query(CATEGORY)
            .columns('contactKey')
            .sort('contactKey', ascending=False)
            .execute()
        )
        names = [r['contactKey'] for r in rows]
        assert names == sorted(names, reverse=True)


class TestQueryWithLimit:
    def test_limit(self, session: CommenceSession) -> None:
        rows = session.query(CATEGORY).columns('contactKey').limit(3).execute()
        assert len(rows) == 3

    def test_count(self, session: CommenceSession) -> None:
        count = session.query(CATEGORY).count()
        assert count == len(CONTACT_ITEM_NAMES)


class TestQueryWithIds:
    def test_with_ids_true(self, session: CommenceSession) -> None:
        rows = session.query(CATEGORY).columns('contactKey').with_ids(True).limit(3).execute()
        for row in rows:
            assert row.row_id is not None

    def test_with_ids_false(self, session: CommenceSession) -> None:
        rows = session.query(CATEGORY).columns('contactKey').with_ids(False).limit(3).execute()
        for row in rows:
            assert row.row_id is None


class TestQueryMaxFilters:
    def test_more_than_four_filters_raises(self, session: CommenceSession) -> None:
        qb = session.query(CATEGORY)
        qb.where('firstName', 'Contains', 'a')
        qb.where('lastName', 'Contains', 'b')
        qb.where('busCity', 'Contains', 'c')
        qb.where('busState', 'Contains', 'd')
        with pytest.raises(ValueError, match='maximum of 4'):
            qb.where('Title', 'Contains', 'e')
