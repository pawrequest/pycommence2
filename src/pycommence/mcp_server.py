"""Built-in MCP server for pycommence.

Exposes Commence database operations as MCP tools, allowing LLM agents
to interact with Commence databases over stdio or SSE transport.

Usage::

    # Via CLI
    pycommence mcp
    pycommence mcp --read-only
    pycommence mcp --transport sse

    # As standalone entry point
    pycommence-mcp
    pycommence-mcp --read-only

Requires the ``mcp`` extra::

    pip install pycommence[mcp]
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy import guard — mcp is an optional dependency
# ---------------------------------------------------------------------------


def _check_mcp_installed() -> None:
    try:
        import mcp  # noqa: F401
    except ImportError:
        raise SystemExit(
            "The MCP server requires the 'mcp' extra.\nInstall with:  pip install pycommence[mcp]"
        )


def _build_server(*, read_only: bool = False) -> Any:
    """Construct the FastMCP server instance with all tools registered."""
    from mcp.server.fastmcp import FastMCP

    mcp_app = FastMCP(
        'pycommence',
        description='MCP server for Commence database operations via pycommence.',
    )

    # The async session is lazily initialised on first tool call.
    _state: dict[str, Any] = {'session': None}

    async def _get_session() -> Any:
        from pycommence.async_session import AsyncCommenceSession

        if _state['session'] is None:
            sess = AsyncCommenceSession()
            await sess.__aenter__()
            _state['session'] = sess
        return _state['session']

    # ------------------------------------------------------------------
    # Read tools
    # ------------------------------------------------------------------

    @mcp_app.tool()
    async def list_categories() -> list[str]:
        """List every category (table) name in the open Commence database."""
        db = await _get_session()
        return await db.list_categories()

    @mcp_app.tool()
    async def get_category_field_names(category: str) -> list[str]:
        """Return the field (column) names for a Commence category."""
        db = await _get_session()
        fields = await db.get_fields(category)
        return [f.name for f in fields]

    @mcp_app.tool()
    async def get_category_field_definitions(category: str) -> list[dict[str, Any]]:
        """Return field definitions (name, type, max-length …) for a Commence category."""
        db = await _get_session()
        fields = await db.get_fields(category)
        return [
            {
                'name': f.name,
                'type': f.field_type.name,
                'max_chars': f.max_chars,
                'default': f.default,
                'is_mandatory': f.is_mandatory,
                'is_shared': f.is_shared,
            }
            for f in fields
        ]

    @mcp_app.tool()
    async def get_row_count(category: str) -> int:
        """Return the number of rows in a Commence category."""
        db = await _get_session()
        return await db.get_row_count(category)

    @mcp_app.tool()
    async def read_rows(
        category: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, str]]:
        """Read rows from a Commence category with optional pagination.

        Args:
            category: Commence category name (e.g. 'Contact', 'Account').
            limit: Maximum rows to return (default 20).
            offset: Row offset for pagination (default 0).
        """
        db = await _get_session()
        # Read limit+offset rows, then slice to simulate offset
        rows = await db.read(category, max_rows=limit + offset)
        return [r.to_dict() for r in rows[offset : offset + limit]]

    @mcp_app.tool()
    async def read_row_by_pk(category: str, pk_value: str) -> dict[str, str]:
        """Read a single row from a Commence category by its primary-key value.

        Args:
            category: Commence category name.
            pk_value: The primary-key value identifying the row.
        """
        db = await _get_session()
        rows = await db.query(
            category,
            filters=[('Name', 'Equal To', pk_value)],
            limit=1,
        )
        if not rows:
            return {'error': f"No row found with Name='{pk_value}' in {category}"}
        return rows[0].to_dict()

    @mcp_app.tool()
    async def search_rows(
        category: str,
        field: str,
        value: str,
        condition: str = 'Contains',
        limit: int = 50,
    ) -> list[dict[str, str]]:
        """Search rows in a Commence category by a field condition.

        Args:
            category: Commence category name.
            field: Field name to filter on.
            value: Value to compare against.
            condition: One of 'Equal To', 'Contains', 'After', 'Before', etc.
            limit: Max rows returned.
        """
        db = await _get_session()
        rows = await db.query(
            category,
            filters=[(field, condition, value)],
            limit=limit,
        )
        return [r.to_dict() for r in rows]

    @mcp_app.tool()
    async def get_db_name() -> dict[str, str]:
        """Return the name and path of the currently open Commence database."""
        db = await _get_session()
        name = await db.db_name()
        path = await db.db_path()
        return {'name': name, 'path': path}

    @mcp_app.tool()
    async def get_db_info() -> dict[str, Any]:
        """Return full database metadata (name, path, version, shared)."""
        db = await _get_session()
        return {
            'name': await db.db_name(),
            'path': await db.db_path(),
            'version': await db.db_version(),
            'shared': await db.db_shared(),
        }

    @mcp_app.tool()
    async def get_connections(category: str) -> list[dict[str, str]]:
        """Return connection definitions for a category."""
        db = await _get_session()
        conns = await db.get_connections(category)
        return [{'name': c.name, 'to_category': c.to_category} for c in conns]

    # ------------------------------------------------------------------
    # Write tools (gated behind --read-only flag)
    # ------------------------------------------------------------------

    if not read_only:

        @mcp_app.tool()
        async def add_row(
            category: str,
            fields: dict[str, str],
        ) -> dict[str, Any]:
            """Add a new row to a Commence category.

            Args:
                category: Target category name.
                fields: Mapping of field_name → value.

            Returns:
                Dict with 'row_id' key (or null if ID unavailable).
            """
            db = await _get_session()
            row_id = await db.add(category, fields)
            return {'row_id': row_id, 'status': 'created'}

        @mcp_app.tool()
        async def edit_row(
            category: str,
            row_id: str,
            fields: dict[str, str],
        ) -> dict[str, str]:
            """Edit an existing row by its unique ID.

            Args:
                category: Commence category name.
                row_id: Unique row identifier.
                fields: Mapping of field_name → new_value.
            """
            db = await _get_session()
            await db.edit(row_id, category, fields)
            return {'status': 'updated', 'row_id': row_id}

        @mcp_app.tool()
        async def delete_row(
            category: str,
            row_id: str,
        ) -> dict[str, str]:
            """Delete a row by its unique ID.

            Args:
                category: Commence category name.
                row_id: Unique row identifier.
            """
            db = await _get_session()
            await db.delete(row_id, category)
            return {'status': 'deleted', 'row_id': row_id}

        @mcp_app.tool()
        async def assign_connection(
            from_category: str,
            from_item: str,
            connection_name: str,
            to_category: str,
            to_item: str,
        ) -> dict[str, str]:
            """Create a connection between two items.

            Args:
                from_category: Source category name.
                from_item: Source item name.
                connection_name: Connection name.
                to_category: Target category name.
                to_item: Target item name.
            """
            db = await _get_session()
            await db.assign_connection(
                from_category,
                from_item,
                connection_name,
                to_category,
                to_item,
            )
            return {'status': 'assigned'}

        @mcp_app.tool()
        async def unassign_connection(
            from_category: str,
            from_item: str,
            connection_name: str,
            to_category: str,
            to_item: str,
        ) -> dict[str, str]:
            """Remove a connection between two items.

            Args:
                from_category: Source category name.
                from_item: Source item name.
                connection_name: Connection name.
                to_category: Target category name.
                to_item: Target item name.
            """
            db = await _get_session()
            await db.unassign_connection(
                from_category,
                from_item,
                connection_name,
                to_category,
                to_item,
            )
            return {'status': 'unassigned'}

    return mcp_app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server (standalone entry point)."""
    import argparse

    _check_mcp_installed()

    parser = argparse.ArgumentParser(
        description='pycommence MCP server — expose Commence DB as MCP tools',
    )
    parser.add_argument(
        '--read-only',
        action='store_true',
        default=False,
        help='Disable write tools (add, edit, delete, connections).',
    )
    parser.add_argument(
        '--transport',
        choices=['stdio', 'sse'],
        default='stdio',
        help='MCP transport (default: stdio).',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port for SSE transport (default: 8000).',
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)s %(levelname)s %(message)s',
    )

    server = _build_server(read_only=args.read_only)

    if args.transport == 'stdio':
        server.run(transport='stdio')
    else:
        server.run(transport='sse', port=args.port)


if __name__ == '__main__':
    main()
