import json

from nicegui import ui

from pycommence2.gui import state
from pycommence2.gui.layout import frame


def register() -> None:
    """Register the detail page routes."""

    @ui.page('/show/{category}/{pk_value}')
    async def show_item(category: str, pk_value) -> None:
        worker = state.worker
        assert worker is not None
        pk_ = lambda s, c=category, pk=pk_value: s.dde.show_item(c, pk)
        await worker.run(pk_)
        with frame('Confirmation'):
            ui.label('Whhop').classes('text-2xl font-medium')

    @ui.page('/test')
    async def test() -> None:
        await do_test()


async def do_test():
    with frame('Test'):
        async def load_ip():
            ip = await ui.run_javascript('localStorage.getItem("desktopIp")')
            ip_input.value = ip or ""

        async def save_ip():
            value = json.dumps(ip_input.value)
            await ui.run_javascript(f'localStorage.setItem("desktopIp", {value})')

        ip_input = ui.input('Desktop IP')
        ui.button('Load', on_click=load_ip)
        ui.button('Save', on_click=save_ip)
