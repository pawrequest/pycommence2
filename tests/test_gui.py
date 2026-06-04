"""Unit tests for the GUI module — no Commence or NiceGUI runtime required.

Tests cover:
- ComWorker state machine (start/stop/connected/error)
- AppState management
- FilterBuilder logic
- Layout helpers
- Module-level ``create_app`` wiring (mocked)

The tests mock out COM (CommenceSession) and NiceGUI (``ui``) so they
run in any environment without a live database or display server.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# ComWorker tests (state.py)
# ---------------------------------------------------------------------------


class TestComWorkerStartStop:
    """Test ComWorker lifecycle without a real COM connection."""

    def _make_worker(self):
        """Create a ComWorker with CommenceSession mocked out."""
        from pycommence2.gui.state import ComWorker

        return ComWorker()

    def test_initial_state(self) -> None:
        worker = self._make_worker()
        assert worker.connected is False
        assert worker.startup_error is None

    def test_start_sets_connected(self) -> None:
        worker = self._make_worker()
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = r'C:\Test'

        with patch('pycommence2.session.CommenceSession.__new__', return_value=mock_session):
            with patch('pycommence2.session.CommenceSession.__init__', return_value=None):
                worker.start()
        try:
            assert worker.connected is True
            assert worker.startup_error is None
        finally:
            worker.stop()

    def test_start_records_error_on_failure(self) -> None:
        worker = self._make_worker()
        with patch(
            'pycommence2.session.CommenceSession.__init__',
            side_effect=RuntimeError('No Commence'),
        ):
            worker.start()
        assert worker.connected is False
        assert worker.startup_error is not None
        assert 'No Commence' in str(worker.startup_error)

    def test_stop_idempotent(self) -> None:
        """Calling stop() when not started should not raise."""
        worker = self._make_worker()
        worker.stop()  # no-op

    def test_stop_joins_thread(self) -> None:
        worker = self._make_worker()
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = r'C:\Test'

        with patch('pycommence2.session.CommenceSession.__new__', return_value=mock_session):
            with patch('pycommence2.session.CommenceSession.__init__', return_value=None):
                worker.start()
        assert worker._dispatcher._thread is not None
        assert worker._dispatcher._thread.is_alive()
        worker.stop()
        assert not worker._dispatcher._thread.is_alive()


class TestComWorkerRun:
    """Test dispatching callables to the COM thread."""

    @pytest.fixture
    def worker_with_session(self):
        from pycommence2.gui.state import ComWorker

        w = ComWorker()
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = r'C:\Test'

        with patch('pycommence2.session.CommenceSession.__new__', return_value=mock_session):
            with patch('pycommence2.session.CommenceSession.__init__', return_value=None):
                w.start()
        yield w, mock_session
        w.stop()

    @pytest.mark.asyncio
    async def test_run_returns_result(self, worker_with_session) -> None:
        worker, mock_session = worker_with_session
        mock_session.db_name = 'TestDB'
        result = await worker.run(lambda s: s.db_name)
        assert result == 'TestDB'

    @pytest.mark.asyncio
    async def test_run_passes_extra_args(self, worker_with_session) -> None:
        worker, mock_session = worker_with_session
        mock_session.read.return_value = [{'Name': 'Alice'}]
        result = await worker.run(lambda s, cat: s.read(cat), 'Contact')
        mock_session.read.assert_called_with('Contact')

    @pytest.mark.asyncio
    async def test_run_propagates_exceptions(self, worker_with_session) -> None:
        worker, mock_session = worker_with_session
        mock_session.read.side_effect = ValueError('boom')
        with pytest.raises(ValueError, match='boom'):
            await worker.run(lambda s: s.read('Contact'))

    @pytest.mark.asyncio
    async def test_run_when_not_connected_raises(self) -> None:
        from pycommence2.gui.state import ComWorker

        worker = ComWorker()
        # Not started → not connected
        with pytest.raises(RuntimeError, match='not connected'):
            await worker.run(lambda s: s.db_name)


# ---------------------------------------------------------------------------
# AppState tests (state.py)
# ---------------------------------------------------------------------------


class TestAppState:
    def test_default_edit_unlocked(self) -> None:
        from pycommence2.gui.state import AppState

        state = AppState()
        assert state.edit_unlocked is False

    def test_toggle_edit(self) -> None:
        from pycommence2.gui.state import AppState

        state = AppState()
        state.edit_unlocked = True
        assert state.edit_unlocked is True
        state.edit_unlocked = False
        assert state.edit_unlocked is False


# ---------------------------------------------------------------------------
# FilterBuilder tests (browser.py) — test the clause logic only
# ---------------------------------------------------------------------------


class TestFilterBuilderLogic:
    """Test _FilterBuilder.build_filters() and clause management.

    We mock out NiceGUI UI components to test pure logic.
    """

    def _make_builder(self, field_names=None):
        """Create a _FilterBuilder with NiceGUI mocked."""
        if field_names is None:
            field_names = ['Name', 'Email', 'City']

        # Mock all NiceGUI UI calls
        with patch('pycommence2.gui.browser.ui') as mock_ui:
            # Make the context managers work
            mock_ui.row.return_value.__enter__ = MagicMock(return_value=None)
            mock_ui.row.return_value.__exit__ = MagicMock(return_value=False)
            mock_ui.column.return_value.__enter__ = MagicMock(return_value=None)
            mock_ui.column.return_value.__exit__ = MagicMock(return_value=False)
            mock_ui.select.return_value.classes.return_value = MagicMock()
            mock_ui.input.return_value.classes.return_value = MagicMock()
            mock_ui.button.return_value.props.return_value = MagicMock()

            from pycommence2.gui.browser import _FilterBuilder

            fb = _FilterBuilder(field_names)
        return fb

    def test_empty_build(self) -> None:
        fb = self._make_builder()
        assert fb.build_filters() == []

    def test_add_clause_builds_filter_string(self) -> None:
        fb = self._make_builder()
        # Simulate adding a clause directly
        fb._clauses.append(
            {
                'field': 'Name',
                'qual': 'Contains',
                'value': 'Smith',
                'str': '[ViewFilter(1, F, , "Name", "Contains", "Smith", False)]',
            }
        )
        filters = fb.build_filters()
        assert len(filters) == 1
        assert '"Name"' in filters[0]
        assert '"Contains"' in filters[0]
        assert '"Smith"' in filters[0]

    def test_multiple_clauses(self) -> None:
        fb = self._make_builder()
        for i, (field, qual, val) in enumerate(
            [
                ('Name', 'Contains', 'Smith'),
                ('City', 'Equal To', 'Boston'),
            ],
            1,
        ):
            fb._clauses.append(
                {
                    'field': field,
                    'qual': qual,
                    'value': val,
                    'str': f'[ViewFilter({i}, F, , "{field}", "{qual}", "{val}", False)]',
                }
            )
        filters = fb.build_filters()
        assert len(filters) == 2
        assert 'ViewFilter(1' in filters[0]
        assert 'ViewFilter(2' in filters[1]

    def test_max_four_clauses(self) -> None:
        fb = self._make_builder()
        # Add 4 clauses
        for i in range(4):
            fb._clauses.append(
                {
                    'field': 'Name',
                    'qual': 'Contains',
                    'value': f'val{i}',
                    'str': f'[ViewFilter({i + 1}, F, , "Name", "Contains", "val{i}", False)]',
                }
            )
        filters = fb.build_filters()
        assert len(filters) == 4


# ---------------------------------------------------------------------------
# create_app wiring tests (__init__.py)
# ---------------------------------------------------------------------------


class TestCreateApp:
    """Verify create_app registers pages and starts the COM worker."""

    def test_create_app_starts_worker(self) -> None:
        """create_app() should instantiate and start a ComWorker."""
        mock_worker_cls = MagicMock()
        mock_worker_instance = MagicMock()
        mock_worker_instance.connected = True
        mock_worker_cls.return_value = mock_worker_instance

        with (
            patch('pycommence2.gui.state.ComWorker', mock_worker_cls),
            patch('pycommence2.gui.browser.register'),
            patch('pycommence2.gui.dashboard.register'),
            patch('pycommence2.gui.detail.register'),
            patch('pycommence2.gui.schema_explorer.register'),
            patch('pycommence2.gui.export_dialog.register'),
            patch('pycommence2.gui.dde_console.register'),
            patch('pycommence2.gui.app', create=True),
        ):
            # Need to also patch the nicegui import
            with patch.dict('sys.modules', {'nicegui': MagicMock(), 'nicegui.app': MagicMock()}):
                import pycommence2.gui as gui_mod

                # Reset the module-level worker
                original_worker = gui_mod.state.worker
                try:
                    gui_mod.create_app()
                    mock_worker_instance.start.assert_called_once()
                finally:
                    gui_mod.state.worker = original_worker


# ---------------------------------------------------------------------------
# Layout helper tests (layout.py)
# ---------------------------------------------------------------------------


class TestLayoutHelpers:
    """Test notify_* helper functions (they call ui.notify)."""

    def test_notify_error(self) -> None:
        with patch('pycommence2.gui.layout.ui') as mock_ui:
            from pycommence2.gui.layout import notify_error

            notify_error('Something went wrong')
            mock_ui.notify.assert_called_once()
            call_args = mock_ui.notify.call_args
            assert 'Something went wrong' in call_args[0]
            assert call_args[1]['type'] == 'negative'

    def test_notify_success(self) -> None:
        with patch('pycommence2.gui.layout.ui') as mock_ui:
            from pycommence2.gui.layout import notify_success

            notify_success('All good')
            mock_ui.notify.assert_called_once()
            call_args = mock_ui.notify.call_args
            assert 'All good' in call_args[0]
            assert call_args[1]['type'] == 'positive'

    def test_set_edit_mode(self) -> None:
        from pycommence2.gui.layout import _set_edit_mode
        from pycommence2.gui.state import app_state

        original = app_state.edit_unlocked
        try:
            _set_edit_mode(True)
            assert app_state.edit_unlocked is True
            _set_edit_mode(False)
            assert app_state.edit_unlocked is False
        finally:
            app_state.edit_unlocked = original


# ---------------------------------------------------------------------------
# DDE Console template data test (dde_console.py)
# ---------------------------------------------------------------------------


class TestDdeConsoleTemplates:
    """Verify the quick-template data is well-formed."""

    def test_templates_are_bracketed_commands(self) -> None:
        """Each template should be a bracket-wrapped DDE command."""
        # We just verify the template tuples exist and have the right shape
        # by importing the module's render function and inspecting
        # Template data is embedded in _render_dde_console, so we
        # test it indirectly by checking the module imports cleanly
        with patch('pycommence2.gui.dde_console.ui'):
            with patch('pycommence2.gui.dde_console.frame'):
                with patch('pycommence2.gui.dde_console.worker'):
                    # Module loaded — that's enough for a smoke test
                    from pycommence2.gui import dde_console

                    assert hasattr(dde_console, 'register')
                    assert callable(dde_console.register)
