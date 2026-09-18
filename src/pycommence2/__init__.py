"""pycommence2 – a clean Python library for Commence database CRUD & introspection."""

from importlib.metadata import version as _get_version

__version__ = _get_version('pycommence2')

from pycommence2.exceptions import (
    CommenceError,
    CommenceNotFoundError,
    ConversationError,
    CursorError,
    FilterError,
    RowsetError,
    SchemaError,
)
from pycommence2.models import (
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
from pycommence2.async_session import AsyncCommenceSession
from pycommence2.query import ConditionType, QueryBuilder
from pycommence2.services.backup import BackupService
from pycommence2.services.connections import ConnectionService
from pycommence2.services.dde import DdeService
from pycommence2.services.export import ExportService
from pycommence2.services.import_svc import ImportService
from pycommence2.session import CommenceSession

__all__ = [
    '__version__',
    # Public entry points
    'AsyncCommenceSession',
    'CommenceSession',
    'ConditionType',
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

    Requires the ``cli`` extra: ``pip install pycommence2[cli]``
    """
    try:
        from pycommence2.cli import cli

        cli()
    except ImportError:
        print("pycommence2 CLI requires the 'cli' extra.")
        print('Install with:  pip install pycommence2[cli]')
        raise SystemExit(1)
