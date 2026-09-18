"""Exception hierarchy for pycommence2."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycommence2.models import ResultTuple


class RaiseAction(StrEnum):
    RAISE = 'raise'
    IGNORE = 'ignore'


class CommenceError(Exception):
    """Base exception for all Commence-related errors."""


class CommenceMaxExceededError(CommenceError):
    """Raised when multiple rows are found but only one was expected."""

    n_results: int = -1


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


class CommenceAmbiguousError(CommenceError):
    """Raised when no Id or pk_value is passed"""


def raise_for_one(res: ResultTuple, raise_action: RaiseAction = RaiseAction.RAISE):
    lenres = len(res)
    match (lenres, raise_action):
        case (1, _):
            return res[0]
        case (0, RaiseAction.RAISE):
            raise CommenceNotFoundError()
        case (_, RaiseAction.RAISE):
            raise CommenceMaxExceededError(res)
    return None


def raise_for_id_or_pk(id, pk):
    """Ensure at least one of id or pk is provided."""
    if not any([id, pk]):
        raise ValueError('Must provide id or pk')
