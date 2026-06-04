"""Category Browser page — server-side paginated table with filtering."""

from __future__ import annotations

from typing import Callable

from nicegui import ui

from pycommence.gui.layout import frame, notify_error
from pycommence.gui import state
from pycommence.query import QueryBuilder

_BATCH_SIZE = 50


# ---------------------------------------------------------------------------
# Query helper
# ---------------------------------------------------------------------------

def make_and_execute_q(session, category, columns, filter_builder_, batch_size, offset=0):
    """Run on the COM thread: fetch *batch_size* rows starting at *offset*."""
    qb: QueryBuilder = (
        session.query(category)
        .columns(*columns)
        .limit(batch_size)
        .with_ids(True)
    ).apply_settings()
    filter_builder_.apply_to(qb)
    rows = []
    for r in qb.execute(resolve=False, offset=offset):
        d = r.to_dict()
        d['__row_id'] = r.row_id
        rows.append(d)
    return rows


# ---------------------------------------------------------------------------
# Public reusable component
# ---------------------------------------------------------------------------

async def build_category_table(
    category: str,
    *,
    default_columns: list[str] | None = None,
    batch_size: int = _BATCH_SIZE,
    on_row_click: Callable | None = None,
) -> None:
    """Render a filterable, lazily-loaded infinite-scroll Commence table.

    Fetches the first *batch_size* rows immediately, then fetches the next
    batch automatically whenever the user scrolls near the bottom.

    Args:
        category: Commence category name.
        default_columns: Columns shown initially (default: first 8).
        batch_size: Rows fetched per COM call (default 50).
        on_row_click: Optional ``callable(category, row_id)`` called on row click.
    """
    worker = state.worker
    assert worker is not None

    try:
        field_names: list[str] = await worker.run(
            lambda s, c=category: s.schema.get_field_names(c)
        )
        total_rows: int = await worker.run(
            lambda s, c=category: s.schema.get_row_count(c)
        )
    except Exception as exc:
        notify_error(f"Failed to load schema for '{category}': {exc}")
        return

    selected_cols = default_columns or field_names[:8]

    # -- Controls --------------------------------------------------------
    with ui.row().classes('w-full items-end gap-4 flex-wrap'):
        filter_builder = FilterBuilder(field_names)
        col_select = (
            ui.select(
                field_names,
                label='Columns',
                multiple=True,
                value=list(selected_cols),
            )
            .classes('w-80')
            .props('use-chips')
        )
        ui.label(f'{total_rows:,} total rows').classes('text-sm text-grey self-center')

    with ui.row().classes('items-center gap-2 flex-wrap'):
        ui.button('Load / Refresh', icon='refresh',
                  on_click=lambda: ui.timer(0, refresh_data, once=True)
                  ).props('color=primary dense')

    # -- Results table -------------------------------------------------------
    table_container = ui.column().classes('w-full')

    # Mutable load state shared between refresh_data and _fetch_and_append
    load_state: dict = {
        'tbl': None,
        'loaded_cols': set(),
        'offset': 0,
        'exhausted': False,
        'fetching': False,
        'status_label': None,
        'load_more_btn': None,
    }

    def _col_defs(cols: list[str]) -> list[dict]:
        return [
            {'name': c, 'label': c, 'field': c, 'align': 'left', 'sortable': True}
            for c in cols
        ]

    async def _fetch_and_append(cols: list[str]) -> None:
        """Fetch the next batch at the current offset and append to the table."""
        if load_state['fetching'] or load_state['exhausted']:
            return
        load_state['fetching'] = True
        try:
            batch: list[dict] = await worker.run(
                make_and_execute_q, category, cols, filter_builder,
                batch_size, load_state['offset'],
            )
        except Exception as exc:
            notify_error(f'Fetch error: {exc}')
            return
        finally:
            load_state['fetching'] = False

        if not batch:
            load_state['exhausted'] = True
            if load_state['status_label']:
                load_state['status_label'].set_text(
                    f'{load_state["offset"]:,} rows — all loaded'
                )
            if load_state['load_more_btn']:
                load_state['load_more_btn'].set_visibility(False)
            return

        tbl = load_state['tbl']
        if tbl is not None:
            tbl.add_rows(batch)

        load_state['offset'] += len(batch)
        if load_state['status_label']:
            load_state['status_label'].set_text(
                f'{load_state["offset"]:,} rows loaded'
                + ('' if load_state['offset'] < total_rows else ' — all loaded')
            )
        if len(batch) < batch_size:
            load_state['exhausted'] = True
            if load_state['load_more_btn']:
                load_state['load_more_btn'].set_visibility(False)

    async def refresh_data() -> None:
        """Reset and load the first batch."""
        table_container.clear()
        load_state.update(tbl=None, loaded_cols=set(), offset=0,
                          exhausted=False, fetching=False, status_label=None,
                          load_more_btn=None)
        cols = list(col_select.value or selected_cols)

        # First batch
        try:
            first_batch: list[dict] = await worker.run(
                make_and_execute_q, category, cols, filter_builder, batch_size, 0,
            )
        except Exception as exc:
            with table_container:
                ui.label(f'Error: {exc}').classes('text-red')
            return

        load_state['loaded_cols'] = set(cols)

        with table_container:
            if not first_batch:
                ui.label('No rows found.').classes('text-grey')
                return

            status = ui.label(f'{len(first_batch):,} rows loaded').classes('text-sm text-grey')
            load_state['status_label'] = status
            load_state['offset'] = len(first_batch)
            if len(first_batch) < batch_size:
                load_state['exhausted'] = True

            tbl = (
                ui.table(
                    columns=_col_defs(cols),
                    rows=first_batch,
                    row_key='__row_id',
                )
                .classes('w-full')
                .props('flat bordered virtual-scroll')
                .style('max-height: 70vh')
            )
            load_state['tbl'] = tbl

            if on_row_click:
                tbl.on(
                    'row-click',
                    lambda e: on_row_click(category, e.args[1].get('__row_id')),
                )

            # Sentinel div — IntersectionObserver fires load_more when it scrolls into view
            sentinel = ui.element('div').style('height:1px')
            load_more_btn = (
                ui.button('Load more', icon='expand_more',
                          on_click=lambda: ui.timer(0, lambda: _fetch_and_append(cols), once=True))
                .props('flat dense')
                .classes('w-full')
            )
            load_state['load_more_btn'] = load_more_btn

            # Wire IntersectionObserver to the sentinel inside the virtual-scroll container
            await ui.run_javascript(f'''
                (function() {{
                    const sentinel = document.getElementById('{sentinel.id}');
                    if (!sentinel) return;
                    const observer = new IntersectionObserver((entries) => {{
                        if (entries[0].isIntersecting) {{
                            emitEvent('{sentinel.id}', 'sentinel_visible', {{}});
                        }}
                    }}, {{ threshold: 0.1 }});
                    observer.observe(sentinel);
                }})();
            ''')

            async def _on_sentinel_visible(_e) -> None:
                await _fetch_and_append(cols)

            sentinel.on('sentinel_visible', _on_sentinel_visible)

    async def _on_columns_changed(_) -> None:
        cols = list(col_select.value or selected_cols)
        tbl = load_state.get('tbl')
        if tbl is None or set(cols) - load_state.get('loaded_cols', set()):
            await refresh_data()
            return
        tbl.columns = _col_defs(cols)
        tbl.update()

    col_select.on_value_change(_on_columns_changed)

    await refresh_data()


# ---------------------------------------------------------------------------
# Filter builder — inline, decoupled from raw DDE strings
# ---------------------------------------------------------------------------

class FilterBuilder:
    """Inline filter clause builder (up to 4 clauses).

    Renders field / qualifier / value inputs in a single row.
    Added clauses appear as removable chips below.
    Call :meth:`apply_to` to fluently attach clauses to any
    :class:`~pycommence.query.QueryBuilder`.
    """

    _QUALIFIERS = [
        'Equal To', 'Not Equal To', 'Contains', 'Not Contains',
        'After', 'Before', 'Between', 'Blank', 'Not Blank',
        'Checked', 'Not Checked',
    ]

    def __init__(self, field_names: list[str]) -> None:
        self._field_names = field_names
        self._clauses: list[tuple[str, str, str]] = []  # (field, qualifier, value)

        with ui.row().classes('gap-2 items-end flex-wrap'):
            self._field_input = ui.select(
                field_names, label='Filter field', with_input=True
            ).classes('w-48')
            self._qual_input = ui.select(
                self._QUALIFIERS, label='Qualifier'
            ).classes('w-40')
            self._value_input = ui.input(label='Value').classes('w-40')
            ui.button('Add filter', icon='add', on_click=self._add_clause).props('dense outline')

        self._display = ui.row().classes('gap-2 flex-wrap items-center')

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
        self._clauses.append((field, qual, value))
        self._value_input.set_value('')
        self._render()

    def _render(self) -> None:
        self._display.clear()
        with self._display:
            for i, (f, q, v) in enumerate(self._clauses):
                label = f'{f} {q}' + (f' "{v}"' if v else '')
                with ui.chip(label, icon='filter_alt', removable=True).props('outline color=primary') as chip:
                    chip.on('remove', lambda _, idx=i: self._remove(idx))

    def _remove(self, idx: int) -> None:
        self._clauses.pop(idx)
        self._render()

    def apply_to(self, qb: QueryBuilder) -> QueryBuilder:
        """Fluently apply all clauses to *qb* and return it."""
        for field, qualifier, value in self._clauses:
            qb = qb.where(field, qualifier, value)
        return qb


# ---------------------------------------------------------------------------
# Page registration
# ---------------------------------------------------------------------------

def register() -> None:
    """Register the browser page routes."""

    @ui.page('/browse')
    async def browse_index() -> None:
        """Category picker landing page."""
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

            # Category switcher always visible at the top
            try:
                categories = await state.worker.run(lambda s: s.schema.list_categories())
            except Exception as exc:
                notify_error(str(exc))
                return

            with ui.row().classes('items-center gap-4 w-full'):
                cat_select = ui.select(
                    categories,
                    value=category,
                    label='Category',
                    with_input=True,
                ).classes('w-64')
                cat_select.on_value_change(
                    lambda e: ui.navigate.to(f'/browse/{e.value}') if e.value else None
                )

            await build_category_table(
                category,
                on_row_click=lambda cat, row_id: ui.navigate.to(f'/detail/{cat}/{row_id}'),
            )
