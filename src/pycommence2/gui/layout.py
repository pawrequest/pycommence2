"""Shared page layout — header, sidebar navigation, and edit-lock toggle."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from nicegui import ui

from pycommence2.gui import state


@contextmanager
def frame(title: str = '') -> Generator[None, None, None]:
    """Wrap page content in the standard app layout.

    Provides a header bar with navigation, DB info badge, and an
    edit-lock toggle.  All pages should be rendered inside this
    context manager.

    Args:
        title: Page title shown in the header.

    Example::

        @ui.page("/")
        async def index():
            with frame("Dashboard"):
                ui.label("Hello!")
    """
    # -- header --------------------------------------------------------------
    with ui.header().classes('items-center justify-between px-4 q-py-xs'):
        with ui.row().classes('items-center gap-4'):
            ui.link('pycommence2', '/').classes('text-white text-lg font-bold no-underline')
            ui.link('Dashboard', '/').classes('text-white no-underline')
            ui.link('Browse', '/browse').classes('text-white no-underline')
            ui.link('Email', '/emailer').classes('text-white no-underline')
            ui.link('Schema', '/schema').classes('text-white no-underline')
            ui.link('Export', '/export').classes('text-white no-underline')
            ui.link('DDE Console', '/dde').classes('text-white no-underline')

        with ui.row().classes('items-center gap-4'):
            if state.worker and state.worker.connected:
                ui.badge('●').props('color=positive')
                ui.label(title).classes('text-white text-sm')
            else:
                ui.badge('●').props('color=negative')
                ui.label('Disconnected').classes('text-white text-sm')

            # edit-lock toggle
            switch = ui.switch('Edit mode', value=state.app_state.edit_unlocked).classes(
                'text-white'
            )
            switch.on_value_change(lambda e: _set_edit_mode(e.value))

    # -- page content --------------------------------------------------------
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 gap-4'):
        yield


def _set_edit_mode(value: bool) -> None:
    """Update the global edit-lock state."""
    state.app_state.edit_unlocked = value


def notify_error(msg: str) -> None:
    """Show an error notification toast."""
    ui.notify(msg, type='negative', position='top', close_button=True)


def notify_success(msg: str) -> None:
    """Show a success notification toast."""
    ui.notify(msg, type='positive', position='top')
