"""Connection service – assign/unassign and query Commence connections via DDE."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pycommence._com.connection import CommenceDB

log = logging.getLogger(__name__)


class ConnectionService:
    """Manage Commence connections (relationships) between items.

    Commence connections cannot be created or deleted through the cursor/rowset
    API — they **must** use DDE Execute commands.
    """

    def __init__(self, db: "CommenceDB") -> None:
        self._db = db
        self._conv = db.get_conversation()

    # -- mutate --------------------------------------------------------------
    def assign(
        self,
        from_category: str,
        from_item: str,
        connection_name: str,
        to_category: str,
        to_item: str,
    ) -> None:
        """Create a connection between two items.

        Args:
            from_category: Source category name.
            from_item: Source item name (primary key).
            connection_name: Connection name (e.g. ``"Relates to"``).
            to_category: Target category name.
            to_item: Target item name (primary key).

        Raises:
            ConversationError: If the DDE command fails.

        Example::

            db.connections.assign(
                "Person", "John Smith",
                "Is Employed by",
                "Company", "Acme Corp",
            )
        """
        cmd = (
            f'[AssignConnection("{from_category}", "{from_item}", '
            f'"{connection_name}", "{to_category}", "{to_item}")]'
        )
        self._conv.execute(cmd)
        log.info(
            "Assigned connection: %s/%s -[%s]-> %s/%s",
            from_category, from_item, connection_name, to_category, to_item,
        )

    def unassign(
        self,
        from_category: str,
        from_item: str,
        connection_name: str,
        to_category: str,
        to_item: str,
    ) -> None:
        """Remove a connection between two items.

        Args:
            from_category: Source category name.
            from_item: Source item name (primary key).
            connection_name: Connection name (e.g. ``"Relates to"``).
            to_category: Target category name.
            to_item: Target item name (primary key).

        Raises:
            ConversationError: If the DDE command fails.

        Example::

            db.connections.unassign(
                "Person", "John Smith",
                "Is Employed by",
                "Company", "Acme Corp",
            )
        """
        cmd = (
            f'[UnassignConnection("{from_category}", "{from_item}", '
            f'"{connection_name}", "{to_category}", "{to_item}")]'
        )
        self._conv.execute(cmd)
        log.info(
            "Unassigned connection: %s/%s -[%s]-> %s/%s",
            from_category, from_item, connection_name, to_category, to_item,
        )

    # -- query ---------------------------------------------------------------
    def get_connected_item_names(
        self,
        from_category: str,
        from_item: str,
        connection_name: str,
        to_category: str,
        *,
        delim: str = "|",
    ) -> list[str]:
        """Return the names of items connected to *from_item*.

        Args:
            from_category: Source category name.
            from_item: Source item name.
            connection_name: Connection name.
            to_category: Target category name.
            delim: Delimiter for the DDE response.

        Returns:
            List of connected item name strings.

        Example::

            names = db.connections.get_connected_item_names(
                "Person", "John Smith",
                "Is Employed by", "Company",
            )
            # ["Acme Corp", "Beta Inc"]
        """
        cmd = (
            f'[GetConnectedItemNames("{from_category}", "{from_item}", '
            f'"{connection_name}", "{to_category}", "{delim}")]'
        )
        raw = self._conv.request(cmd)
        return [n.strip() for n in raw.split(delim) if n.strip()]

    def get_connected_item_count(
        self,
        from_category: str,
        from_item: str,
        connection_name: str,
        to_category: str,
    ) -> int:
        """Return the number of items connected to *from_item*.

        Args:
            from_category: Source category name.
            from_item: Source item name.
            connection_name: Connection name.
            to_category: Target category name.

        Returns:
            Connected item count as an integer.

        Example::

            count = db.connections.get_connected_item_count(
                "Person", "John Smith",
                "Is Employed by", "Company",
            )
        """
        cmd = (
            f'[GetConnectedItemCount("{from_category}", "{from_item}", '
            f'"{connection_name}", "{to_category}")]'
        )
        raw = self._conv.request(cmd)
        return int(raw.strip())

    def get_connected_item_field(
        self,
        from_category: str,
        from_item: str,
        connection_name: str,
        to_category: str,
        field_name: str,
        *,
        delim: str = "|",
    ) -> list[str]:
        """Return a specific field value from each connected item.

        Args:
            from_category: Source category name.
            from_item: Source item name.
            connection_name: Connection name.
            to_category: Target category name.
            field_name: Field to retrieve from each connected item.
            delim: Delimiter for the DDE response.

        Returns:
            List of field values, one per connected item.

        Example::

            phones = db.connections.get_connected_item_field(
                "Person", "John Smith",
                "Is Employed by", "Company",
                "Phone",
            )
            # ["555-0100", "555-0200"]
        """
        cmd = (
            f'[GetConnectedItemField("{from_category}", "{from_item}", '
            f'"{connection_name}", "{to_category}", "{field_name}", "{delim}")]'
        )
        raw = self._conv.request(cmd)
        return [v.strip() for v in raw.split(delim) if v.strip()]
