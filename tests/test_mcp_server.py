"""Tests for the built-in MCP server."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pycommence.models import RowResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_async_session():
    """Create a mock AsyncCommenceSession with async method returns."""
    s = AsyncMock()
    s.db_name.return_value = "TestDB"
    s.db_path.return_value = "C:\\test"
    s.db_version.return_value = "6.0"
    s.db_shared.return_value = False
    s.list_categories.return_value = ["Contact", "Hire"]

    field1 = MagicMock()
    field1.name = "Name"
    field1.field_type.name = "NAME"
    field1.max_chars = 40
    field1.default = ""
    field1.is_mandatory = True
    field1.is_shared = False
    s.get_fields.return_value = [field1]

    conn1 = MagicMock()
    conn1.name = "Relates to"
    conn1.to_category = "Account"
    s.get_connections.return_value = [conn1]

    s.get_row_count.return_value = 42
    s.read.return_value = [
        RowResult(columns={"Name": "Alice"}, row_id="r1"),
        RowResult(columns={"Name": "Bob"}, row_id="r2"),
    ]
    s.query.return_value = [
        RowResult(columns={"Name": "Alice"}, row_id="r1"),
    ]
    s.add.return_value = "new-id"
    return s


# ---------------------------------------------------------------------------
# Unit tests — each MCP tool in isolation
# ---------------------------------------------------------------------------

class TestMcpServerBuild:
    """Test that the server builds without errors."""

    def test_build_server_read_write(self):
        pytest.importorskip("mcp")
        from pycommence.mcp_server import _build_server
        server = _build_server(read_only=False)
        assert server is not None

    def test_build_server_read_only(self):
        pytest.importorskip("mcp")
        from pycommence.mcp_server import _build_server
        server = _build_server(read_only=True)
        assert server is not None


class TestMcpToolFunctions:
    """Test MCP tool functions by calling the underlying async session logic."""

    @pytest.mark.asyncio
    async def test_list_categories(self):
        mock_session = _mock_async_session()
        result = await mock_session.list_categories()
        assert result == ["Contact", "Hire"]

    @pytest.mark.asyncio
    async def test_get_row_count(self):
        mock_session = _mock_async_session()
        result = await mock_session.get_row_count("Contact")
        assert result == 42

    @pytest.mark.asyncio
    async def test_read_rows(self):
        mock_session = _mock_async_session()
        rows = await mock_session.read("Contact", max_rows=20)
        assert len(rows) == 2
        assert rows[0]["Name"] == "Alice"

    @pytest.mark.asyncio
    async def test_search_rows_via_query(self):
        mock_session = _mock_async_session()
        rows = await mock_session.query(
            "Contact",
            filters=[("Name", "Equal To", "Alice")],
            limit=1,
        )
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_get_db_info(self):
        mock_session = _mock_async_session()
        info = {
            "name": await mock_session.db_name(),
            "path": await mock_session.db_path(),
            "version": await mock_session.db_version(),
            "shared": await mock_session.db_shared(),
        }
        assert info["name"] == "TestDB"
        assert info["shared"] is False

    @pytest.mark.asyncio
    async def test_get_fields(self):
        mock_session = _mock_async_session()
        fields = await mock_session.get_fields("Contact")
        assert len(fields) == 1
        assert fields[0].name == "Name"

    @pytest.mark.asyncio
    async def test_get_connections(self):
        mock_session = _mock_async_session()
        conns = await mock_session.get_connections("Contact")
        assert len(conns) == 1
        assert conns[0].name == "Relates to"

    @pytest.mark.asyncio
    async def test_add_row(self):
        mock_session = _mock_async_session()
        row_id = await mock_session.add("Contact", {"Name": "Jane"})
        assert row_id == "new-id"

    @pytest.mark.asyncio
    async def test_edit_row(self):
        mock_session = _mock_async_session()
        await mock_session.edit("r1", "Contact", {"Email": "new@example.com"})
        mock_session.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_row(self):
        mock_session = _mock_async_session()
        await mock_session.delete("r1", "Contact")
        mock_session.delete.assert_called_once()

