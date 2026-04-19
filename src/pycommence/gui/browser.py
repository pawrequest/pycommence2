"""Category Browser page — server-side paginated table with filtering."""

from __future__ import annotations

from nicegui import ui

from pycommence.gui.layout import frame, notify_error
from pycommence.gui import state


def register() -> None:
    """Register the browser page routes."""

    @ui.page('/browse')
    async def browse_index() -> None:
        """Category picker — redirect to a specific category."""
        with frame('Browse'):
            if not state.worker or not state.worker.connected:
                ui.label('⚠ Not connected to Commence.')
                return
            try:
                categories = await state.worker.run(lambda s: s.schema.list_categories())
            except Exception as exc:
                notify_error(str(exc))
                return

            ui.label('Select a category to browse:').classes('text-lg')
            select = ui.select(categories, label='Category', with_input=True).classes('w-64')
            select.on_value_change(
                lambda e: ui.navigate.to(f'/browse/{e.value}') if e.value else None
            )

    @ui.page('/browse/{category}')
    async def browse_category(category: str) -> None:
        with frame(f'Browse — {category}'):
            if not state.worker or not state.worker.connected:
                ui.label('⚠ Not connected to Commence.')
                return
            await _render_browser(category)


async def _render_browser(category: str) -> None:
    """Render the full category browser with pagination and filters."""
    worker = state.worker
    assert worker is not None

    # Get field names for column picker
    try:
        field_names: list[str] = await worker.run(lambda s, c=category: s.schema.get_field_names(c))
        total_rows: int = await worker.run(lambda s, c=category: s.schema.get_row_count(c))
    except Exception as exc:
        notify_error(f"Failed to load schema for '{category}': {exc}")
        return

    # State
    page_state = {
        'page': 1,
        'rows_per_page': 25,
        'selected_columns': field_names[:8],  # default to first 8
        'filters': [],
        'sort_field': None,
        'sort_asc': True,
        'total': total_rows,
    }

    # -- Controls row --------------------------------------------------------
    with ui.row().classes('w-full items-end gap-4 flex-wrap'):
        col_select = (
            ui.select(
                field_names,
                label='Columns',
                multiple=True,
                value=page_state['selected_columns'],
            )
            .classes('w-96')
            .props('use-chips')
        )

        ui.label(f'{total_rows:,} total rows').classes('text-sm text-grey')

    # -- Filter builder ------------------------------------------------------
    with ui.expansion('Filters', icon='filter_alt').classes('w-full'):
        filter_rows_container = ui.column().classes('gap-2 w-full')
        with filter_rows_container:
            _filter_ui = _FilterBuilder(field_names)

    # -- Results table -------------------------------------------------------
    table_container = ui.column().classes('w-full')
    table_ref: dict = {'tbl': None, 'loaded_cols': set()}

    def _make_columns_def(cols: list[str]) -> list[dict]:
        return [
            {'name': c, 'label': c, 'field': c, 'align': 'left', 'sortable': True} for c in cols
        ]

    async def refresh_data() -> None:
        """Fetch data from Commence and rebuild the table."""
        table_container.clear()
        table_ref['tbl'] = None
        cols = col_select.value or field_names[:8]
        page_state['selected_columns'] = cols

        # Build filter strings
        filters = _filter_ui.build_filters()

        try:
            rows = await worker.run(
                lambda s, c=category, cl=list(cols), f=filters: s.read(
                    c,
                    columns=cl,
                    filters=f if f else None,
                    max_rows=page_state['rows_per_page'],
                    canonical=False,
                )
            )
        except Exception as exc:
            with table_container:
                ui.label(f'Error: {exc}').classes('text-red')
            return

        row_dicts = []
        for r in rows:
            d = r.to_dict()
            d['__row_id'] = r.row_id
            row_dicts.append(d)

        table_ref['loaded_cols'] = set(cols)

        with table_container:
            if not row_dicts:
                ui.label('No rows found.').classes('text-grey')
                return

            tbl = ui.table(
                columns=_make_columns_def(cols),
                rows=row_dicts,
                row_key='__row_id',
                pagination={'rowsPerPage': page_state['rows_per_page']},
            ).classes('w-full')
            tbl.on(
                'row-click',
                lambda e: _navigate_to_detail(category, e.args[1].get('__row_id')),
            )
            table_ref['tbl'] = tbl

    async def _on_columns_changed(_) -> None:
        """Update visible columns client-side; re-query only if new columns were added."""
        cols = col_select.value or field_names[:8]
        tbl = table_ref.get('tbl')
        if tbl is None:
            # No table yet — do a full fetch
            await refresh_data()
            return

        # If user selected columns we don't have data for, re-query
        if set(cols) - table_ref.get('loaded_cols', set()):
            await refresh_data()
            return

        # All selected columns already in loaded data — just update visibility
        tbl.columns = _make_columns_def(cols)
        tbl.update()

    col_select.on_value_change(_on_columns_changed)
    ui.button('Load / Refresh', icon='refresh', on_click=refresh_data).props('color=primary')

    # Initial load
    await refresh_data()


def _navigate_to_detail(category: str, row_id: str | None) -> None:
    """Navigate to record detail page."""
    if row_id:
        ui.navigate.to(f'/detail/{category}/{row_id}')


class _FilterBuilder:
    """Interactive filter clause builder (up to 4 clauses)."""

    def __init__(self, field_names: list[str]) -> None:
        self._field_names = field_names
        self._clauses: list[dict] = []

        self._qualifiers = [
            'Equal To',
            'Not Equal To',
            'Contains',
            'Not Contains',
            'After',
            'Before',
            'Between',
            'Blank',
            'Not Blank',
            'Checked',
            'Not Checked',
        ]

        with ui.row().classes('gap-2 items-end'):
            self._field_input = ui.select(
                field_names,
                label='Field',
                with_input=True,
            ).classes('w-48')
            self._qual_input = ui.select(
                self._qualifiers,
                label='Qualifier',
            ).classes('w-40')
            self._value_input = ui.input(label='Value').classes('w-48')
            ui.button('Add', icon='add', on_click=self._add_clause).props('dense')

        self._clauses_display = ui.column().classes('gap-1')

    def _add_clause(self) -> None:
        field = self._field_input.value
        qual = self._qual_input.value
        value = self._value_input.value or ''
        if not field or not qual:
            ui.notify('Select a field and qualifier', type='warning')
            return
        if len(self._clauses) >= 4:
            ui.notify('Maximum 4 filter clauses', type='warning')
            return

        clause_num = len(self._clauses) + 1
        clause_str = f'[ViewFilter({clause_num}, F, , "{field}", "{qual}", "{value}", False)]'
        self._clauses.append(
            {
                'field': field,
                'qual': qual,
                'value': value,
                'str': clause_str,
            }
        )
        self._render_clauses()

    def _render_clauses(self) -> None:
        self._clauses_display.clear()
        with self._clauses_display:
            for i, c in enumerate(self._clauses):
                with ui.row().classes('items-center gap-2'):
                    ui.label(f'{i + 1}. {c["field"]} {c["qual"]} {c["value"]!r}').classes('text-sm')
                    ui.button(
                        icon='close',
                        on_click=lambda _, idx=i: self._remove_clause(idx),
                    ).props('dense flat size=xs')

    def _remove_clause(self, idx: int) -> None:
        self._clauses.pop(idx)
        # Re-number
        for i, c in enumerate(self._clauses):
            field, qual, value = c['field'], c['qual'], c['value']
            c['str'] = f'[ViewFilter({i + 1}, F, , "{field}", "{qual}", "{value}", False)]'
        self._render_clauses()

    def build_filters(self) -> list[str]:
        """Return the current filter strings."""
        return [c['str'] for c in self._clauses]
