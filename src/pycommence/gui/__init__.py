"""pycommence GUI — NiceGUI desktop application.

Launched via ``pycommence gui`` or by calling ``create_app()`` directly.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def create_app() -> None:
    """Register all page routes and configure the NiceGUI app.

    Call this before ``ui.run()`` to set up the full GUI.
    """
    from nicegui import app

    from pycommence.gui import state
    from pycommence.gui import (
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
        log.error(
            "GUI starting in disconnected mode — Commence is not running "
            "or no database is open."
        )

    # Register all page routes
    dashboard.register()
    browser.register()
    detail.register()
    schema_explorer.register()
    export_dialog.register()
    dde_console.register()

    # Clean shutdown
    app.on_shutdown(lambda: state.worker.stop() if state.worker else None)

    log.info("pycommence GUI app configured.")


def run(
    *,
    native: bool = True,
    title: str = "pycommence",
    port: int = 0,
    reload: bool = False,
) -> None:
    """Create the app and start the NiceGUI server.

    Args:
        native: If ``True`` (default), open in a native desktop window.
        title: Window title.
        port: Server port (0 = auto-select).
        reload: Enable hot-reload (for development).
    """
    from nicegui import ui

    create_app()
    ui.run(
        native=native,
        title=title,
        port=port,
        reload=reload,
        window_size=(1280, 800),
    )

