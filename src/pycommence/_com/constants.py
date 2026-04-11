"""Commence COM/DDE constants mapped from the DBAPI documentation."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Cursor mode flags  (GetCursor nMode)
# ---------------------------------------------------------------------------
CMC_CURSOR_CATEGORY = 0
CMC_CURSOR_VIEW = 1
CMC_CURSOR_PILOTAB = 2
CMC_CURSOR_PILOTMEMO = 3
CMC_CURSOR_PILOTTODO = 5
CMC_CURSOR_PILOTAPPT = 6
CMC_CURSOR_OUTLOOKAB = 7
CMC_CURSOR_OUTLOOKAPPT = 8
CMC_CURSOR_EMAILLOG = 9
CMC_CURSOR_OUTLOOKTASK = 10
CMC_CURSOR_MERGE = 11

# ---------------------------------------------------------------------------
# SeekRow bookmarks
# ---------------------------------------------------------------------------
BOOKMARK_BEGINNING = 0
BOOKMARK_CURRENT = 1
BOOKMARK_END = 2

# ---------------------------------------------------------------------------
# Option flags  (hex values from docs)
# ---------------------------------------------------------------------------
CMC_FLAG_FIELD_NAME = 0x0001
CMC_FLAG_ALL = 0x0002
CMC_FLAG_SHARED = 0x0004
CMC_FLAG_PILOT = 0x0008
CMC_FLAG_CANONICAL = 0x0010
CMC_FLAG_INTERNET = 0x0020
