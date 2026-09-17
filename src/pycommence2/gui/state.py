"""COM worker thread — bridges NiceGUI's async world with Commence's STA COM.

Commence COM objects are STA-bound (Single Threaded Apartment) — they must be
created and used from a single thread.  NiceGUI, however, runs an asyncio
event loop and dispatches UI events on different tasks.

``ComWorker`` solves this by delegating to :class:`~pycommence2._thread_dispatch.ThreadDispatcher`,
which owns a dedicated daemon thread that:
1. Calls ``CoInitialize()`` once.
2. Creates one ``CommenceSession``.
3. Processes all COM calls dispatched from async code via ``run()``.
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar
from collections.abc import Callable

from pycommence2._thread_dispatch import ThreadDispatcher

log = logging.getLogger(__name__)

T = TypeVar('T')


class ComWorker:
    """Dedicated COM thread that owns a single CommenceSession.

    Usage::

        worker = ComWorker()
        worker.start()

        # From async code:
        name = await worker.run(lambda s: s.db_name)
        rows = await worker.run(lambda s: s.read("Contact", max_rows=10))

        worker.stop()
    """

    def __init__(self) -> None:
        self._dispatcher = ThreadDispatcher()

    @property
    def connected(self) -> bool:
        """Whether the COM session was successfully created."""
        return self._dispatcher.connected

    @property
    def startup_error(self) -> Exception | None:
        """The exception that prevented startup, if any."""
        return self._dispatcher.startup_error

    def start(self) -> None:
        """Spawn the COM worker thread and wait for it to initialise."""
        self._dispatcher.start()
        if self._dispatcher.startup_error:
            log.error('COM worker failed to start: %s', self._dispatcher.startup_error)

    def stop(self) -> None:
        """Signal the worker to shut down and wait for it to finish."""
        self._dispatcher.stop()

    async def run(self, fn: Callable[..., T], *args: Any) -> T:
        """Dispatch *fn(session, \\*args)* to the COM thread and await the result.

        Args:
            fn: A callable that receives the ``CommenceSession`` as its first
                argument, plus any extra ``args``.

        Returns:
            Whatever *fn* returns.

        Raises:
            RuntimeError: If the worker is not connected.
            Exception: Whatever *fn* raises on the COM thread.
        """
        return await self._dispatcher.run(fn, *args)


# ---------------------------------------------------------------------------
# Module-level singleton — initialised by create_app()
# ---------------------------------------------------------------------------
worker: ComWorker | None = None


class AppState:
    """Lightweight shared UI state."""

    def __init__(self) -> None:
        self.edit_unlocked: bool = False


app_state = AppState()
