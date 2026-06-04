"""Tests for Step 2 DBAPI surface — new DDE methods added in v0.5.0.

These tests use mocks to verify the DDE command strings are correct.
Integration tests against the Tutorial DB are in test_dde.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock


from pycommence2.services.dde import DdeService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dde() -> tuple[DdeService, MagicMock]:
    """Create a DdeService with a mocked conversation."""
    db = MagicMock()
    conv = MagicMock()
    db.get_conversation.return_value = conv
    svc = DdeService(db)
    return svc, conv


# ---------------------------------------------------------------------------
# Item marking
# ---------------------------------------------------------------------------


class TestItemMarking:
    def test_get_mark_item(self):
        svc, conv = _make_dde()
        conv.request.return_value = 'Jane Doe\n'
        result = svc.get_mark_item('Contact')
        conv.request.assert_called_once_with('[GetMarkItem("Contact")]')
        assert result == 'Jane Doe'

    def test_view_mark_item_no_view(self):
        svc, conv = _make_dde()
        svc.view_mark_item('Contact', 'Jane Doe')
        conv.execute.assert_called_once_with('[ViewMarkItem("", "Contact", "Jane Doe")]')

    def test_view_mark_item_with_view(self):
        svc, conv = _make_dde()
        svc.view_mark_item('Contact', 'Jane Doe', view_name='Active')
        conv.execute.assert_called_once_with('[ViewMarkItem("Active", "Contact", "Jane Doe")]')

    def test_mark_active_item(self):
        svc, conv = _make_dde()
        svc.mark_active_item('Contact')
        conv.execute.assert_called_once_with('[MarkActiveItem("Contact")]')


# ---------------------------------------------------------------------------
# View-to-file
# ---------------------------------------------------------------------------


class TestViewToFile:
    def test_get_view_to_file_html(self):
        svc, conv = _make_dde()
        svc.get_view_to_file('My View', 'C:\\out.html')
        conv.execute.assert_called_once_with('[GetViewToFile("My View", "C:\\out.html", "HTML")]')

    def test_get_view_to_file_text(self):
        svc, conv = _make_dde()
        svc.get_view_to_file('My View', 'C:\\out.txt', file_type='Text')
        conv.execute.assert_called_once_with('[GetViewToFile("My View", "C:\\out.txt", "Text")]')


# ---------------------------------------------------------------------------
# Merge templates
# ---------------------------------------------------------------------------


class TestMergeTemplate:
    def test_merge_template(self):
        svc, conv = _make_dde()
        svc.merge_template('Contact', 'Jane Doe', 'Letter', 'C:\\letter.doc')
        conv.execute.assert_called_once_with(
            '[MergeTemplateCreate("Contact", "Jane Doe", "Letter", "C:\\letter.doc")]'
        )


# ---------------------------------------------------------------------------
# Form script management
# ---------------------------------------------------------------------------


class TestFormScripts:
    def test_check_out_form_script(self):
        svc, conv = _make_dde()
        svc.check_out_form_script('Contact', 'Detail', 'C:\\script.vbs')
        conv.execute.assert_called_once_with(
            '[CheckOutFormScript("Contact", "Detail", "C:\\script.vbs")]'
        )

    def test_check_in_form_script(self):
        svc, conv = _make_dde()
        svc.check_in_form_script('Contact', 'Detail', 'C:\\script.vbs')
        conv.execute.assert_called_once_with(
            '[CheckInFormScript("Contact", "Detail", "C:\\script.vbs")]'
        )


# ---------------------------------------------------------------------------
# Preferences / system info
# ---------------------------------------------------------------------------


class TestPreferences:
    def test_get_preference(self):
        svc, conv = _make_dde()
        conv.request.return_value = 'Admin User\n'
        result = svc.get_preference('Me')
        conv.request.assert_called_once_with('[GetPreference("Me")]')
        assert result == 'Admin User'

    def test_get_caller_id(self):
        svc, conv = _make_dde()
        conv.request.return_value = 'CALLER-123\n'
        result = svc.get_caller_id()
        conv.request.assert_called_once_with('[GetCallerID()]')
        assert result == 'CALLER-123'


# ---------------------------------------------------------------------------
# Database definition
# ---------------------------------------------------------------------------


class TestDatabaseDefinition:
    def test_get_database_definition(self):
        svc, conv = _make_dde()
        conv.request.return_value = 'MyDB|C:\\db|6.0|Admin|Yes'
        result = svc.get_database_definition()
        assert result['name'] == 'MyDB'
        assert result['path'] == 'C:\\db'
        assert result['version'] == '6.0'
        assert result['registered_user'] == 'Admin'
        assert result['shared'] == 'Yes'
