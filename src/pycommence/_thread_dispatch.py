"""Thread dispatcher — runs a CommenceSession on a dedicated COM thread.

Commence COM objects are STA-bound (Single Threaded Apartment): they must be
created and called from the same thread.  ``ThreadDispatcher`` manages that
thread and provides both sync and async methods to dispatch work to it.

This module is the shared foundation for :class:`AsyncCommenceSession` and
the GUI's :class:`ComWorker`.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from concurrent.futures import Future
from typing import Any, Callable, TypeVar

log = logging.getLogger(__name__)

T = TypeVar('T')

# Sentinel object to signal shutdown.
_SHUTDOWN = object()


class ThreadDispatcher:
    """Owns a daemon thread with a ``CommenceSession`` and dispatches calls to it.

    Usage::

        dispatcher = ThreadDispatcher()
        dispatcher.start()          # spawns COM thread, creates session

        # Sync (from any thread):
        name = dispatcher.submit(lambda s: s.db_name).result()

        # Async (from an event loop):
        name = await dispatcher.run(lambda s: s.db_name)

        dispatcher.stop()
    """

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._queue: queue.Queue[tuple[Callable, Future] | object] = queue.Queue()
        self._session: Any = None  # CommenceSession, set on worker thread
        self._ready = threading.Event()
        self._error: Exception | None = None

    # -- public state --------------------------------------------------------

    @property
    def connected(self) -> bool:
        """Whether the COM session was successfully created."""
        return self._session is not None and self._error is None

    @property
    def startup_error(self) -> Exception | None:
        """The exception that prevented startup, if any."""
        return self._error

    @property
    def session(self) -> Any:
        """The underlying ``CommenceSession`` (only safe from the COM thread)."""
        return self._session

    # -- lifecycle -----------------------------------------------------------

    def start(self, *, timeout: float = 15) -> None:
        """Spawn the COM worker thread and block until it is ready.

        Args:
            timeout: Seconds to wait for COM initialisation.
        """
        self._thread = threading.Thread(
            target=self._worker_loop,
            name='pycommence-dispatch',
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=timeout)
        if self._error:
            log.error('Dispatcher failed to start: %s', self._error)

    def stop(self) -> None:
        """Signal the worker to shut down and wait for it to finish."""
        if self._thread and self._thread.is_alive():
            self._queue.put(_SHUTDOWN)
            self._thread.join(timeout=5)
            log.info('Dispatcher stopped.')

    # -- dispatching ---------------------------------------------------------

    def submit(self, fn: Callable[..., T], *args: Any) -> Future[T]:
        """Submit *fn(session, \\*args)* for execution on the COM thread.

        Returns a :class:`~concurrent.futures.Future` that will contain the
        result (or exception) once the COM thread processes the call.
        """
        if not self.connected:
            raise RuntimeError('Dispatcher not connected. Is Commence running?')
        future: Future[T] = Future()

        def _task(session: Any) -> None:
            try:
                result = fn(session, *args)
                future.set_result(result)
            except Exception as exc:
                future.set_exception(exc)

        self._queue.put((_task, future))
        return future

    async def run(self, fn: Callable[..., T], *args: Any) -> T:
        """Dispatch *fn(session, \\*args)* to the COM thread and ``await`` the result.

        This is the async-friendly counterpart of :meth:`submit`.
        """
        if not self.connected:
            raise RuntimeError('Dispatcher not connected. Is Commence running?')
        loop = asyncio.get_running_loop()
        future: Future[T] = Future()

        def _task(session: Any) -> None:
            try:
                result = fn(session, *args)
                loop.call_soon_threadsafe(future.set_result, result)
            except Exception as exc:
                loop.call_soon_threadsafe(future.set_exception, exc)

        self._queue.put((_task, future))
        return await asyncio.wrap_future(future)

    # -- internal ------------------------------------------------------------

    def _worker_loop(self) -> None:
        """Main loop executed on the dedicated COM thread."""
        from pycommence.session import CommenceSession

        try:
            self._session = CommenceSession()
            log.info(
                'Dispatcher connected: %s (%s)',
                self._session.db_name,
                self._session.db_path,
            )
        except Exception as exc:
            self._error = exc
            self._ready.set()
            return

        self._ready.set()

        while True:
            item = self._queue.get()
            if item is _SHUTDOWN:
                break
            task_fn, _future = item  # type: ignore[misc]
            try:
                task_fn(self._session)
            except Exception:
                log.debug('Dispatcher task raised', exc_info=True)

        # Cleanup
        try:
            self._session.close()
        except Exception:
            log.debug('Error closing session on dispatcher shutdown', exc_info=True)
        self._session = None
