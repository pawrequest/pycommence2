"""Unit tests for the CLI module — no Commence connection required.

All CommenceSession interactions are mocked. Tests exercise click
command parsing, output formatting, and error handling.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from pycommence.models import (
    ConnectionInfo,
    FieldInfo,
    FieldType,
    RowResult,
)

# Import CLI after click/rich are guaranteed available
from pycommence.cli import (
    RENDERERS,
    _parse_filter,
    _render_csv,
    _render_json,
    _render_table,
    cli,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_session() -> MagicMock:
    """A fully-wired mock CommenceSession."""
    session = MagicMock()
    session.db_name = 'TestDB'
    session.db_path = r'C:\Commence\TestDB'
    session.db_version = '9.0'
    session.db_shared = False

    # Schema service
    session.schema.list_categories.return_value = ['Contact', 'Hire', 'Account']
    session.schema.get_row_count.side_effect = lambda cat: {
        'Contact': 25,
        'Hire': 100,
        'Account': 10,
    }.get(cat, 0)
    session.schema.get_fields.return_value = [
        FieldInfo(name='contactKey', field_type=FieldType.NAME, max_chars=50, is_mandatory=True),
        FieldInfo(name='emailBusiness', field_type=FieldType.EMAIL, max_chars=100),
        FieldInfo(name='Active', field_type=FieldType.CHECK_BOX, is_combo=True),
    ]
    session.schema.get_field_names.return_value = ['contactKey', 'emailBusiness', 'Active']
    session.schema.get_connection_names.return_value = [
        ConnectionInfo(name='Is Employed by', to_category='Account'),
    ]

    # Query builder (mock)
    qb = MagicMock()
    qb.columns.return_value = qb
    qb.where.return_value = qb
    qb.sort.return_value = qb
    qb.limit.return_value = qb
    qb.canonical.return_value = qb
    qb.count.return_value = 42
    qb.execute.return_value = [
        RowResult(columns={'Name': 'Alice', 'Email': 'alice@example.com'}, row_id='r1'),
        RowResult(columns={'Name': 'Bob', 'Email': 'bob@example.com'}, row_id='r2'),
    ]
    qb._filters = ['[ViewFilter(1, F, , "Name", "Contains", "Smith", False)]']
    session.query.return_value = qb

    # Export / backup / import
    session.export.return_value = 50
    session.backup.return_value = {'categories_exported': 3, 'total_rows': 135}
    session.import_csv.return_value = {'rows_parsed': 10, 'rows_imported': 10, 'errors': []}
    session.import_json.return_value = {'rows_parsed': 5, 'rows_imported': 5, 'errors': []}

    return session


# ---------------------------------------------------------------------------
# Helper: _parse_filter
# ---------------------------------------------------------------------------


class TestParseFilter:
    def test_standard_filter(self) -> None:
        field, qual, value = _parse_filter('Name:Contains:Smith')
        assert field == 'Name'
        assert qual == 'Contains'
        assert value == 'Smith'

    def test_value_with_colons(self) -> None:
        """Value portion can contain colons (split on first two only)."""
        field, qual, value = _parse_filter('Note:Contains:foo:bar:baz')
        assert field == 'Note'
        assert qual == 'Contains'
        assert value == 'foo:bar:baz'

    def test_empty_value(self) -> None:
        field, qual, value = _parse_filter('Status:Blank:')
        assert field == 'Status'
        assert qual == 'Blank'
        assert value == ''

    def test_no_value_portion(self) -> None:
        """When no third part, value defaults to empty string."""
        field, qual, value = _parse_filter('Status:Blank')
        assert value == ''

    def test_single_part_raises(self) -> None:
        with pytest.raises(click.BadParameter, match='Filter must be'):
            _parse_filter('InvalidNoColon')

    def test_strips_whitespace(self) -> None:
        field, qual, value = _parse_filter('  Name : Contains : Smith  ')
        assert field == 'Name'
        assert qual == 'Contains'
        assert value == 'Smith'


# ---------------------------------------------------------------------------
# Renderers (unit tests for output formatting)
# ---------------------------------------------------------------------------


class TestRenderers:
    def test_renderers_dict_has_all_formats(self) -> None:
        assert set(RENDERERS.keys()) == {'table', 'json', 'csv'}

    def test_render_json_output(self) -> None:
        rows = [
            RowResult(columns={'Name': 'Alice', 'City': 'Boston'}),
            RowResult(columns={'Name': 'Bob', 'City': 'NYC'}),
        ]
        # _render_json uses click.echo to stdout
        runner = CliRunner()
        # We can test indirectly by capturing what click.echo writes
        with runner.isolated_filesystem():
            buf = io.StringIO()
            with patch('pycommence.cli.click.echo', side_effect=lambda x, **kw: buf.write(str(x))):
                _render_json(rows)
            data = json.loads(buf.getvalue())
            assert len(data) == 2
            assert data[0]['Name'] == 'Alice'

    def test_render_csv_output(self) -> None:
        rows = [
            RowResult(columns={'Name': 'Alice', 'City': 'Boston'}),
            RowResult(columns={'Name': 'Bob', 'City': 'NYC'}),
        ]
        buf = io.StringIO()
        with patch('pycommence.cli.click.echo', side_effect=lambda x, **kw: buf.write(str(x))):
            _render_csv(rows)
        reader = csv.DictReader(io.StringIO(buf.getvalue()))
        parsed = list(reader)
        assert len(parsed) == 2
        assert parsed[0]['Name'] == 'Alice'

    def test_render_csv_empty(self) -> None:
        """CSV render with no rows should produce no output."""
        buf = io.StringIO()
        with patch('pycommence.cli.click.echo', side_effect=lambda x, **kw: buf.write(str(x))):
            _render_csv([])
        assert buf.getvalue() == ''

    def test_render_table_empty(self) -> None:
        """Table render with no rows should not raise."""
        _render_table([])  # just verify no exception


# ---------------------------------------------------------------------------
# CLI commands — using Click CliRunner
# ---------------------------------------------------------------------------


class TestCliGroup:
    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'pycommence' in result.output

    def test_verbose_flag(self, runner: CliRunner) -> None:
        """--verbose should not error even without a subcommand."""
        result = runner.invoke(cli, ['--verbose', '--help'])
        assert result.exit_code == 0


class TestInfoCommand:
    def test_info(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['info'])
        assert result.exit_code == 0
        assert 'TestDB' in result.output

    def test_info_shows_path(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['info'])
        assert r'C:\Commence\TestDB' in result.output

    def test_info_shows_not_shared(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['info'])
        assert 'No' in result.output

    def test_info_session_error(self, runner: CliRunner) -> None:
        """When Commence isn't running, we get a ClickException."""
        with patch(
            'pycommence.cli._get_session',
            side_effect=click.ClickException('Cannot connect'),
        ):
            result = runner.invoke(cli, ['info'])
        assert result.exit_code != 0
        assert 'Cannot connect' in result.output


class TestSchemaCommand:
    def test_schema_list_categories(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['schema'])
        assert result.exit_code == 0
        assert 'Contact' in result.output
        assert 'Hire' in result.output
        assert 'Account' in result.output

    def test_schema_category_detail(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['schema', 'Contact'])
        assert result.exit_code == 0
        assert 'contactKey' in result.output
        assert 'emailBusiness' in result.output
        assert 'Is Employed by' in result.output


class TestReadCommand:
    def test_read_basic(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['read', 'Contact'])
        assert result.exit_code == 0
        assert '2 row(s) returned' in result.output

    def test_read_json_format(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['read', 'Contact', '--format', 'json'])
        assert result.exit_code == 0
        data = json.loads(result.output.split('\n', 1)[1])  # skip the "N row(s)" line
        assert len(data) == 2
        assert data[0]['Name'] == 'Alice'

    def test_read_csv_format(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['read', 'Contact', '--format', 'csv'])
        assert result.exit_code == 0
        assert 'Alice' in result.output

    def test_read_with_columns(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['read', 'Contact', '-c', 'Name,Email'])
        assert result.exit_code == 0
        mock_session.query.return_value.columns.assert_called_with('Name', 'Email')

    def test_read_with_filter(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(
                cli,
                [
                    'read',
                    'Contact',
                    '-f',
                    'Name:Contains:Smith',
                ],
            )
        assert result.exit_code == 0
        mock_session.query.return_value.where.assert_called_with(
            'Name',
            'Contains',
            'Smith',
        )

    def test_read_with_limit(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['read', 'Contact', '-l', '5'])
        assert result.exit_code == 0
        mock_session.query.return_value.limit.assert_called_with(5)

    def test_read_canonical(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['read', 'Contact', '--canonical'])
        assert result.exit_code == 0
        mock_session.query.return_value.canonical.assert_called()

    def test_read_multiple_filters(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(
                cli,
                [
                    'read',
                    'Contact',
                    '-f',
                    'Name:Contains:Smith',
                    '-f',
                    'City:Equal To:Boston',
                ],
            )
        assert result.exit_code == 0
        assert mock_session.query.return_value.where.call_count == 2

    def test_read_missing_category(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ['read'])
        assert result.exit_code != 0


class TestCountCommand:
    def test_count_unfiltered(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['count', 'Contact'])
        assert result.exit_code == 0
        assert '25' in result.output
        mock_session.schema.get_row_count.assert_called_with('Contact')

    def test_count_filtered(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(
                cli,
                [
                    'count',
                    'Contact',
                    '-f',
                    'Name:Contains:Smith',
                ],
            )
        assert result.exit_code == 0
        assert '42' in result.output
        mock_session.query.return_value.count.assert_called()


class TestExportCommand:
    def test_export_csv(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['export', 'Contact', 'out.csv'])
        assert result.exit_code == 0
        assert 'Exported' in result.output
        assert '50' in result.output
        mock_session.export.assert_called_once()

    def test_export_with_format(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(
                cli,
                [
                    'export',
                    'Contact',
                    'out.json',
                    '--format',
                    'json',
                ],
            )
        assert result.exit_code == 0
        call_kwargs = mock_session.export.call_args
        assert (
            call_kwargs[1]['format'] == 'json'
            or call_kwargs[0][2] == 'json'
            or 'json' in str(call_kwargs)
        )

    def test_export_with_columns(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(
                cli,
                [
                    'export',
                    'Contact',
                    'out.csv',
                    '-c',
                    'Name,Email',
                ],
            )
        assert result.exit_code == 0
        mock_session.export.assert_called_once()

    def test_export_with_limit(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(
                cli,
                [
                    'export',
                    'Contact',
                    'out.csv',
                    '-l',
                    '100',
                ],
            )
        assert result.exit_code == 0

    def test_export_missing_args(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ['export'])
        assert result.exit_code != 0


class TestBackupCommand:
    def test_backup_all(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['backup', './my_backup'])
        assert result.exit_code == 0
        assert 'Backup complete' in result.output
        assert '3' in result.output  # categories_exported
        assert '135' in result.output  # total_rows

    def test_backup_selected_categories(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(
                cli,
                [
                    'backup',
                    './my_backup',
                    '-c',
                    'Contact,Hire',
                ],
            )
        assert result.exit_code == 0
        mock_session.backup.assert_called_once()

    def test_backup_no_canonical(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(
                cli,
                [
                    'backup',
                    './my_backup',
                    '--no-canonical',
                ],
            )
        assert result.exit_code == 0


class TestImportCommand:
    def test_import_csv(self, runner: CliRunner, mock_session: MagicMock, tmp_path: Path) -> None:
        csv_file = tmp_path / 'data.csv'
        csv_file.write_text('Name,Email\nAlice,a@b.com\n', encoding='utf-8')
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['import', 'Contact', str(csv_file)])
        assert result.exit_code == 0
        assert 'Imported' in result.output
        mock_session.import_csv.assert_called_once()

    def test_import_json(self, runner: CliRunner, mock_session: MagicMock, tmp_path: Path) -> None:
        json_file = tmp_path / 'data.json'
        json_file.write_text('[{"Name": "Alice"}]', encoding='utf-8')
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['import', 'Contact', str(json_file)])
        assert result.exit_code == 0
        assert 'Imported' in result.output
        mock_session.import_json.assert_called_once()

    def test_import_dry_run(
        self, runner: CliRunner, mock_session: MagicMock, tmp_path: Path
    ) -> None:
        mock_session.import_csv.return_value = {
            'rows_parsed': 10,
            'rows_imported': 0,
            'dry_run': True,
        }
        csv_file = tmp_path / 'data.csv'
        csv_file.write_text('Name\nAlice\n', encoding='utf-8')
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['import', 'Contact', str(csv_file), '--dry-run'])
        assert result.exit_code == 0
        assert 'DRY RUN' in result.output

    def test_import_with_limit(
        self, runner: CliRunner, mock_session: MagicMock, tmp_path: Path
    ) -> None:
        csv_file = tmp_path / 'data.csv'
        csv_file.write_text('Name\nAlice\n', encoding='utf-8')
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(
                cli,
                [
                    'import',
                    'Contact',
                    str(csv_file),
                    '-l',
                    '5',
                ],
            )
        assert result.exit_code == 0

    def test_import_unsupported_format(
        self, runner: CliRunner, mock_session: MagicMock, tmp_path: Path
    ) -> None:
        bad_file = tmp_path / 'data.parquet'
        bad_file.write_text('nope', encoding='utf-8')
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['import', 'Contact', str(bad_file)])
        assert result.exit_code != 0
        assert 'Unsupported import format' in result.output

    def test_import_reports_errors(
        self, runner: CliRunner, mock_session: MagicMock, tmp_path: Path
    ) -> None:
        mock_session.import_csv.return_value = {
            'rows_parsed': 3,
            'rows_imported': 2,
            'errors': ['Row 2: duplicate Name'],
        }
        csv_file = tmp_path / 'data.csv'
        csv_file.write_text('Name\nAlice\n', encoding='utf-8')
        with patch('pycommence.cli._get_session', return_value=mock_session):
            result = runner.invoke(cli, ['import', 'Contact', str(csv_file)])
        assert result.exit_code == 0
        assert 'Row 2: duplicate Name' in result.output


class TestGuiCommand:
    def test_gui_import_error(self, runner: CliRunner) -> None:
        """If nicegui is not installed, the GUI command should give a clear error."""
        import sys

        with patch.dict(sys.modules, {'pycommence.gui': None}):
            result = runner.invoke(cli, ['gui'])
        # Should report the missing extra, not traceback
        assert result.exit_code != 0
        assert 'gui' in result.output.lower()

    def test_gui_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ['gui', '--help'])
        assert result.exit_code == 0
        assert 'NiceGUI' in result.output or 'native' in result.output


# ---------------------------------------------------------------------------
# Edge cases & integration-ish
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_session_close_called_on_info(self, runner: CliRunner, mock_session: MagicMock) -> None:
        """Verify session.close() is called even on success."""
        with patch('pycommence.cli._get_session', return_value=mock_session):
            runner.invoke(cli, ['info'])
        mock_session.close.assert_called_once()

    def test_session_close_called_on_read(self, runner: CliRunner, mock_session: MagicMock) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            runner.invoke(cli, ['read', 'Contact'])
        mock_session.close.assert_called_once()

    def test_session_close_called_on_count(
        self, runner: CliRunner, mock_session: MagicMock
    ) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            runner.invoke(cli, ['count', 'Contact'])
        mock_session.close.assert_called_once()

    def test_session_close_called_on_schema(
        self, runner: CliRunner, mock_session: MagicMock
    ) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            runner.invoke(cli, ['schema'])
        mock_session.close.assert_called_once()

    def test_session_close_called_on_export(
        self, runner: CliRunner, mock_session: MagicMock
    ) -> None:
        with patch('pycommence.cli._get_session', return_value=mock_session):
            runner.invoke(cli, ['export', 'Contact', 'out.csv'])
        mock_session.close.assert_called_once()

    def test_read_invalid_format_rejected(self, runner: CliRunner) -> None:
        """--format with an invalid choice should be rejected by Click."""
        result = runner.invoke(cli, ['read', 'Contact', '--format', 'xml'])
        assert result.exit_code != 0
