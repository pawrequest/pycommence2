"""Tests for SchemaService – category listing, field introspection, connections."""

from __future__ import annotations

from pycommence2 import (
    CategoryInfo,
    CommenceSession,
    ConnectionInfo,
    FieldInfo,
    FieldType,
)
from tests.sample_data import CONTACT_FIELD_NAMES, CONTACT_ITEM_NAMES


# ── Categories ──────────────────────────────────────────────────────────────


class TestListCategories:
    def test_returns_list_of_strings(self, session: CommenceSession) -> None:
        categories = session.schema.list_categories()
        assert isinstance(categories, list)
        assert all(isinstance(c, str) for c in categories)

    def test_contact_category_exists(self, session: CommenceSession) -> None:
        categories = session.schema.list_categories()
        assert 'Contact' in categories

    def test_account_category_exists(self, session: CommenceSession) -> None:
        categories = session.schema.list_categories()
        assert 'Account' in categories

    def test_tutorial_has_many_categories(self, session: CommenceSession) -> None:
        categories = session.schema.list_categories()
        # Tutorial DB has 39 categories
        assert len(categories) >= 30


class TestCategoryCount:
    def test_count_matches_list(self, session: CommenceSession) -> None:
        count = session.schema.get_category_count()
        categories = session.schema.list_categories()
        assert count == len(categories)


class TestCategoryDefinition:
    def test_returns_category_info(self, session: CommenceSession) -> None:
        info = session.schema.get_category_definition('Contact')
        assert isinstance(info, CategoryInfo)
        assert info.name == 'Contact'

    def test_max_items(self, session: CommenceSession) -> None:
        info = session.schema.get_category_definition('Contact')
        assert info.max_items == 500_000


# ── Fields ──────────────────────────────────────────────────────────────────


class TestFieldNames:
    def test_returns_all_contact_fields(self, session: CommenceSession) -> None:
        names = session.schema.get_field_names('Contact')
        assert isinstance(names, list)
        assert len(names) == len(CONTACT_FIELD_NAMES)

    def test_known_field_names_present(self, session: CommenceSession) -> None:
        names = session.schema.get_field_names('Contact')
        for expected in CONTACT_FIELD_NAMES:
            assert expected in names, f'Missing field: {expected}'

    def test_field_names_match_exactly(self, session: CommenceSession) -> None:
        names = session.schema.get_field_names('Contact')
        assert sorted(names) == sorted(CONTACT_FIELD_NAMES)


class TestFieldCount:
    def test_count_matches_names(self, session: CommenceSession) -> None:
        count = session.schema.get_field_count('Contact')
        names = session.schema.get_field_names('Contact')
        assert count == len(names)


class TestFieldDefinitions:
    def test_get_all_fields_returns_field_infos(self, session: CommenceSession) -> None:
        fields = session.schema.get_fields('Contact')
        assert all(isinstance(f, FieldInfo) for f in fields)
        assert len(fields) == len(CONTACT_FIELD_NAMES)

    def test_contact_key_is_name_type(self, session: CommenceSession) -> None:
        fi = session.schema.get_field_definition('Contact', 'contactKey')
        assert fi.field_type == FieldType.NAME
        assert fi.is_mandatory is True
        assert fi.max_chars == 50

    def test_email_business_is_email_type(self, session: CommenceSession) -> None:
        fi = session.schema.get_field_definition('Contact', 'emailBusiness')
        assert fi.field_type == FieldType.EMAIL

    def test_business_number_is_telephone(self, session: CommenceSession) -> None:
        fi = session.schema.get_field_definition('Contact', 'businessNumber')
        assert fi.field_type == FieldType.TELEPHONE

    def test_influence_is_selection(self, session: CommenceSession) -> None:
        fi = session.schema.get_field_definition('Contact', 'Influence')
        assert fi.field_type == FieldType.SELECTION
        assert fi.is_combo is True

    def test_do_not_solicit_is_checkbox(self, session: CommenceSession) -> None:
        fi = session.schema.get_field_definition('Contact', 'doNotSolicit')
        assert fi.field_type == FieldType.CHECK_BOX

    def test_facebook_link_is_url(self, session: CommenceSession) -> None:
        fi = session.schema.get_field_definition('Contact', 'FacebookLink')
        assert fi.field_type == FieldType.URL

    def test_birthday_is_date(self, session: CommenceSession) -> None:
        fi = session.schema.get_field_definition('Contact', 'Birthday')
        assert fi.field_type == FieldType.DATE

    def test_first_name_is_text(self, session: CommenceSession) -> None:
        fi = session.schema.get_field_definition('Contact', 'firstName')
        assert fi.field_type == FieldType.TEXT


# ── Connections ─────────────────────────────────────────────────────────────


class TestConnections:
    def test_contact_has_connections(self, session: CommenceSession) -> None:
        conns = session.schema.get_connection_names('Contact')
        assert isinstance(conns, list)
        assert len(conns) > 0
        assert all(isinstance(c, ConnectionInfo) for c in conns)

    def test_connection_has_name_and_to_category(self, session: CommenceSession) -> None:
        conns = session.schema.get_connection_names('Contact')
        for c in conns:
            assert c.name, f'Connection has empty name: {c}'
            assert c.to_category, f'Connection has empty to_category: {c}'

    def test_relates_to_account_exists(self, session: CommenceSession) -> None:
        conns = session.schema.get_connection_names('Contact')
        conn_names = [(c.name, c.to_category) for c in conns]
        assert ('Relates to', 'Account') in conn_names

    def test_connection_count_matches(self, session: CommenceSession) -> None:
        count = session.schema.get_connection_count('Contact')
        conns = session.schema.get_connection_names('Contact')
        assert count == len(conns)


# ── Row count ───────────────────────────────────────────────────────────────


class TestRowCount:
    def test_contact_row_count(self, session: CommenceSession) -> None:
        count = session.schema.get_row_count('Contact')
        assert count == len(CONTACT_ITEM_NAMES)
