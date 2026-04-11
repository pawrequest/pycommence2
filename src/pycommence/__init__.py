"""pycommence – a clean Python library for Commence database CRUD & introspection."""

from importlib.metadata import version as _get_version

__version__ = _get_version("pycommence")

from pycommence.exceptions import (
    CommenceError,
    CommenceNotFoundError,
    ConversationError,
    CursorError,
    FilterError,
    RowsetError,
    SchemaError,
)
from pycommence.models import (
    CategoryInfo,
    ConnectionInfo,
    FieldInfo,
    FieldType,
    FilterClause,
    FilterType,
    RelatedColumn,
    RowResult,
    SortSpec,
)
from pycommence.query import QueryBuilder
from pycommence.services.connections import ConnectionService
from pycommence.services.dde import DdeService
from pycommence.session import CommenceSession

__all__ = [
    "__version__",
    # Public entry point
    "CommenceSession",
    "QueryBuilder",
    # Services
    "ConnectionService",
    "DdeService",
    # Models
    "CategoryInfo",
    "ConnectionInfo",
    "FieldInfo",
    "FieldType",
    "FilterClause",
    "FilterType",
    "RelatedColumn",
    "RowResult",
    "SortSpec",
    # Exceptions
    "CommenceError",
    "CommenceNotFoundError",
    "ConversationError",
    "CursorError",
    "FilterError",
    "RowsetError",
    "SchemaError",
]


def main() -> None:
    """CLI entry point — delegates to the click-based CLI.

    Requires the ``cli`` extra: ``pip install pycommence[cli]``
    """
    try:
        from pycommence.cli import cli
        cli()
    except ImportError:
        print("pycommence CLI requires the 'cli' extra.")
        print("Install with:  pip install pycommence[cli]")
        raise SystemExit(1)
