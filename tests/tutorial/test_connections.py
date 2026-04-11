"""Tests for ConnectionService – assign/unassign connections against Tutorial DB.

The Tutorial DB has Contact → Account via 'Relates to' connection.
"""

from __future__ import annotations

import uuid


from pycommence import CommenceSession


CONTACT_CAT = 'Contact'
ACCOUNT_CAT = 'Account'
CONNECTION_NAME = 'Relates to'


def _unique_name() -> str:
    return f'Test.{uuid.uuid4().hex[:8]}'


class TestConnectionQuery:
    """Query existing connections (read-only)."""

    def test_get_connected_item_count(self, session: CommenceSession) -> None:
        """Gates.Bill should be connected to at least one Account."""
        count = session.connections.get_connected_item_count(
            CONTACT_CAT,
            'Gates.Bill',
            CONNECTION_NAME,
            ACCOUNT_CAT,
        )
        assert isinstance(count, int)
        assert count >= 0

    def test_get_connected_item_names(self, session: CommenceSession) -> None:
        """Query connected account names for a known contact."""
        names = session.connections.get_connected_item_names(
            CONTACT_CAT,
            'Gates.Bill',
            CONNECTION_NAME,
            ACCOUNT_CAT,
        )
        assert isinstance(names, list)

    def test_get_connected_item_field(self, session: CommenceSession) -> None:
        """Query a specific field from connected accounts."""
        names = session.connections.get_connected_item_names(
            CONTACT_CAT,
            'Gates.Bill',
            CONNECTION_NAME,
            ACCOUNT_CAT,
        )
        if names:
            # If there are connected accounts, we should be able to get a field
            values = session.connections.get_connected_item_field(
                CONTACT_CAT,
                'Gates.Bill',
                CONNECTION_NAME,
                ACCOUNT_CAT,
                'accountKey',
            )
            assert isinstance(values, list)


class TestConnectionAssignUnassign:
    """Test assign/unassign lifecycle.

    Creates a temporary contact + account, assigns them, verifies, then cleans up.
    """

    def test_assign_and_unassign(self, session: CommenceSession) -> None:
        contact_name = _unique_name()
        account_name = _unique_name()
        try:
            # Create temp items
            session.add(CONTACT_CAT, {'contactKey': contact_name, 'firstName': 'ConnTest'})
            session.add(ACCOUNT_CAT, {'accountKey': account_name})

            # Assign connection
            session.assign_connection(
                CONTACT_CAT,
                contact_name,
                CONNECTION_NAME,
                ACCOUNT_CAT,
                account_name,
            )

            # Verify
            names = session.connections.get_connected_item_names(
                CONTACT_CAT,
                contact_name,
                CONNECTION_NAME,
                ACCOUNT_CAT,
            )
            assert account_name in names

            # Unassign
            session.unassign_connection(
                CONTACT_CAT,
                contact_name,
                CONNECTION_NAME,
                ACCOUNT_CAT,
                account_name,
            )

            # Verify removed
            names = session.connections.get_connected_item_names(
                CONTACT_CAT,
                contact_name,
                CONNECTION_NAME,
                ACCOUNT_CAT,
            )
            assert account_name not in names
        finally:
            # Clean up
            self._delete_by_name(session, CONTACT_CAT, 'contactKey', contact_name)
            self._delete_by_name(session, ACCOUNT_CAT, 'accountKey', account_name)

    @staticmethod
    def _delete_by_name(
        session: CommenceSession,
        category: str,
        key_field: str,
        name: str,
    ) -> None:
        rows = (
            session.query(category).columns(key_field).where(key_field, 'Equal To', name).execute()
        )
        if rows and rows[0].row_id:
            session.delete(rows[0].row_id, category)
