from pathlib import Path

from nicegui import ui

from pycommence2 import FieldType
from pycommence2.config import PycommenceSettings, Sort
from pycommence2.gui.layout import frame, notify_error
from pycommence2.gui import state
from pycommence2.gui.emailer import Email

RowId = str

def query_f_settings():
    ...

def make_query(session, category):
    qb = session.query(category).limit(200)
    qb = qb.apply_settings()
    return qb.execute()


def register():
    @ui.page('/emailer')
    async def emailer_page():
        with (frame('Emailer')):
            # Step 1: Select category
            if not state.worker or not state.worker.connected:
                ui.label('⚠ Not connected to Commence.')
                return
            try:
                categories = await state.worker.run(lambda s: s.schema.list_categories())
            except Exception as exc:
                notify_error(str(exc))
                return
            category_select = ui.select(categories, label='Category', with_input=True).classes('w-64')
            record_select = ui.select([], label='Record', with_input=True).classes('w-96')
            email_field_select = ui.select([], label='Email Fields', multiple=True).classes('w-96')
            subject_input = ui.input(label='Subject').classes('w-full')
            body_input = ui.textarea(label='Body').classes('w-full h-32')
            stock_row = ui.row().classes('gap-2')
            # Placeholders for stock text buttons
            with stock_row:
                ui.button(
                    'Insert Greeting',
                    on_click=lambda: body_input.set_value((body_input.value or '') + '\n[Greeting Placeholder]')
                )
                ui.button(
                    'Insert Signature',
                    on_click=lambda: body_input.set_value((body_input.value or '') + '\n[Signature Placeholder]')
                )
            # State
            state_dict = {'fields': [], 'records': {}, 'email_fields': []}

            # Handlers
            async def on_category_change(e):
                cat = e.value
                if not cat:
                    record_select.options = []
                    email_field_select.options = []
                    return
                try:
                    # Get field definitions
                    field_defs = await state.worker.run(lambda s, c=cat: s.schema.get_fields(c))
                    state_dict['fields'] = field_defs
                    # Find email fields
                    email_fields = [f.name for f in field_defs if f.field_type is FieldType.EMAIL]
                    name_field = next((f.name for f in field_defs if f.field_type is FieldType.NAME)) or None
                    if not name_field:
                        raise ValueError("No name field found in category")
                    state_dict['email_fields'] = email_fields
                    email_field_select.set_options(email_fields)


                    records = await state.worker.run(make_query, cat)
                    state_dict['records'] = {r.row_id: r for r in records}
                    options = {r.row_id: r[name_field] for r in records}
                    record_select.set_options(options)


                except Exception as exc:
                    notify_error(f"Failed to load category data: {exc}")
                    record_select.options = []
                    email_field_select.options = []

            async def on_record_change(e):
                if not e.value:
                    return
                email_fields = state_dict['email_fields']
                record = state_dict['records'][e.value]
                options = {}
                seen = set()
                for f in email_fields:
                    email = record.get(f)
                    if email and email not in seen:
                        options[f] = f'{f}:{email}'
                        seen.add(email)
                email_field_select.set_options(options)

            category_select.on_value_change(on_category_change)
            record_select.on_value_change(on_record_change)

            def on_prepare_email(e):
                # Get selected record
                record = state_dict['records'][record_select.value]
                if not record:
                    ui.notify('Select a record', type='warning')
                    return
                # Get selected email fields
                selected_fields = email_field_select.value or []
                if not selected_fields:
                    ui.notify('Select at least one email field', type='warning')
                    return
                # Collect email addresses
                addresses = []
                for f in selected_fields:
                    val = record.get(f, None)
                    if val:
                        addresses.append(val)
                if not addresses:
                    ui.notify('No email addresses found in selected fields', type='warning')
                    return
                # Prepare Email dataclass (just first address for now)
                email = Email(
                    to_address=';'.join(addresses),
                    subject=subject_input.value or '',
                    body=body_input.value or '',
                )
                ui.notify(f"Prepared email to: {email.to_address}")

            ui.button('Prepare Email', icon='email', on_click=on_prepare_email).props('color=primary')
