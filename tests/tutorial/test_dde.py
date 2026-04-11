"""Tests for DdeService – DDE Execute/Request commands against Tutorial DB."""

from __future__ import annotations

import uuid

from pycommence import CommenceSession
from tests.sample_data import CONTACT_ITEM_NAMES

CATEGORY = 'Contact'


def _unique_name() -> str:
    return f'Test.{uuid.uuid4().hex[:8]}'


class TestDdeItemRead:
    """Read operations via DDE."""

    def test_get_field(self, session: CommenceSession) -> None:
        val = session.dde.get_field(CATEGORY, 'Gates.Bill', 'firstName')
        assert val == 'Bill'

    def test_get_fields(self, session: CommenceSession) -> None:
        vals = session.dde.get_fields(
            CATEGORY,
            'Gates.Bill',
            'firstName',
            'lastName',
        )
        assert vals[0] == 'Bill'
        assert vals[1] == 'Gates'

    def test_get_item_names(self, session: CommenceSession) -> None:
        names = session.dde.get_item_names(CATEGORY)
        assert sorted(names) == sorted(CONTACT_ITEM_NAMES)

    def test_get_item_count(self, session: CommenceSession) -> None:
        count = session.dde.get_item_count(CATEGORY)
        assert count == len(CONTACT_ITEM_NAMES)


class TestDdeItemCrud:
    """CRUD lifecycle via DDE (add, edit, delete)."""

    def test_add_edit_delete(self, session: CommenceSession) -> None:
        name = _unique_name()
        try:
            # Add via DDE
            session.dde.add_item(CATEGORY, name)

            # Verify it exists
            count = session.query(CATEGORY).where('contactKey', 'Equal To', name).count()
            assert count == 1

            # Edit via DDE
            session.dde.edit_item(CATEGORY, name, 'firstName', 'DdeTest')

            # Verify edit
            val = session.dde.get_field(CATEGORY, name, 'firstName')
            assert val == 'DdeTest'

            # Delete via DDE
            session.dde.delete_item(CATEGORY, name)

            # Verify deleted
            count = session.query(CATEGORY).where('contactKey', 'Equal To', name).count()
            assert count == 0
        except Exception:
            # Fallback cleanup
            try:
                session.dde.delete_item(CATEGORY, name)
            except Exception:
                pass
            raise


class TestDdeDatabaseDefinition:
    def test_get_database_definition(self, session: CommenceSession) -> None:
        info = session.dde.get_database_definition()
        assert isinstance(info, dict)
        assert 'name' in info
        assert info['name'] == 'Tutorial'
