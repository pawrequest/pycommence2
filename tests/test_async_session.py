"""Tests for AsyncCommenceSession and ThreadDispatcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# ThreadDispatcher tests
# ---------------------------------------------------------------------------
from pycommence2._thread_dispatch import ThreadDispatcher


class TestThreadDispatcherLifecycle:
    """Start / stop / connected state."""

    def test_initial_state(self):
        d = ThreadDispatcher()
        assert not d.connected
        assert d.startup_error is None
        assert d.session is None

    def test_start_and_connected(self):
        d = ThreadDispatcher()
        with (
            patch('pycommence2.session.CommenceSession') as MockSession,
        ):
            mock_session = MagicMock()
            mock_session.db_name = 'TestDB'
            mock_session.db_path = 'C:\\test'
            MockSession.return_value = mock_session

            # Patch at the import location inside _worker_loop
            with patch(
                'pycommence2.session.CommenceSession',
                MockSession,
            ):
                d.start()
                assert d.connected
                assert d.startup_error is None
                d.stop()

    def test_start_records_error_on_failure(self):
        d = ThreadDispatcher()
        with patch(
            'pycommence2.session.CommenceSession',
            side_effect=RuntimeError('No Commence'),
        ):
            d.start()
            assert not d.connected
            assert isinstance(d.startup_error, RuntimeError)

    def test_stop_idempotent(self):
        d = ThreadDispatcher()
        d.stop()  # no thread started — should not raise

    def test_stop_joins_thread(self):
        d = ThreadDispatcher()
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = 'C:\\test'
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            d.start()
            assert d._thread is not None
            assert d._thread.is_alive()
            d.stop()
            assert not d._thread.is_alive()


class TestThreadDispatcherSubmit:
    """Sync submit() method."""

    def _make_dispatcher(self):
        d = ThreadDispatcher()
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = 'C:\\test'
        return d, mock_session

    def test_submit_returns_future(self):
        d, mock_session = self._make_dispatcher()
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            d.start()
            try:
                future = d.submit(lambda s: s.db_name)
                assert future.result(timeout=5) == 'TestDB'
            finally:
                d.stop()

    def test_submit_propagates_exception(self):
        d, mock_session = self._make_dispatcher()
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            d.start()
            try:
                future = d.submit(lambda s: 1 / 0)
                with pytest.raises(ZeroDivisionError):
                    future.result(timeout=5)
            finally:
                d.stop()

    def test_submit_raises_when_not_connected(self):
        d = ThreadDispatcher()
        with pytest.raises(RuntimeError, match='not connected'):
            d.submit(lambda s: s.db_name)


class TestThreadDispatcherRun:
    """Async run() method."""

    @pytest.mark.asyncio
    async def test_run_returns_result(self):
        d = ThreadDispatcher()
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = 'C:\\test'
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            d.start()
            try:
                result = await d.run(lambda s: s.db_name)
                assert result == 'TestDB'
            finally:
                d.stop()

    @pytest.mark.asyncio
    async def test_run_propagates_exceptions(self):
        d = ThreadDispatcher()
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = 'C:\\test'
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            d.start()
            try:
                with pytest.raises(ZeroDivisionError):
                    await d.run(lambda s: 1 / 0)
            finally:
                d.stop()

    @pytest.mark.asyncio
    async def test_run_passes_extra_args(self):
        d = ThreadDispatcher()
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = 'C:\\test'
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            d.start()
            try:
                result = await d.run(lambda s, x, y: x + y, 3, 4)
                assert result == 7
            finally:
                d.stop()

    @pytest.mark.asyncio
    async def test_run_raises_when_not_connected(self):
        d = ThreadDispatcher()
        with pytest.raises(RuntimeError, match='not connected'):
            await d.run(lambda s: s.db_name)


# ---------------------------------------------------------------------------
# AsyncCommenceSession tests
# ---------------------------------------------------------------------------
from pycommence2.async_session import AsyncCommenceSession


class TestAsyncSessionLifecycle:
    """Context manager and start/stop."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        with patch(
            'pycommence2.session.CommenceSession',
        ) as MockSession:
            mock_session = MagicMock()
            mock_session.db_name = 'TestDB'
            mock_session.db_path = 'C:\\test'
            MockSession.return_value = mock_session

            async with AsyncCommenceSession() as db:
                assert db._dispatcher.connected

    @pytest.mark.asyncio
    async def test_context_manager_raises_on_failure(self):
        with patch(
            'pycommence2.session.CommenceSession',
            side_effect=RuntimeError('No Commence'),
        ):
            with pytest.raises(RuntimeError, match='No Commence'):
                async with AsyncCommenceSession():
                    pass  # pragma: no cover

    @pytest.mark.asyncio
    async def test_repr(self):
        db = AsyncCommenceSession()
        assert 'disconnected' in repr(db)


class TestAsyncSessionMetadata:
    """db_name, db_path, db_version, db_shared."""

    @pytest.fixture
    def mock_session(self):
        s = MagicMock()
        s.db_name = 'TestDB'
        s.db_path = 'C:\\test'
        s.db_version = '6.0.0'
        s.db_shared = False
        return s

    @pytest.mark.asyncio
    async def test_db_name(self, mock_session):
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                assert await db.db_name() == 'TestDB'

    @pytest.mark.asyncio
    async def test_db_path(self, mock_session):
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                assert await db.db_path() == 'C:\\test'

    @pytest.mark.asyncio
    async def test_db_version(self, mock_session):
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                assert await db.db_version() == '6.0.0'

    @pytest.mark.asyncio
    async def test_db_shared(self, mock_session):
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                assert await db.db_shared() is False


class TestAsyncSessionSchema:
    """list_categories, get_fields, get_connections, get_row_count."""

    @pytest.fixture
    def mock_session(self):
        s = MagicMock()
        s.db_name = 'TestDB'
        s.db_path = 'C:\\test'
        s.schema.list_categories.return_value = ['Contact', 'Hire']
        s.schema.get_fields.return_value = [MagicMock(name='Name')]
        s.schema.get_connection_names.return_value = [MagicMock(name='Relates to')]
        s.schema.get_row_count.return_value = 42
        return s

    @pytest.mark.asyncio
    async def test_list_categories(self, mock_session):
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                cats = await db.list_categories()
                assert cats == ['Contact', 'Hire']

    @pytest.mark.asyncio
    async def test_get_row_count(self, mock_session):
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                count = await db.get_row_count('Contact')
                assert count == 42


class TestAsyncSessionRead:
    """read, read_by_id, query, count."""

    @pytest.fixture
    def mock_session(self):
        from pycommence2.models import RowResult

        s = MagicMock()
        s.db_name = 'TestDB'
        s.db_path = 'C:\\test'
        s.read.return_value = [
            RowResult(columns={'Name': 'Alice'}, row_id='r1'),
            RowResult(columns={'Name': 'Bob'}, row_id='r2'),
        ]
        s.read_by_id.return_value = RowResult(
            columns={'Name': 'Alice', 'Email': 'alice@example.com'},
            row_id='r1',
        )
        return s

    @pytest.mark.asyncio
    async def test_read(self, mock_session):
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                rows = await db.read('Contact', max_rows=10)
                assert len(rows) == 2
                assert rows[0]['Name'] == 'Alice'

    @pytest.mark.asyncio
    async def test_read_by_id(self, mock_session):
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                row = await db.read_by_id('Contact', 'r1')
                assert row['Email'] == 'alice@example.com'

    @pytest.mark.asyncio
    async def test_query(self, mock_session):
        # Mock the fluent query builder chain
        mock_qb = MagicMock()
        mock_qb.columns.return_value = mock_qb
        mock_qb.where.return_value = mock_qb
        mock_qb.sort.return_value = mock_qb
        mock_qb.limit.return_value = mock_qb
        mock_qb.canonical.return_value = mock_qb
        from pycommence2.models import RowResult

        mock_qb.execute.return_value = [
            RowResult(columns={'Name': 'Smith'}, row_id='r1'),
        ]
        mock_session.query.return_value = mock_qb

        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                rows = await db.query(
                    'Contact',
                    columns=['Name'],
                    filters=[('Name', 'Contains', 'Smith')],
                    sort='Name',
                    limit=20,
                    canonical=True,
                )
                assert len(rows) == 1
                assert rows[0]['Name'] == 'Smith'

    @pytest.mark.asyncio
    async def test_count(self, mock_session):
        mock_qb = MagicMock()
        mock_qb.where.return_value = mock_qb
        mock_qb.count.return_value = 5
        mock_session.query.return_value = mock_qb

        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                n = await db.count('Contact', filters=[('Status', 'Equal To', 'Active')])
                assert n == 5


class TestAsyncSessionCRUD:
    """add, add_many, edit, delete."""

    @pytest.fixture
    def mock_session(self):
        s = MagicMock()
        s.db_name = 'TestDB'
        s.db_path = 'C:\\test'
        s.add.return_value = 'new-id'
        s.add_many.return_value = 3
        return s

    @pytest.mark.asyncio
    async def test_add(self, mock_session):
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                row_id = await db.add('Contact', {'Name': 'Jane'})
                assert row_id == 'new-id'

    @pytest.mark.asyncio
    async def test_add_many(self, mock_session):
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                count = await db.add_many(
                    'Contact',
                    [
                        {'Name': 'A'},
                        {'Name': 'B'},
                        {'Name': 'C'},
                    ],
                )
                assert count == 3

    @pytest.mark.asyncio
    async def test_edit(self, mock_session):
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                await db.edit('r1', 'Contact', {'Email': 'new@example.com'})
                mock_session.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete(self, mock_session):
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                await db.delete('r1', 'Contact')
                mock_session.delete.assert_called_once()


class TestAsyncSessionConnections:
    """assign_connection, unassign_connection."""

    @pytest.mark.asyncio
    async def test_assign_connection(self):
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = 'C:\\test'
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                await db.assign_connection(
                    'Person',
                    'John',
                    'Relates to',
                    'Company',
                    'Acme',
                )
                mock_session.assign_connection.assert_called_once_with(
                    'Person',
                    'John',
                    'Relates to',
                    'Company',
                    'Acme',
                )

    @pytest.mark.asyncio
    async def test_unassign_connection(self):
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = 'C:\\test'
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                await db.unassign_connection(
                    'Person',
                    'John',
                    'Relates to',
                    'Company',
                    'Acme',
                )
                mock_session.unassign_connection.assert_called_once()


class TestAsyncSessionExport:
    """export, backup, import."""

    @pytest.mark.asyncio
    async def test_export(self):
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = 'C:\\test'
        mock_session.export.return_value = 100
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                count = await db.export('Contact', 'out.csv')
                assert count == 100

    @pytest.mark.asyncio
    async def test_backup(self):
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = 'C:\\test'
        mock_session.backup.return_value = {'total_rows': 500}
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                stats = await db.backup('./backup')
                assert stats['total_rows'] == 500


class TestAsyncSessionDde:
    """DDE shortcuts."""

    @pytest.mark.asyncio
    async def test_dde_get_field(self):
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = 'C:\\test'
        mock_session.dde.get_field.return_value = 'jane@example.com'
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                email = await db.dde_get_field('Contact', 'Jane', 'Email')
                assert email == 'jane@example.com'

    @pytest.mark.asyncio
    async def test_dde_fire_trigger(self):
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = 'C:\\test'
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                await db.dde_fire_trigger('Nightly Sync')
                mock_session.dde.fire_trigger.assert_called_once_with('Nightly Sync')


class TestAsyncSessionRun:
    """The escape-hatch run() method."""

    @pytest.mark.asyncio
    async def test_run_arbitrary_function(self):
        mock_session = MagicMock()
        mock_session.db_name = 'TestDB'
        mock_session.db_path = 'C:\\test'
        mock_session.schema.get_fields.return_value = ['field1', 'field2']
        with patch(
            'pycommence2.session.CommenceSession',
            return_value=mock_session,
        ):
            async with AsyncCommenceSession() as db:
                fields = await db.run(lambda s: s.schema.get_fields('Contact'))
                assert fields == ['field1', 'field2']
