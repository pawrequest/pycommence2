"""DDE service – direct DDE Execute/Request commands not covered by the cursor API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycommence._com.connection import CommenceDB

log = logging.getLogger(__name__)


class DdeService:
    """Thin service exposing useful DDE Execute and Request commands.

    These supplement the cursor/rowset API for operations that are easier
    (or only possible) via DDE: single-item CRUD, UI commands, triggers, etc.
    """

    def __init__(self, db: "CommenceDB") -> None:
        self._db = db
        self._conv = db.get_conversation()

    # -- item CRUD via DDE ---------------------------------------------------
    def add_item(
        self,
        category: str,
        item_name: str,
        *,
        clarify_value: str | None = None,
    ) -> None:
        """Add a new item (row) by name via DDE.

        Unlike ``session.add()`` (which uses the cursor API), this does
        not return a row ID. Use it for simple one-off item creation.

        Args:
            category: Commence category name.
            item_name: The Name (primary key) for the new item.
            clarify_value: Optional clarify field value, required for
                categories that allow duplicate names.

        Raises:
            ConversationError: If the DDE command fails (e.g. item
                already exists in a category that disallows duplicates).

        Example::

            db.dde.add_item("Contact", "Jane Doe")
            db.dde.add_item("Contact", "Jane Doe", clarify_value="Boston")
        """
        if clarify_value:
            cmd = f'[AddItem("{category}", "{item_name}", "{clarify_value}")]'
        else:
            cmd = f'[AddItem("{category}", "{item_name}")]'
        self._conv.execute(cmd)

    def edit_item(
        self,
        category: str,
        item_name: str,
        field_name: str,
        value: str,
    ) -> None:
        """Set a single field value on an existing item via DDE.

        Args:
            category: Commence category name.
            item_name: Item name (primary key).
            field_name: Field to update.
            value: New value (as a string).

        Raises:
            ConversationError: If the item does not exist or the
                field name is invalid.

        Example::

            db.dde.edit_item("Contact", "Jane Doe", "Email", "jane@example.com")
        """
        cmd = f'[EditItem("{category}", "{item_name}", "{field_name}", "{value}")]'
        self._conv.execute(cmd)

    def delete_item(self, category: str, item_name: str) -> None:
        """Delete an item by name via DDE.

        Args:
            category: Commence category name.
            item_name: Item name (primary key) to delete.

        Raises:
            ConversationError: If the item does not exist.

        Example::

            db.dde.delete_item("Contact", "Jane Doe")
        """
        cmd = f'[DeleteItem("{category}", "{item_name}")]'
        self._conv.execute(cmd)

    def append_text(
        self,
        category: str,
        item_name: str,
        field_name: str,
        text: str,
    ) -> None:
        """Append text to a field (useful for Notes / large text fields).

        Args:
            category: Commence category name.
            item_name: Item name (primary key).
            field_name: Field to append to.
            text: Text to append.

        Raises:
            ConversationError: If the item or field does not exist.

        Example::

            db.dde.append_text("Contact", "Jane Doe", "Notes",
                               "\\n2026-04-11: Called back.")
        """
        cmd = f'[AppendText("{category}", "{item_name}", "{field_name}", "{text}")]'
        self._conv.execute(cmd)

    # -- field reads via DDE -------------------------------------------------
    def get_field(self, category: str, item_name: str, field_name: str) -> str:
        """Read a single field value from an item via DDE.

        Args:
            category: Commence category name.
            item_name: Item name (primary key).
            field_name: Field to read.

        Returns:
            The field value as a string (trailing newline stripped).

        Raises:
            ConversationError: If the item or field does not exist.

        Example::

            email = db.dde.get_field("Contact", "Jane Doe", "Email")
        """
        cmd = f'[GetField("{category}", "{item_name}", "{field_name}")]'
        return self._conv.request(cmd).rstrip("\n")

    def get_fields(
        self,
        category: str,
        item_name: str,
        *field_names: str,
        delim: str = "|",
    ) -> list[str]:
        """Read multiple field values from a single item in one DDE call.

        Args:
            category: Category name.
            item_name: Item primary key.
            *field_names: One or more field names to read.
            delim: Delimiter for the DDE response (max 8 chars).

        Returns:
            A list of field values in the same order as *field_names*.

        Raises:
            ConversationError: If the item does not exist.

        Example::

            values = db.dde.get_fields("Contact", "Jane Doe",
                                       "Name", "Email", "Phone")
            # ["Jane Doe", "jane@example.com", "555-0100"]
        """
        n = len(field_names)
        fields_str = '", "'.join(field_names)
        cmd = f'[GetFields("{category}", "{item_name}", {n}, "{fields_str}", "{delim}")]'
        raw = self._conv.request(cmd)
        return [v.rstrip("\n") for v in raw.split(delim)]

    def get_field_to_file(
        self,
        category: str,
        item_name: str,
        field_name: str,
        filename: str,
    ) -> None:
        """Save a field value to a file on disk via DDE.

        Useful for extracting image or data-file fields.

        Args:
            category: Commence category name.
            item_name: Item name (primary key).
            field_name: Field to export.
            filename: Absolute path for the output file.

        Raises:
            ConversationError: If the DDE command fails.

        Example::

            db.dde.get_field_to_file("Contact", "Jane Doe",
                                     "Photo", "C:\\\\photos\\\\jane.jpg")
        """
        cmd = (
            f'[GetFieldToFile("{category}", "{item_name}", '
            f'"{field_name}", "{filename}")]'
        )
        self._conv.execute(cmd)

    # -- item enumeration ----------------------------------------------------
    def get_item_names(self, category: str, *, delim: str = "|") -> list[str]:
        """Return all item names (primary keys) in a category.

        Args:
            category: Commence category name.
            delim: Delimiter for the DDE response.

        Returns:
            List of item name strings.

        Example::

            names = db.dde.get_item_names("Contact")
        """
        cmd = f'[GetItemNames("{category}", "{delim}")]'
        raw = self._conv.request(cmd)
        return [n.strip() for n in raw.split(delim) if n.strip()]

    def get_item_count(self, category: str) -> int:
        """Return the number of items in a category via DDE.

        Args:
            category: Commence category name.

        Returns:
            Item count as an integer.

        Example::

            count = db.dde.get_item_count("Contact")
        """
        cmd = f'[GetItemCount("{category}")]'
        raw = self._conv.request(cmd)
        return int(raw.strip())

    # -- UI commands ---------------------------------------------------------
    def show_item(
        self,
        category: str,
        item_name: str,
        *,
        form_name: str | None = None,
    ) -> None:
        """Open the detail form for an item in the Commence UI.

        Args:
            category: Commence category name.
            item_name: Item name (primary key).
            form_name: Optional form to use. If ``None``, the default
                detail form is used.

        Raises:
            ConversationError: If the item does not exist.

        Example::

            db.dde.show_item("Contact", "Jane Doe")
            db.dde.show_item("Contact", "Jane Doe", form_name="Contact Detail")
        """
        if form_name:
            cmd = f'[ShowItem("{category}", "{item_name}", "{form_name}")]'
        else:
            cmd = f'[ShowItem("{category}", "{item_name}")]'
        self._conv.execute(cmd)

    def show_view(self, view_name: str) -> None:
        """Open a named view in the Commence UI.

        Args:
            view_name: Name of the view to display.

        Raises:
            ConversationError: If the view does not exist.

        Example::

            db.dde.show_view("Active Contacts")
        """
        cmd = f'[ShowView("{view_name}")]'
        self._conv.execute(cmd)

    # -- triggers ------------------------------------------------------------
    def fire_trigger(self, trigger_name: str) -> None:
        """Fire a named Commence agent/trigger.

        Args:
            trigger_name: Name of the agent or trigger to fire.

        Raises:
            ConversationError: If the trigger does not exist.

        Example::

            db.dde.fire_trigger("Nightly Sync")
        """
        cmd = f'[FireTrigger("{trigger_name}")]'
        self._conv.execute(cmd)

    # -- database metadata ---------------------------------------------------
    def get_database_definition(self, *, delim: str = "|") -> dict[str, str]:
        """Return high-level database metadata via DDE.

        Args:
            delim: Delimiter for the DDE response.

        Returns:
            A dict with keys: ``name``, ``path``, ``version``, ``registered_user``, ``shared``.

        Example::

            info = db.dde.get_database_definition()
            print(info["name"], info["path"])
        """
        cmd = f'[GetDatabaseDefinition("{delim}")]'
        raw = self._conv.request(cmd)
        parts = [p.strip() for p in raw.split(delim)]
        keys = ("name", "path", "version", "registered_user", "shared")
        return dict(zip(keys, parts))

