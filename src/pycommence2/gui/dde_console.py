"""DDE Console page — raw DDE request/execute with response display."""

from __future__ import annotations

from nicegui import ui

from pycommence2.gui.layout import frame, notify_error
from pycommence2.gui import state


def register() -> None:
    """Register the DDE console page routes."""

    @ui.page('/dde')
    async def dde_page() -> None:
        with frame('DDE Console'):
            if not state.worker or not state.worker.connected:
                ui.label('⚠ Not connected to Commence.')
                return
            _render_dde_console()


def _render_dde_console() -> None:
    """Render the DDE console UI."""
    ui.label('DDE Console').classes('text-xl font-bold')
    ui.label(
        'Send raw DDE Request or Execute commands to the Commence database. '
        'Power-user tool — use with care.'
    ).classes('text-sm text-grey')

    # -- Command input -------------------------------------------------------
    with ui.card().classes('w-full'):
        cmd_input = (
            ui.textarea(
                label='DDE Command',
                placeholder='[GetCategoryNames("|")]',
            )
            .classes('w-full font-mono')
            .props('rows=3')
        )

        # Response area
        response_area = ui.code('').classes('w-full mt-2')

    # -- Quick templates -----------------------------------------------------
    with ui.expansion('Quick Templates', icon='bolt').classes('w-full'):
        templates = [
            ('[GetCategoryNames("|")]', 'List all categories'),
            ('[GetCategoryCount()]', 'Get category count'),
            ('[GetFieldNames("Contact", "|")]', 'List Contact fields'),
            ('[GetFieldCount("Contact")]', 'Contact field count'),
            ('[GetConnectionNames("Contact", "|", "::")]', 'Contact connections'),
            ('[GetItemCount("Contact")]', 'Contact item count'),
        ]
        with ui.column().classes('gap-1'):
            for tmpl, desc in templates:
                with ui.row().classes('items-center gap-2'):
                    ui.button(
                        'Use',
                        on_click=lambda _, t=tmpl: cmd_input.set_value(t),
                    ).props('dense flat size=sm')
                    ui.label(f'{desc}:').classes('text-sm font-bold w-40')
                    ui.label(tmpl).classes('text-xs font-mono text-grey')

    # -- Request / Execute buttons -------------------------------------------
    async def do_request() -> None:
        cmd = cmd_input.value
        if not cmd:
            notify_error('Enter a DDE command.')
            return
        try:
            result = await state.worker.run(
                lambda s, c=cmd: s._schema._conv.request(c)  # noqa: SLF001
            )
            response_area.set_content(result)
        except Exception as exc:
            response_area.set_content(f'ERROR: {exc}')

    async def do_execute() -> None:
        cmd = cmd_input.value
        if not cmd:
            notify_error('Enter a DDE command.')
            return
        try:
            await state.worker.run(
                lambda s, c=cmd: s._schema._conv.execute(c)  # noqa: SLF001
            )
            response_area.set_content('OK (no return value for Execute commands)')
        except Exception as exc:
            response_area.set_content(f'ERROR: {exc}')

    with ui.row().classes('gap-4 mt-4'):
        ui.button('Request', icon='send', on_click=do_request).props('color=primary')
        ui.button('Execute', icon='play_arrow', on_click=do_execute).props('color=secondary')
        ui.button(
            'Clear',
            icon='clear',
            on_click=lambda: response_area.set_content(''),
        ).props('flat')
