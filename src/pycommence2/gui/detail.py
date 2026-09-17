"""Record Detail page — view/edit a single row, show connections."""

from __future__ import annotations

from nicegui import ui

from pycommence2.gui.layout import frame, notify_error, notify_success
from pycommence2.gui import state


def register() -> None:
    """Register the detail page routes."""

    @ui.page('/detail/{category}/{row_id}')
    async def detail(category: str, row_id: str) -> None:
        with frame(f'Detail — {category}'):
            if not state.worker or not state.worker.connected:
                ui.label('⚠ Not connected to Commence.')
                return
            await _render_detail(category, row_id)


async def _render_detail(category: str, row_id: str) -> None:
    """Render the record detail view."""
    worker = state.worker
    assert worker is not None

    # Load the row data
    try:
        row = await worker.run(lambda s, c=category, rid=row_id: s.read_by_id(c, rid))
    except Exception as exc:
        notify_error(f'Failed to load row: {exc}')
        return

    # Load field info for type context
    try:
        fields = await worker.run(lambda s, c=category: s.schema.get_fields(c))
    except Exception:
        fields = []

    field_type_map = {f.name: f for f in fields}

    # -- Header info ---------------------------------------------------------
    with ui.row().classes('items-center gap-4'):
        ui.button(
            icon='arrow_back',
            on_click=lambda: ui.navigate.to(f'/browse/{category}'),
        ).props('flat')
        ui.label(category).classes('text-xl font-bold')
        if row.row_id:
            ui.label(f'ID: {row.row_id}').classes('text-sm text-grey')

    # -- Field editor card ---------------------------------------------------
    field_inputs: dict[str, ui.input] = {}

    with ui.card().classes('w-full'):
        ui.label('Fields').classes('text-lg font-bold mb-2')
        with ui.grid(columns=2).classes('gap-x-8 gap-y-2 w-full'):
            for col_name, value in row.columns.items():
                fi = field_type_map.get(col_name)
                type_label = fi.field_type.name if fi else ''

                with ui.row().classes('items-center gap-1'):
                    ui.label(col_name).classes('font-bold text-sm')
                    if type_label:
                        ui.badge(type_label).props('outline dense').classes('text-xs')

                inp = ui.input(
                    value=value,
                    placeholder='(empty)',
                ).classes('w-full')
                inp.props('dense outlined')
                # Disable unless edit mode is on
                if not state.app_state.edit_unlocked:
                    inp.props('disable')
                field_inputs[col_name] = inp

    # -- Save button ---------------------------------------------------------
    async def save_changes() -> None:
        if not state.app_state.edit_unlocked:
            notify_error('Enable Edit mode first (toggle in the header).')
            return
        changes: dict[str, str] = {}
        for col_name, inp in field_inputs.items():
            new_val = inp.value or ''
            old_val = row.columns.get(col_name, '')
            if new_val != old_val:
                changes[col_name] = new_val

        if not changes:
            ui.notify('No changes to save.', type='info')
            return

        try:
            await worker.run(lambda s, c=category, rid=row_id, ch=changes: s.edit(rid, c, ch))
            notify_success(f'Saved {len(changes)} field(s).')
        except Exception as exc:
            notify_error(f'Save failed: {exc}')

    with ui.row().classes('gap-4 mt-4'):
        ui.button('Save Changes', icon='save', on_click=save_changes).props('color=primary').bind_enabled_from(
            state.app_state, 'edit_unlocked'
        )

        # Open in Commence
        async def open_in_commence() -> None:
            pk_field = next((f.name for f in fields if f.field_type.name == 'NAME'), None)
            pk_value = row.columns.get(pk_field, '') if pk_field else ''
            if pk_value:
                try:
                    await worker.run(lambda s, c=category, pk=pk_value: s.dde.show_item(c, pk))
                    notify_success('Opened in Commence.')
                except Exception as exc:
                    notify_error(f'Failed to open in Commence: {exc}')
            else:
                notify_error('Cannot determine item name for DDE show_item.')

        ui.button('Open in Commence', icon='open_in_new', on_click=open_in_commence)

    # -- Connections section --------------------------------------------------
    try:
        connections = await worker.run(lambda s, c=category: s.schema.get_connection_names(c))
    except Exception:
        connections = []

    if connections:
        ui.separator().classes('mt-4')
        ui.label('Connections').classes('text-lg font-bold')

        pk_field = next((f.name for f in fields if f.field_type.name == 'NAME'), None)
        pk_value = row.columns.get(pk_field, '') if pk_field else ''

        if pk_value:
            for conn in connections:
                with ui.expansion(f'{conn.name} → {conn.to_category}', icon='link').classes('w-full'):
                    try:
                        connected_names = await worker.run(
                            lambda s, c=category, pk=pk_value, cn=conn.name, tc=conn.to_category: (
                                s.connections.get_connected_item_names(c, pk, cn, tc)
                            )
                        )
                        if connected_names:
                            for name in connected_names:
                                ui.label(f'  • {name}').classes('text-sm ml-4')
                        else:
                            ui.label('  (none)').classes('text-sm text-grey ml-4')
                    except Exception as exc:
                        ui.label(f'  Error: {exc}').classes('text-sm text-red ml-4')
        else:
            ui.label('Cannot load connections — item name field not found.').classes('text-sm text-grey')
