"""Export Dialog page — pick category, columns, filters → export to file."""

from __future__ import annotations

from nicegui import ui

from pycommence.gui.layout import frame, notify_error, notify_success
from pycommence.gui import state


def register() -> None:
    """Register the export page routes."""

    @ui.page("/export")
    async def export_page() -> None:
        with frame("Export"):
            if not state.worker or not state.worker.connected:
                ui.label("⚠ Not connected to Commence.")
                return
            await _render_export()


async def _render_export() -> None:
    """Render the export dialog."""
    worker = state.worker
    assert worker is not None

    try:
        categories = await worker.run(lambda s: s.schema.list_categories())
    except Exception as exc:
        notify_error(str(exc))
        return

    # State
    column_select = None
    field_names_cache: dict[str, list[str]] = {}

    with ui.card().classes("w-full"):
        ui.label("Export Data").classes("text-xl font-bold")

        with ui.column().classes("gap-4 w-full"):
            # Category
            cat_input = ui.select(
                categories, label="Category", with_input=True,
            ).classes("w-64")

            # Column picker (populated after category is selected)
            col_container = ui.column().classes("w-full")

            async def on_category_change(e) -> None:
                nonlocal column_select
                cat = e.value
                if not cat:
                    return
                col_container.clear()
                if cat not in field_names_cache:
                    try:
                        names = await worker.run(
                            lambda s, c=cat: s.schema.get_field_names(c)
                        )
                        field_names_cache[cat] = names
                    except Exception as exc:
                        notify_error(str(exc))
                        return
                with col_container:
                    column_select = ui.select(
                        field_names_cache[cat],
                        label="Columns (leave empty for all)",
                        multiple=True,
                    ).classes("w-full").props("use-chips")

            cat_input.on_value_change(on_category_change)

            # Format
            format_input = ui.radio(
                ["csv", "json", "excel"],
                value="csv",
            ).props("inline")

            # Max rows
            limit_input = ui.number(
                label="Max rows",
                value=50000,
                min=1,
                max=500000,
                step=1000,
            ).classes("w-48")

            # Canonical
            canonical_input = ui.switch("Canonical mode", value=True)

            # Output path
            path_input = ui.input(
                label="Output file path",
                placeholder="e.g. C:\\exports\\contacts.csv",
            ).classes("w-full")

    # -- Export button -------------------------------------------------------
    async def do_export() -> None:
        cat = cat_input.value
        if not cat:
            notify_error("Select a category.")
            return
        path = path_input.value
        if not path:
            notify_error("Enter an output file path.")
            return

        cols = column_select.value if column_select and column_select.value else None
        fmt = format_input.value
        limit = int(limit_input.value or 50000)
        canonical = canonical_input.value

        try:
            count = await worker.run(
                lambda s, c=cat, p=path, f=fmt, cl=cols, li=limit, cn=canonical: (
                    s.export(c, p, format=f, columns=cl, max_rows=li, canonical=cn)
                )
            )
            notify_success(f"Exported {count:,} rows to {path}")
        except Exception as exc:
            notify_error(f"Export failed: {exc}")

    ui.button("Export", icon="download", on_click=do_export).props(
        "color=primary size=lg"
    ).classes("mt-4")

    # -- Backup section ------------------------------------------------------
    ui.separator().classes("mt-6")

    with ui.card().classes("w-full"):
        ui.label("Full Backup").classes("text-xl font-bold")
        ui.label(
            "Export all (or selected) categories to a directory with schema metadata."
        ).classes("text-sm text-grey")

        with ui.column().classes("gap-4 w-full"):
            backup_cats = ui.select(
                categories,
                label="Categories (leave empty for all)",
                multiple=True,
            ).classes("w-full").props("use-chips")

            backup_dir = ui.input(
                label="Output directory",
                placeholder="e.g. C:\\backups\\2026-04-11",
            ).classes("w-full")

            backup_limit = ui.number(
                label="Max rows per category",
                value=50000,
                min=1,
            ).classes("w-48")

    async def do_backup() -> None:
        out = backup_dir.value
        if not out:
            notify_error("Enter an output directory.")
            return
        cats = list(backup_cats.value) if backup_cats.value else None
        limit = int(backup_limit.value or 50000)

        try:
            stats = await worker.run(
                lambda s, o=out, c=cats, li=limit: s.backup(
                    o, categories=c, max_rows_per_category=li,
                )
            )
            notify_success(
                f"Backup complete: {stats['categories_exported']} categories, "
                f"{stats['total_rows']:,} rows"
            )
        except Exception as exc:
            notify_error(f"Backup failed: {exc}")

    ui.button("Backup", icon="backup", on_click=do_backup).props(
        "color=secondary size=lg"
    ).classes("mt-4")


