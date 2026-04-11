"""Wrapper around ICommenceConversation – DDE request/execute for schema introspection."""

from __future__ import annotations

import logging
from typing import Any

from pycommence._com.retry import com_retry
from pycommence.exceptions import ConversationError

log = logging.getLogger(__name__)


class ConversationWrapper:
    """Wraps ICommenceConversation for DDE-style Request and Execute calls."""

    def __init__(self, raw_conversation: Any) -> None:
        self._conv = raw_conversation

    @com_retry()
    def request(self, dde_command: str) -> str:
        """Send a DDE Request and return the response string.

        Example: request('[GetCategoryNames("|")]')
        """
        result = self._conv.Request(dde_command)
        if result is None:
            raise ConversationError(f"Request failed: {dde_command}")
        return result

    @com_retry()
    def execute(self, dde_command: str) -> bool:
        """Send a DDE Execute command. Returns True on success."""
        result = self._conv.Execute(dde_command)
        if not result:
            raise ConversationError(f"Execute failed: {dde_command}")
        return True

    @property
    def raw(self) -> Any:
        return self._conv

