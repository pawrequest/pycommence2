"""CLI for pycommence — powered by click + rich.

Install with::

    pip install pycommence[cli]

Usage::

    pycommence info
    pycommence schema
    pycommence schema Contact
    pycommence read Hire --limit 20 --format table
    pycommence count Hire --filter "Name:Contains:Smith"
"""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import TYPE_CHECKING

try:
    import click
except ImportError:
    raise SystemExit(
        "The CLI requires the 'cli' extra.  Install with:\n  pip install pycommence[cli]"
    )

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    raise SystemExit(
        "The CLI requires the 'cli' extra.  Install with:\n  pip install pycommence[cli]"
    )

if TYPE_CHECKING:
    from pycommence.models import RowResult
    from pycommence.session import CommenceSession

log = logging.getLogger(__name__)
console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_session() -> 'CommenceSession':
    """Create a CommenceSession, converting errors to ClickException."""
    from pycommence.exceptions import CommenceNotFoundError
    from pycommence.session import CommenceSession

    try:
        return CommenceSession()
    except CommenceNotFoundError as exc:
        raise click.ClickException(
            f'Cannot connect to Commence: {exc}\n'
            'Make sure Commence is running with a database open.'
        )


def _parse_filter(raw: str) -> tuple[str, str, str]:
    """Parse ``"Field:Qualifier:Value"`` into a 3-tuple.

    The value portion may itself contain colons, so we split on the
    first two colons only.
    """
    parts = raw.split(':', 2)
    if len(parts) < 2:
        raise click.BadParameter(f"Filter must be 'FIELD:QUALIFIER:VALUE', got: {raw!r}")
    field = parts[0].strip()
    qualifier = parts[1].strip()
    value = parts[2].strip() if len(parts) > 2 else ''
    return field, qualifier, value


# ---------------------------------------------------------------------------
# Output renderers
# ---------------------------------------------------------------------------


def _render_table(rows: list['RowResult']) -> None:
    """Render rows as a rich table to the console."""
    if not rows:
        console.print('[dim]No rows returned.[/dim]')
        return
    table = Table(show_lines=False, row_styles=['', 'dim'])
    cols = list(rows[0].columns.keys())
    for col in cols:
        table.add_column(col, overflow='fold')
    for row in rows:
        table.add_row(*(row.get(c, '') for c in cols))
    console.print(table)


def _render_json(rows: list['RowResult']) -> None:
    """Render rows as JSON array to stdout."""
    data = [r.to_dict() for r in rows]
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def _render_csv(rows: list['RowResult']) -> None:
    """Render rows as CSV to stdout."""
    if not rows:
        return
    cols = list(rows[0].columns.keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow(row.to_dict())
    click.echo(buf.getvalue(), nl=False)


RENDERERS = {
    'table': _render_table,
    'json': _render_json,
    'csv': _render_csv,
}


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
@click.option('-v', '--verbose', is_flag=True, help='Enable debug logging.')
def cli(verbose: bool) -> None:
    """pycommence — Commence database tools from the command line."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='%(name)s: %(message)s')


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


@cli.command()
def info() -> None:
    """Show database name, path, version, and shared status."""
    session = _get_session()
    try:
        table = Table(title='Commence Database', show_header=False)
        table.add_column('Property', style='bold')
        table.add_column('Value')
        table.add_row('Name', session.db_name)
        table.add_row('Path', session.db_path)
        table.add_row('Version', session.db_version)
        table.add_row('Shared', 'Yes' if session.db_shared else 'No')
        console.print(table)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


@cli.command()
@click.argument('category', required=False)
def schema(category: str | None) -> None:
    """List categories, or show fields/connections for CATEGORY."""
    session = _get_session()
    try:
        if category is None:
            _show_category_list(session)
        else:
            _show_category_detail(session, category)
    finally:
        session.close()


def _show_category_list(session: 'CommenceSession') -> None:
    """Print all category names with row counts."""
    cats = session.schema.list_categories()
    table = Table(title=f'Categories ({len(cats)})')
    table.add_column('#', justify='right', style='dim')
    table.add_column('Category')
    table.add_column('Rows', justify='right')
    for i, name in enumerate(cats, 1):
        try:
            count = session.schema.get_row_count(name)
        except Exception:
            count = -1
        table.add_row(str(i), name, str(count))
    console.print(table)


def _show_category_detail(session: 'CommenceSession', category: str) -> None:
    """Print fields and connections for a single category."""
    # Fields
    fields = session.schema.get_fields(category)
    ft = Table(title=f'Fields — {category} ({len(fields)})')
    ft.add_column('#', justify='right', style='dim')
    ft.add_column('Field')
    ft.add_column('Type')
    ft.add_column('Max Chars', justify='right')
    ft.add_column('Flags')
    for i, f in enumerate(fields, 1):
        flags = []
        if f.is_mandatory:
            flags.append('mandatory')
        if f.is_combo:
            flags.append('combo')
        if f.is_shared:
            flags.append('shared')
        if f.is_recurring:
            flags.append('recurring')
        ft.add_row(
            str(i),
            f.name,
            f.field_type.name,
            str(f.max_chars) if f.max_chars else '',
            ', '.join(flags) if flags else '',
        )
    console.print(ft)

    # Connections
    conns = session.schema.get_connection_names(category)
    if conns:
        ct = Table(title=f'Connections — {category} ({len(conns)})')
        ct.add_column('#', justify='right', style='dim')
        ct.add_column('Connection')
        ct.add_column('To Category')
        for i, c in enumerate(conns, 1):
            ct.add_row(str(i), c.name, c.to_category)
        console.print(ct)
    else:
        console.print(f'[dim]No connections for {category}.[/dim]')

    # Row count
    row_count = session.schema.get_row_count(category)
    console.print(f'\n[bold]{row_count:,}[/bold] rows in {category}')


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


@cli.command()
@click.argument('category')
@click.option('-c', '--columns', default=None, help='Comma-separated column names to include.')
@click.option(
    '-f',
    '--filter',
    'filters',
    multiple=True,
    help="Filter as 'FIELD:QUALIFIER:VALUE' (repeatable).",
)
@click.option(
    '-l', '--limit', default=50, show_default=True, type=int, help='Maximum rows to return.'
)
@click.option(
    '--format',
    'fmt',
    default='table',
    type=click.Choice(['table', 'json', 'csv'], case_sensitive=False),
    show_default=True,
    help='Output format.',
)
@click.option(
    '--canonical', is_flag=True, help='Use canonical (locale-independent) data formatting.'
)
def read(
    category: str,
    columns: str | None,
    filters: tuple[str, ...],
    limit: int,
    fmt: str,
    canonical: bool,
) -> None:
    """Read rows from CATEGORY."""
    session = _get_session()
    try:
        qb = session.query(category)

        if columns:
            qb.columns(*[c.strip() for c in columns.split(',')])

        for raw_f in filters:
            field, qual, value = _parse_filter(raw_f)
            qb.where(field, qual, value)

        if canonical:
            qb.canonical()

        qb.limit(limit)
        rows = qb.execute()

        console.print(f'[dim]{len(rows)} row(s) returned[/dim]\n')
        RENDERERS[fmt](rows)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


@cli.command()
@click.argument('category')
@click.option(
    '-f',
    '--filter',
    'filters',
    multiple=True,
    help="Filter as 'FIELD:QUALIFIER:VALUE' (repeatable).",
)
def count(category: str, filters: tuple[str, ...]) -> None:
    """Count rows in CATEGORY (optionally filtered)."""
    session = _get_session()
    try:
        if not filters:
            n = session.schema.get_row_count(category)
        else:
            qb = session.query(category)
            for raw_f in filters:
                field, qual, value = _parse_filter(raw_f)
                qb.where(field, qual, value)
            n = qb.count()
        console.print(f'[bold]{n:,}[/bold] rows in {category}')
    finally:
        session.close()


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


@cli.command()
@click.argument('category')
@click.argument('outfile')
@click.option('-c', '--columns', default=None, help='Comma-separated column names to include.')
@click.option(
    '-f',
    '--filter',
    'filters',
    multiple=True,
    help="Filter as 'FIELD:QUALIFIER:VALUE' (repeatable).",
)
@click.option(
    '-l', '--limit', default=50_000, show_default=True, type=int, help='Maximum rows to export.'
)
@click.option(
    '--format',
    'fmt',
    default=None,
    type=click.Choice(['csv', 'json', 'excel'], case_sensitive=False),
    help='Output format (auto-detected from extension if omitted).',
)
@click.option(
    '--canonical/--no-canonical',
    default=True,
    show_default=True,
    help='Use canonical (locale-independent) data formatting.',
)
def export(
    category: str,
    outfile: str,
    columns: str | None,
    filters: tuple[str, ...],
    limit: int,
    fmt: str | None,
    canonical: bool,
) -> None:
    """Export CATEGORY to OUTFILE (CSV, JSON, or Excel).

    Format is auto-detected from the file extension (.csv, .json, .xlsx)
    unless --format is specified.

    \b
    Examples:
        pycommence export Contact contacts.csv
        pycommence export Hire hires.json --limit 1000
        pycommence export Account data.xlsx --columns "Name,Email,Phone"
    """
    session = _get_session()
    try:
        col_list = [c.strip() for c in columns.split(',')] if columns else None
        filter_strs = None
        if filters:
            qb = session.query(category)
            for raw_f in filters:
                field, qual, value = _parse_filter(raw_f)
                qb.where(field, qual, value)
            filter_strs = qb._filters  # noqa: SLF001

        count = session.export(
            category,
            outfile,
            format=fmt,
            columns=col_list,
            filters=filter_strs,
            max_rows=limit,
            canonical=canonical,
        )
        console.print(
            f'[bold green]✓[/bold green] Exported [bold]{count:,}[/bold] rows '
            f'from {category} → {outfile}'
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# backup
# ---------------------------------------------------------------------------


@cli.command()
@click.argument('output_dir')
@click.option(
    '-c', '--categories', default=None, help='Comma-separated category names (default: all).'
)
@click.option(
    '-l', '--limit', default=50_000, show_default=True, type=int, help='Maximum rows per category.'
)
@click.option(
    '--canonical/--no-canonical',
    default=True,
    show_default=True,
    help='Use canonical data formatting.',
)
def backup(
    output_dir: str,
    categories: str | None,
    limit: int,
    canonical: bool,
) -> None:
    """Backup categories to OUTPUT_DIR with schema metadata.

    Creates a directory of JSON files (one per category) plus a
    _schema.json sidecar with field and connection definitions.

    \b
    Examples:
        pycommence backup ./my_backup
        pycommence backup ./partial --categories "Contact,Hire"
    """
    session = _get_session()
    try:
        cat_list = [c.strip() for c in categories.split(',')] if categories else None
        stats = session.backup(
            output_dir,
            categories=cat_list,
            max_rows_per_category=limit,
            canonical=canonical,
        )
        console.print(
            f'[bold green]✓[/bold green] Backup complete: '
            f'[bold]{stats["categories_exported"]}[/bold] categories, '
            f'[bold]{stats["total_rows"]:,}[/bold] rows → {output_dir}'
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# import (load)
# ---------------------------------------------------------------------------


@cli.command(name='import')
@click.argument('category')
@click.argument('infile')
@click.option('--dry-run', is_flag=True, help='Parse and validate without writing data.')
@click.option('-l', '--limit', default=None, type=int, help='Maximum rows to import.')
def import_cmd(
    category: str,
    infile: str,
    dry_run: bool,
    limit: int | None,
) -> None:
    """Import rows from INFILE into CATEGORY.

    Supports CSV (.csv) and JSON (.json) files.

    \b
    Examples:
        pycommence import Contact contacts.csv
        pycommence import Hire hires.json --dry-run
        pycommence import Account data.csv --limit 100
    """
    from pathlib import Path

    ext = Path(infile).suffix.lower()
    session = _get_session()
    try:
        if ext == '.csv':
            result = session.import_csv(
                category,
                infile,
                max_rows=limit,
                dry_run=dry_run,
            )
        elif ext == '.json':
            result = session.import_json(
                category,
                infile,
                max_rows=limit,
                dry_run=dry_run,
            )
        else:
            raise click.ClickException(f"Unsupported import format: '{ext}'. Use .csv or .json.")

        if dry_run:
            console.print(
                f'[bold yellow]DRY RUN[/bold yellow]: parsed '
                f'[bold]{result["rows_parsed"]}[/bold] rows from {infile} '
                f'(no data written)'
            )
        else:
            console.print(
                f'[bold green]✓[/bold green] Imported '
                f'[bold]{result["rows_imported"]}[/bold]/'
                f'{result["rows_parsed"]} rows into {category}'
            )
            errors = result.get('errors', [])
            if errors:
                for err in errors:  # type: ignore[union-attr]
                    console.print(f'  [red]✗[/red] {err}')
    finally:
        session.close()


# ---------------------------------------------------------------------------
# mcp
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    '--read-only', is_flag=True, help='Disable write tools (add, edit, delete, connections).'
)
@click.option(
    '--transport',
    default='stdio',
    type=click.Choice(['stdio', 'sse'], case_sensitive=False),
    show_default=True,
    help='MCP transport protocol.',
)
@click.option('--port', default=8000, type=int, show_default=True, help='Port for SSE transport.')
def mcp(read_only: bool, transport: str, port: int) -> None:
    """Start the MCP server for LLM agent access to Commence.

    Exposes Commence database operations as MCP tools over stdio or SSE.

    Requires the ``mcp`` extra::

        pip install pycommence[mcp]

    \b
    Examples:
        pycommence mcp
        pycommence mcp --read-only
        pycommence mcp --transport sse --port 9000
    """
    try:
        from pycommence.mcp_server import _build_server, _check_mcp_installed
    except ImportError:
        raise click.ClickException(
            "The MCP server requires the 'mcp' extra.  Install with:\n  pip install pycommence[mcp]"
        )

    _check_mcp_installed()
    server = _build_server(read_only=read_only)

    console.print(
        f'[bold green]▶[/bold green] Starting MCP server '
        f'(transport={transport}, read_only={read_only})'
    )

    if transport == 'stdio':
        server.run(transport='stdio')
    else:
        server.run(transport='sse', port=port)


# ---------------------------------------------------------------------------
# gui
# ---------------------------------------------------------------------------


@cli.command()
@click.option('--no-native', is_flag=True, help='Run as a web app instead of a native window.')
@click.option('--port', default=0, type=int, help='Server port (0 = auto).')
@click.option('--reload', is_flag=True, help='Enable hot-reload (for development).')
def gui(no_native: bool, port: int, reload: bool) -> None:
    """Launch the NiceGUI desktop frontend.

    Opens a native desktop window with a full GUI for browsing,
    searching, exporting, and managing Commence data.

    Requires the ``gui`` extra::

        pip install pycommence[gui]
    """
    try:
        from pycommence.gui import run as gui_run
    except ImportError:
        raise click.ClickException(
            "The GUI requires the 'gui' extra.  Install with:\n  pip install pycommence[gui]"
        )

    gui_run(
        native=not no_native,
        port=port,
        reload=reload,
    )


if __name__ == '__main__':
    cli()
