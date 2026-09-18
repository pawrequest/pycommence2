"""pycommence2 GUI — NiceGUI desktop application.

Launched via ``pycommence2 gui`` or by calling ``create_app()`` directly.
"""

from __future__ import annotations

import logging

from pycommence2.gui import emailer_page, actions

log = logging.getLogger(__name__)


def create_app() -> None:
    """Register all page routes and configure the NiceGUI app.

    Call this before ``ui.run()`` to set up the full GUI.
    """
    from nicegui import app

    from pycommence2.gui import state
    from pycommence2.gui import (
        browser,
        dashboard,
        dde_console,
        detail,
        export_dialog,
        schema_explorer,
    )

    # Start the COM worker
    state.worker = state.ComWorker()
    state.worker.start()

    if not state.worker.connected:
        log.error('GUI starting in disconnected mode — Commence is not running or no database is open.')

    # Register all page routes
    dashboard.register()
    browser.register()
    detail.register()
    schema_explorer.register()
    export_dialog.register()
    dde_console.register()
    emailer_page.register()
    actions.register()

    # Clean shutdown
    app.on_shutdown(lambda: state.worker.stop() if state.worker else None)

    log.info('pycommence2 GUI app configured.')


def run(
    *,
    native: bool = False,
    title: str = 'pycommence2',
    port: int = 0,
    reload: bool = False,
    host: str = '0.0.0.0'
) -> None:
    """Create the app and start the NiceGUI server.

    Args:
        native: If ``True`` (default), open in a native desktop window.
        title: Window title.
        port: Server port (0 = auto-select).
        reload: Enable hot-reload (for development).
        host: Server host (default '0.0.0.0').
    """
    from nicegui import ui

    create_app()
    ui.run(
        native=native,
        title=title,
        port=port,
        reload=reload,
        host=host,
        window_size=(1280, 800),
    )


if __name__ == '__main__':
    run()
