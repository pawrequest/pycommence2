"""Persistent schema cache with METADATA.PIM-based staleness detection.

Caches category/field/connection definitions to disk so that repeated
schema lookups are instant.  Uses the mtime of Commence's ``METADATA.PIM``
file as a primary invalidation sentinel — one ``os.stat()`` call replaces
dozens of DDE round-trips.

Cache files are stored under ``platformdirs.user_cache_dir("pycommence2")``,
one JSON file per database (keyed by ``db_name + db_path`` hash).
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from platformdirs import user_cache_dir

log = logging.getLogger(__name__)

CACHE_DIR = Path(user_cache_dir('pycommence2'))

# Sentinel values for cache trust level
TRUST_FULL = 'full'  # L1 passed — mtime matches
TRUST_SUSPECT = 'suspect'  # mtime differs but category count same
TRUST_NONE = 'none'  # no cache or full invalidation


def _cache_key(db_name: str, db_path: str) -> str:
    """Generate a unique filename-safe key for a database."""
    raw = f'{db_name}|{db_path}'.encode()
    short_hash = hashlib.sha256(raw).hexdigest()[:8]
    safe_name = db_name.replace(' ', '_').replace('\\', '_').replace('/', '_')
    return f'{safe_name}_{short_hash}'


def _metadata_pim_path(db_path: str) -> Path:
    """Return the expected path to METADATA.PIM for a Commence database."""
    return Path(db_path) / 'METADATA.PIM'


def _get_mtime_iso(path: Path) -> str | None:
    """Return the mtime of a file as an ISO 8601 string, or None on failure."""
    try:
        stat = path.stat()
        return datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()
    except OSError:
        return None


class SchemaCache:
    """In-memory + on-disk cache for Commence schema data.

    Attributes:
        db_name: Name of the Commence database.
        db_path: Filesystem path to the database.
        trust_level: Current trust level (``"full"``, ``"suspect"``, ``"none"``).
    """

    def __init__(self, db_name: str, db_path: str) -> None:
        self.db_name = db_name
        self.db_path = db_path
        self.trust_level: str = TRUST_NONE
        self._data: dict[str, Any] = {}
        self._cache_file = CACHE_DIR / f'{_cache_key(db_name, db_path)}.json'
        self._load()

    # -- public API ----------------------------------------------------------

    def get_category_names(self) -> list[str] | None:
        """Return cached category names, or None if not cached."""
        if self.trust_level == TRUST_NONE:
            return None
        return self._data.get('category_names')

    def get_category_count(self) -> int | None:
        """Return cached category count, or None if not cached."""
        if self.trust_level == TRUST_NONE:
            return None
        return self._data.get('category_count')

    def get_field_names(self, category: str) -> list[str] | None:
        """Return cached field names for a category, or None."""
        cat_data = self._get_category_data(category)
        if cat_data is None:
            return None
        return cat_data.get('field_names')

    def get_field_count(self, category: str) -> int | None:
        """Return cached field count for a category, or None."""
        cat_data = self._get_category_data(category)
        if cat_data is None:
            return None
        return cat_data.get('field_count')

    def get_fields(self, category: str) -> list[dict[str, Any]] | None:
        """Return cached field definitions for a category, or None."""
        cat_data = self._get_category_data(category)
        if cat_data is None:
            return None
        return cat_data.get('fields')

    def get_connections(self, category: str) -> list[dict[str, str]] | None:
        """Return cached connection definitions for a category, or None."""
        cat_data = self._get_category_data(category)
        if cat_data is None:
            return None
        return cat_data.get('connections')

    # -- update methods ------------------------------------------------------

    def set_category_names(self, names: list[str]) -> None:
        """Store category names in cache."""
        self._data['category_names'] = names
        self._data['category_count'] = len(names)

    def set_fields(
        self,
        category: str,
        field_names: list[str],
        fields: list[dict[str, Any]],
    ) -> None:
        """Store field definitions for a category."""
        cats = self._data.setdefault('categories', {})
        cats.setdefault(category, {}).update(
            {
                'field_count': len(field_names),
                'field_names': field_names,
                'fields': fields,
            }
        )

    def set_connections(
        self,
        category: str,
        connections: list[dict[str, str]],
    ) -> None:
        """Store connection definitions for a category."""
        cats = self._data.setdefault('categories', {})
        cats.setdefault(category, {}).update(
            {
                'connections': connections,
            }
        )

    def invalidate_category(self, category: str) -> None:
        """Remove cached data for a single category."""
        cats = self._data.get('categories', {})
        cats.pop(category, None)

    def save(self) -> None:
        """Write cache to disk."""
        self._data['db_name'] = self.db_name
        self._data['db_path'] = self.db_path
        # Update mtime from METADATA.PIM
        mtime = _get_mtime_iso(_metadata_pim_path(self.db_path))
        if mtime:
            self._data['metadata_mtime'] = mtime
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            self._cache_file.write_text(
                json.dumps(self._data, indent=2, default=str),
                encoding='utf-8',
            )
            log.debug('Schema cache saved to %s', self._cache_file)
        except OSError as exc:
            log.warning('Failed to save schema cache: %s', exc)

    def clear(self) -> None:
        """Drop in-memory and on-disk cache."""
        self._data = {}
        self.trust_level = TRUST_NONE
        try:
            self._cache_file.unlink(missing_ok=True)
            log.info('Schema cache cleared: %s', self._cache_file)
        except OSError as exc:
            log.warning('Failed to delete cache file: %s', exc)

    # -- staleness detection -------------------------------------------------

    def check_staleness(self, live_category_count: int | None = None) -> str:
        """Run the layered staleness check and return the trust level.

        Args:
            live_category_count: If provided, used for L2 check when L1
                is unavailable. Pass ``None`` to skip L2.

        Returns:
            The trust level: ``"full"``, ``"suspect"``, or ``"none"``.
        """
        if not self._data:
            self.trust_level = TRUST_NONE
            return TRUST_NONE

        # L0: DB identity
        if self._data.get('db_name') != self.db_name or self._data.get('db_path') != self.db_path:
            log.info('Cache L0 fail: DB identity mismatch')
            self.trust_level = TRUST_NONE
            return TRUST_NONE

        # L1: METADATA.PIM mtime
        cached_mtime = self._data.get('metadata_mtime')
        current_mtime = _get_mtime_iso(_metadata_pim_path(self.db_path))
        if cached_mtime and current_mtime:
            if cached_mtime == current_mtime:
                log.debug('Cache L1 pass: METADATA.PIM mtime unchanged')
                self.trust_level = TRUST_FULL
                return TRUST_FULL
            else:
                log.info(
                    'Cache L1 fail: METADATA.PIM mtime changed (cached=%s, current=%s)',
                    cached_mtime,
                    current_mtime,
                )
                # Fall through to L2

        # L2: Category count (if available)
        if live_category_count is not None:
            cached_count = self._data.get('category_count')
            if cached_count is not None and cached_count == live_category_count:
                log.debug(
                    'Cache L2 pass: category count unchanged (%d)',
                    live_category_count,
                )
                self.trust_level = TRUST_SUSPECT
                return TRUST_SUSPECT
            else:
                log.info(
                    'Cache L2 fail: category count changed (cached=%s, live=%s)',
                    cached_count,
                    live_category_count,
                )
                self.trust_level = TRUST_NONE
                return TRUST_NONE

        # L1 unavailable and no L2 provided
        if current_mtime is None and live_category_count is None:
            log.info('Cache staleness: no L1 or L2 available, marking suspect')
            self.trust_level = TRUST_SUSPECT
            return TRUST_SUSPECT

        # mtime changed but no L2 to verify
        self.trust_level = TRUST_SUSPECT
        return TRUST_SUSPECT

    # -- internal ------------------------------------------------------------

    def _get_category_data(self, category: str) -> dict[str, Any] | None:
        """Return cached data for a specific category, respecting trust level."""
        if self.trust_level == TRUST_NONE:
            return None
        cats = self._data.get('categories', {})
        return cats.get(category)

    def _load(self) -> None:
        """Load cache from disk if available."""
        if not self._cache_file.exists():
            log.debug('No cache file at %s', self._cache_file)
            return
        try:
            raw = self._cache_file.read_text(encoding='utf-8')
            self._data = json.loads(raw)
            log.debug('Loaded schema cache from %s', self._cache_file)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning('Corrupt cache file %s: %s — deleting', self._cache_file, exc)
            self._cache_file.unlink(missing_ok=True)
            self._data = {}
