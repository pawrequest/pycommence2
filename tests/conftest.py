"""Shared pytest fixtures for pycommence2 integration tests.

These tests run against the LIVE Commence Tutorial database.
Commence must be open in Tutorial mode before running.
"""

from __future__ import annotations

import pytest

from pycommence2 import CommenceSession


@pytest.fixture(scope='session')
def session() -> CommenceSession:
    """A single CommenceSession shared across the entire test session.

    Using session scope because:
    - COM init is expensive
    - We're testing against a live Tutorial DB
    - Tests that mutate data clean up after themselves
    """
    s = CommenceSession()
    yield s
    s.close()


@pytest.fixture
async def async_session():
    """An AsyncCommenceSession for async tests.

    Uses function scope so each async test gets a fresh session.
    Requires pytest-asyncio.
    """
    from pycommence2 import AsyncCommenceSession

    async with AsyncCommenceSession() as db:
        yield db
