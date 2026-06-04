"""Exception hierarchy for pycommence2."""

from __future__ import annotations


class CommenceError(Exception):
    """Base exception for all Commence-related errors."""


class CommenceNotFoundError(CommenceError):
    """Commence application not found or not running."""


class CursorError(CommenceError):
    """Error creating or operating on a Commence cursor."""


class RowsetError(CommenceError):
    """Error creating or operating on a Commence rowset."""


class SchemaError(CommenceError):
    """Error performing schema introspection."""


class ConversationError(CommenceError):
    """Error in DDE conversation request/execute."""


class FilterError(CommenceError):
    """Error building or applying a filter."""
