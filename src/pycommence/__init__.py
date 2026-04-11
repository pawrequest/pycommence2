"""pycommence – a clean Python library for Commence database CRUD & introspection."""

from importlib.metadata import version as _get_version

__version__ = _get_version('pycommence')

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
    WatchEvent,
)
from pycommence.async_session import AsyncCommenceSession
from pycommence.query import QueryBuilder
from pycommence.services.backup import BackupService
from pycommence.services.connections import ConnectionService
from pycommence.services.dde import DdeService
from pycommence.services.export import ExportService
from pycommence.services.import_svc import ImportService
from pycommence.session import CommenceSession

__all__ = [
    '__version__',
    # Public entry points
    'AsyncCommenceSession',
    'CommenceSession',
    'QueryBuilder',
    # Services
    'BackupService',
    'ConnectionService',
    'DdeService',
    'ExportService',
    'ImportService',
    # Models
    'CategoryInfo',
    'ConnectionInfo',
    'FieldInfo',
    'FieldType',
    'FilterClause',
    'FilterType',
    'RelatedColumn',
    'RowResult',
    'SortSpec',
    'WatchEvent',
    # Exceptions
    'CommenceError',
    'CommenceNotFoundError',
    'ConversationError',
    'CursorError',
    'FilterError',
    'RowsetError',
    'SchemaError',
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
        print('Install with:  pip install pycommence[cli]')
        raise SystemExit(1)
