"""Tests for CRUD write operations – add, edit, delete.

Each test that creates data cleans up after itself to keep the Tutorial DB pristine.
Tests are ordered: add → edit → delete within classes.
"""

from __future__ import annotations

import uuid


from pycommence import CommenceSession
from tests.sample_data import CONTACT_ITEM_NAMES

CATEGORY = 'Contact'


def _unique_name() -> str:
    """Generate a unique contact key that won't collide with tutorial data."""
    return f'Test.{uuid.uuid4().hex[:8]}'


# ── Add (CREATE) ────────────────────────────────────────────────────────────


class TestAddRow:
    def test_add_single_row(self, session: CommenceSession) -> None:
        name = _unique_name()
        try:
            row_id = session.add(
                CATEGORY,
                {
                    'contactKey': name,
                    'firstName': 'Test',
                    'lastName': 'User',
                },
            )
            # Should get a row_id back
            assert row_id is not None
            assert len(row_id) > 0

            # Verify it was actually added
            rows = (
                session.query(CATEGORY)
                .columns('contactKey', 'firstName', 'lastName')
                .where('contactKey', 'Equal To', name)
                .execute()
            )
            assert len(rows) == 1
            assert rows[0]['firstName'] == 'Test'
            assert rows[0]['lastName'] == 'User'
        finally:
            # Clean up
            self._delete_by_name(session, name)

    def test_add_row_with_email(self, session: CommenceSession) -> None:
        name = _unique_name()
        try:
            session.add(
                CATEGORY,
                {
                    'contactKey': name,
                    'firstName': 'Email',
                    'emailBusiness': 'test@example.com',
                },
            )
            rows = (
                session.query(CATEGORY)
                .columns('contactKey', 'emailBusiness')
                .where('contactKey', 'Equal To', name)
                .execute()
            )
            assert len(rows) == 1
            assert rows[0]['emailBusiness'] == 'test@example.com'
        finally:
            self._delete_by_name(session, name)

    def test_add_many(self, session: CommenceSession) -> None:
        names = [_unique_name() for _ in range(3)]
        try:
            count = session.add_many(
                CATEGORY,
                [
                    {'contactKey': names[0], 'firstName': 'Bulk1'},
                    {'contactKey': names[1], 'firstName': 'Bulk2'},
                    {'contactKey': names[2], 'firstName': 'Bulk3'},
                ],
            )
            assert count == 3

            # Verify all were added
            for n in names:
                rows = (
                    session.query(CATEGORY)
                    .columns('contactKey')
                    .where('contactKey', 'Equal To', n)
                    .execute()
                )
                assert len(rows) == 1
        finally:
            for n in names:
                self._delete_by_name(session, n)

    @staticmethod
    def _delete_by_name(session: CommenceSession, name: str) -> None:
        """Helper: find row by name and delete it."""
        rows = (
            session.query(CATEGORY)
            .columns('contactKey')
            .where('contactKey', 'Equal To', name)
            .execute()
        )
        if rows and rows[0].row_id:
            session.delete(rows[0].row_id, CATEGORY)


# ── Edit (UPDATE) ───────────────────────────────────────────────────────────


class TestEditRow:
    def test_edit_by_id(self, session: CommenceSession) -> None:
        name = _unique_name()
        try:
            row_id = session.add(
                CATEGORY,
                {
                    'contactKey': name,
                    'firstName': 'Before',
                    'lastName': 'Edit',
                },
            )
            assert row_id is not None

            # Edit it
            session.edit(row_id, CATEGORY, {'firstName': 'After'})

            # Verify
            result = session.read_by_id(CATEGORY, row_id, columns=['contactKey', 'firstName'])
            assert result['firstName'] == 'After'
        finally:
            self._cleanup(session, name)

    def test_edit_multiple_fields(self, session: CommenceSession) -> None:
        name = _unique_name()
        try:
            row_id = session.add(
                CATEGORY,
                {
                    'contactKey': name,
                    'firstName': 'Old',
                    'lastName': 'Name',
                    'busCity': 'OldCity',
                },
            )
            assert row_id is not None

            session.edit(
                row_id,
                CATEGORY,
                {
                    'firstName': 'New',
                    'lastName': 'Person',
                    'busCity': 'NewCity',
                },
            )

            result = session.read_by_id(
                CATEGORY,
                row_id,
                columns=['firstName', 'lastName', 'busCity'],
            )
            assert result['firstName'] == 'New'
            assert result['lastName'] == 'Person'
            assert result['busCity'] == 'NewCity'
        finally:
            self._cleanup(session, name)

    @staticmethod
    def _cleanup(session: CommenceSession, name: str) -> None:
        rows = (
            session.query(CATEGORY)
            .columns('contactKey')
            .where('contactKey', 'Equal To', name)
            .execute()
        )
        if rows and rows[0].row_id:
            session.delete(rows[0].row_id, CATEGORY)


# ── Delete (DELETE) ─────────────────────────────────────────────────────────


class TestDeleteRow:
    def test_delete_by_id(self, session: CommenceSession) -> None:
        name = _unique_name()
        # Add
        row_id = session.add(
            CATEGORY,
            {
                'contactKey': name,
                'firstName': 'ToDelete',
            },
        )
        assert row_id is not None

        # Confirm it exists
        rows = (
            session.query(CATEGORY)
            .columns('contactKey')
            .where('contactKey', 'Equal To', name)
            .execute()
        )
        assert len(rows) == 1

        # Delete
        session.delete(row_id, CATEGORY)

        # Confirm it's gone
        rows = (
            session.query(CATEGORY)
            .columns('contactKey')
            .where('contactKey', 'Equal To', name)
            .execute()
        )
        assert len(rows) == 0

    def test_original_data_intact_after_tests(self, session: CommenceSession) -> None:
        """Sanity check: tutorial data should still have the original 25 contacts."""
        count = session.schema.get_row_count(CATEGORY)
        assert count == len(CONTACT_ITEM_NAMES)


# ── Full CRUD cycle ─────────────────────────────────────────────────────────


class TestCrudCycle:
    """Test the complete Create → Read → Update → Delete lifecycle."""

    def test_full_lifecycle(self, session: CommenceSession) -> None:
        name = _unique_name()

        # CREATE
        row_id = session.add(
            CATEGORY,
            {
                'contactKey': name,
                'firstName': 'Lifecycle',
                'lastName': 'Test',
                'busCity': 'TestCity',
                'Title': 'QA Engineer',
            },
        )
        assert row_id is not None

        # READ
        result = session.read_by_id(
            CATEGORY,
            row_id,
            columns=['contactKey', 'firstName', 'lastName', 'busCity', 'Title'],
        )
        assert result['contactKey'] == name
        assert result['firstName'] == 'Lifecycle'
        assert result['busCity'] == 'TestCity'
        assert result['Title'] == 'QA Engineer'

        # UPDATE
        session.edit(
            row_id,
            CATEGORY,
            {
                'busCity': 'UpdatedCity',
                'Title': 'Senior QA Engineer',
            },
        )

        result = session.read_by_id(
            CATEGORY,
            row_id,
            columns=['busCity', 'Title'],
        )
        assert result['busCity'] == 'UpdatedCity'
        assert result['Title'] == 'Senior QA Engineer'

        # DELETE
        session.delete(row_id, CATEGORY)

        rows = (
            session.query(CATEGORY)
            .columns('contactKey')
            .where('contactKey', 'Equal To', name)
            .execute()
        )
        assert len(rows) == 0

        # Verify tutorial data intact
        assert session.schema.get_row_count(CATEGORY) == len(CONTACT_ITEM_NAMES)
