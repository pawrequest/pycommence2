"""COM retry decorator for transient COM failures."""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, TypeVar

log = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])

# Commence application-level error strings that should NOT be retried.
_PERMANENT_ERROR_MARKERS = (
    'Error processing Request command',
    'Error processing Execute command',
)


def _is_transient(exc: Exception) -> bool:
    """Return True if the com_error looks transient (worth retrying)."""
    # pywintypes.com_error args: (hresult, message, excepinfo, argErr)
    # excepinfo is a tuple: (wCode, source, description, helpFile, helpCtx, scode)
    exc_args = getattr(exc, 'args', ())
    if len(exc_args) >= 3 and exc_args[2] is not None:
        excepinfo = exc_args[2]
        if len(excepinfo) >= 3:
            description = str(excepinfo[2] or '')
            for marker in _PERMANENT_ERROR_MARKERS:
                if marker in description:
                    return False
    return True


def com_retry(max_retries: int = 3, delay: float = 0.5) -> Callable[[F], F]:
    """Decorator that retries a function on transient ``pywintypes.com_error``.

    Permanent errors (bad DDE command format, etc.) are raised immediately
    without wasting time on retries.

    Args:
        max_retries: Maximum number of attempts (including the first).
        delay: Base delay in seconds between retries (multiplied by attempt #).
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    # Only retry on COM errors; re-raise everything else.
                    exc_type = type(exc).__name__
                    if exc_type != 'com_error' and 'com_error' not in str(type(exc).__mro__):
                        raise
                    # Don't retry permanent application-level errors.
                    if not _is_transient(exc):
                        raise
                    last_exc = exc
                    if attempt < max_retries - 1:
                        wait = delay * (attempt + 1)
                        log.warning(
                            'COM error in %s (attempt %d/%d), retrying in %.1fs: %s',
                            fn.__qualname__,
                            attempt + 1,
                            max_retries,
                            wait,
                            exc,
                        )
                        time.sleep(wait)
            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator
