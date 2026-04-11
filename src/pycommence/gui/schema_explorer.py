"""Schema Explorer page — field definitions table and connections tree."""

from __future__ import annotations

from nicegui import ui

from pycommence.gui.layout import frame, notify_error
from pycommence.gui import state


def register() -> None:
    """Register the schema explorer page routes."""

    @ui.page("/schema")
    async def schema_index() -> None:
        with frame("Schema Explorer"):
            if not state.worker or not state.worker.connected:
                ui.label("⚠ Not connected to Commence.")
                return
            await _render_schema_explorer()


async def _render_schema_explorer() -> None:
    """Render the schema explorer with category picker."""
    worker = state.worker
    assert worker is not None

    try:
        categories = await worker.run(lambda s: s.schema.list_categories())
    except Exception as exc:
        notify_error(str(exc))
        return

    content = ui.column().classes("w-full gap-4")

    async def on_category_change(e) -> None:
        cat_name = e.value
        if not cat_name:
            return
        content.clear()
        with content:
            await _render_category_schema(cat_name)

    ui.select(
        categories, label="Category", with_input=True,
        on_change=on_category_change,
    ).classes("w-64")

    # Placeholder
    with content:
        ui.label("Select a category above to view its schema.").classes("text-grey")


async def _render_category_schema(category: str) -> None:
    """Render fields and connections for a single category."""
    worker = state.worker
    assert worker is not None

    # -- Fields table --------------------------------------------------------
    try:
        fields = await worker.run(
            lambda s, c=category: s.schema.get_fields(c)
        )
    except Exception as exc:
        notify_error(f"Failed to load fields: {exc}")
        return

    ui.label(f"Fields — {category} ({len(fields)})").classes("text-lg font-bold")

    field_rows = []
    for i, f in enumerate(fields, 1):
        flags = []
        if f.is_mandatory:
            flags.append("mandatory")
        if f.is_combo:
            flags.append("combo")
        if f.is_shared:
            flags.append("shared")
        if f.is_recurring:
            flags.append("recurring")
        field_rows.append({
            "num": i,
            "name": f.name,
            "type": f.field_type.name,
            "max_chars": f.max_chars if f.max_chars else "",
            "default": f.default,
            "flags": ", ".join(flags),
        })

    field_columns = [
        {"name": "num", "label": "#", "field": "num", "align": "right", "sortable": True},
        {"name": "name", "label": "Field", "field": "name", "align": "left", "sortable": True},
        {"name": "type", "label": "Type", "field": "type", "align": "left", "sortable": True},
        {"name": "max_chars", "label": "Max Chars", "field": "max_chars", "align": "right"},
        {"name": "default", "label": "Default", "field": "default", "align": "left"},
        {"name": "flags", "label": "Flags", "field": "flags", "align": "left"},
    ]

    ui.table(
        columns=field_columns,
        rows=field_rows,
        row_key="name",
        pagination={"rowsPerPage": 50, "sortBy": "num"},
    ).classes("w-full")

    # -- Connections ---------------------------------------------------------
    try:
        connections = await worker.run(
            lambda s, c=category: s.schema.get_connection_names(c)
        )
    except Exception as exc:
        notify_error(f"Failed to load connections: {exc}")
        return

    if connections:
        ui.label(
            f"Connections — {category} ({len(connections)})"
        ).classes("text-lg font-bold mt-4")

        conn_rows = []
        for i, c in enumerate(connections, 1):
            conn_rows.append({
                "num": i,
                "name": c.name,
                "to_category": c.to_category,
            })

        conn_columns = [
            {"name": "num", "label": "#", "field": "num", "align": "right"},
            {"name": "name", "label": "Connection", "field": "name", "align": "left", "sortable": True},
            {"name": "to_category", "label": "To Category", "field": "to_category", "align": "left", "sortable": True},
        ]

        ui.table(
            columns=conn_columns,
            rows=conn_rows,
            row_key="name",
        ).classes("w-full")
    else:
        ui.label(f"No connections for {category}.").classes("text-grey mt-2")

    # -- Row count -----------------------------------------------------------
    try:
        count = await worker.run(
            lambda s, c=category: s.schema.get_row_count(c)
        )
        ui.label(f"{count:,} rows in {category}").classes("text-sm text-grey mt-2")
    except Exception:
        pass

