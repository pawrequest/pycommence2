"""Shared pytest fixtures for pycommence integration tests.

These tests run against the LIVE Commence Tutorial database.
Commence must be open in Tutorial mode before running.
"""

from __future__ import annotations

import pytest

from pycommence import CommenceSession


@pytest.fixture(scope="session")
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

