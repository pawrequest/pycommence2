"""Tests for CommenceSession – connection, metadata, repr."""

from __future__ import annotations

from pycommence2 import CommenceSession


class TestSessionConnection:
    """Verify we can connect to the Tutorial DB and read basic metadata."""

    def test_session_connects(self, session: CommenceSession) -> None:
        assert session.db_name == 'Tutorial'

    def test_db_path_not_empty(self, session: CommenceSession) -> None:
        assert session.db_path
        assert 'tutorial' in session.db_path.lower()

    def test_db_version_format(self, session: CommenceSession) -> None:
        # Version should be in "x.y" format
        version = session.db_version
        assert '.' in version
        parts = version.split('.')
        assert len(parts) >= 2
        assert parts[0].isdigit()

    def test_repr(self, session: CommenceSession) -> None:
        r = repr(session)
        assert 'CommenceSession' in r
        assert 'Tutorial' in r

    def test_context_manager(self) -> None:
        """Verify context manager opens and closes without error."""
        with CommenceSession() as s:
            assert s.db_name == 'Tutorial'
        # After exit, the session is closed – no assertion needed,
        # just verifying no exception.
