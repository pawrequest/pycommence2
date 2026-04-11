"""Open a COM connection to the Commence database and wrap ICommenceDB.

.. warning:: COM STA threading

   Commence.DB is an STA (Single-Threaded Apartment) COM object.  All calls
   must be made from the thread that called ``CoInitialize``.  Accessing the
   object from another thread will raise an error or silently corrupt state.

   If you need multi-threaded access, create one ``CommenceSession`` per thread
   (each with its own ``CoInitialize`` call), or use ``pythoncom.CoInitializeEx``
   with careful marshalling.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

import pythoncom
import win32com.client

from pycommence.exceptions import CommenceNotFoundError

if TYPE_CHECKING:
    from pycommence._com.conversation import ConversationWrapper
    from pycommence._com.cursor import CursorWrapper

log = logging.getLogger(__name__)

# Per-thread COM initialisation reference count.
# Each CommenceDB.__init__ increments; each .close() decrements.
# CoUninitialize is only called when the count reaches zero.
_com_init_count: dict[int, int] = {}  # thread-id → count
_com_lock = threading.Lock()


class CommenceDB:
    """Thin wrapper around the ICommenceDB COM dispatch object.

    Ensures COM is initialised (STA) and provides typed factory
    methods for cursors and conversations.
    """

    def __init__(self) -> None:
        tid = threading.current_thread().ident or 0
        with _com_lock:
            prev = _com_init_count.get(tid, 0)
            pythoncom.CoInitialize()
            _com_init_count[tid] = prev + 1
        self._closed = False
        self._init_thread = threading.current_thread()
        try:
            self._db = win32com.client.Dispatch("Commence.DB")
        except Exception as exc:
            # Roll back the ref-count increment on failure.
            with _com_lock:
                _com_init_count[tid] -= 1
                if _com_init_count[tid] <= 0:
                    pythoncom.CoUninitialize()
                    _com_init_count.pop(tid, None)
            raise CommenceNotFoundError(
                "Could not connect to Commence. Is it running?"
            ) from exc
        log.info("Connected to Commence DB: %s (%s)", self.name, self.path)

    def _check_thread(self) -> None:
        """Log a warning if called from a thread other than the init thread."""
        current = threading.current_thread()
        if current is not self._init_thread:
            log.warning(
                "CommenceDB accessed from thread %r but was initialised on %r. "
                "COM STA objects are NOT thread-safe.",
                current.name, self._init_thread.name,
            )

    # -- properties ----------------------------------------------------------
    @property
    def name(self) -> str:
        return self._db.Name

    @property
    def path(self) -> str:
        return self._db.Path

    @property
    def version(self) -> str:
        return self._db.Version

    @property
    def version_ext(self) -> str:
        return self._db.VersionExt

    @property
    def registered_user(self) -> str:
        return self._db.RegisteredUser

    @property
    def shared(self) -> bool:
        return bool(self._db.Shared)

    # -- factories -----------------------------------------------------------
    def get_cursor(
        self,
        name: str,
        mode: int = 0,
        flags: int = 0,
    ) -> "CursorWrapper":
        """Create and return a wrapped ICommenceCursor."""
        self._check_thread()
        from pycommence._com.cursor import CursorWrapper

        raw = self._db.GetCursor(mode, name, flags)
        if raw is None:
            from pycommence.exceptions import CursorError
            raise CursorError(f"GetCursor failed for '{name}' (mode={mode})")
        return CursorWrapper(raw)

    def get_conversation(
        self,
        topic: str | None = None,
    ) -> "ConversationWrapper":
        """Create and return a wrapped ICommenceConversation."""
        self._check_thread()
        from pycommence._com.conversation import ConversationWrapper

        # Use the DB name as topic by default (recommended by docs)
        topic = topic or self.name
        raw = self._db.GetConversation("Commence", topic)
        if raw is None:
            from pycommence.exceptions import ConversationError
            raise ConversationError(f"GetConversation failed for topic '{topic}'")
        return ConversationWrapper(raw)

    # -- raw access (escape hatch) -------------------------------------------
    @property
    def raw(self) -> Any:
        """Direct access to the underlying COM dispatch — use sparingly."""
        return self._db

    def close(self) -> None:
        """Release the COM reference. Safe to call multiple times."""
        if self._closed:
            return
        self._closed = True
        self._db = None  # type: ignore[assignment]
        tid = (self._init_thread.ident or 0)
        with _com_lock:
            count = _com_init_count.get(tid, 1) - 1
            if count <= 0:
                pythoncom.CoUninitialize()
                _com_init_count.pop(tid, None)
            else:
                _com_init_count[tid] = count

