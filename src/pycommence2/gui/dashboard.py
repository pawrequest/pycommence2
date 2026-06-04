"""Dashboard page — DB overview and category quick-nav."""

from __future__ import annotations

from nicegui import ui

from pycommence2.gui.layout import frame, notify_error
from pycommence2.gui import state


def register() -> None:
    """Register the dashboard page routes."""

    @ui.page('/')
    async def index() -> None:
        with frame('Dashboard'):
            if not state.worker or not state.worker.connected:
                ui.label('⚠ Not connected to Commence.').classes('text-lg text-red')
                if state.worker and state.worker.startup_error:
                    ui.label(str(state.worker.startup_error)).classes('text-sm text-grey')
                return

            await _render_dashboard()


async def _render_dashboard() -> None:
    """Render the dashboard content."""
    worker = state.worker
    assert worker is not None

    # DB info card
    try:
        info = await worker.run(
            lambda s: {
                'name': s.db_name,
                'path': s.db_path,
                'version': s.db_version,
                'shared': s.db_shared,
            }
        )
    except Exception as exc:
        notify_error(f'Failed to get DB info: {exc}')
        return

    with ui.card().classes('w-full'):
        ui.label('Database').classes('text-xl font-bold')
        with ui.grid(columns=2).classes('gap-2'):
            ui.label('Name').classes('font-bold')
            ui.label(info['name'])
            ui.label('Path').classes('font-bold')
            ui.label(info['path'])
            ui.label('Version').classes('font-bold')
            ui.label(info['version'])
            ui.label('Shared').classes('font-bold')
            ui.label('Yes' if info['shared'] else 'No')

    # Category list with row counts
    ui.label('Categories').classes('text-xl font-bold mt-4')

    try:
        categories = await worker.run(lambda s: s.schema.list_categories())
    except Exception as exc:
        notify_error(f'Failed to list categories: {exc}')
        return

    # Fetch row counts in parallel-ish (but all go through COM worker serially)
    cat_data: list[dict[str, object]] = []
    for cat_name in categories:
        try:
            count = await worker.run(lambda s, c=cat_name: s.schema.get_row_count(c))
        except Exception:
            count = -1
        cat_data.append({'name': cat_name, 'rows': count})

    columns = [
        {'name': 'name', 'label': 'Category', 'field': 'name', 'align': 'left', 'sortable': True},
        {'name': 'rows', 'label': 'Rows', 'field': 'rows', 'align': 'right', 'sortable': True},
    ]

    table = ui.table(
        columns=columns,
        rows=cat_data,
        row_key='name',
        pagination={'rowsPerPage': 25, 'sortBy': 'name'},
    ).classes('w-full')
    table.on('row-click', lambda e: _navigate_to_category(e.args[1]['name']))

    ui.label('Click a category to browse its data.').classes('text-sm text-grey')


def _navigate_to_category(name: str) -> None:
    """Navigate to the category browser page."""
    ui.navigate.to(f'/browse/{name}')
