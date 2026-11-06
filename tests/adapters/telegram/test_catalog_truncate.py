"""Opt-in truncate_dialogs: stop at max_dialogs instead of failing with CATALOG_LIMIT."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from telethon import functions

from telegram_mcp.adapters.config import Settings
from telegram_mcp.adapters.telegram import TelegramBackend, TelegramRuntime
from tests.support.catalog import dialog_page, gateway, pinned_page


def test_truncate_dialogs_is_off_by_default() -> None:
    assert Settings().truncate_dialogs is False


async def test_truncate_keeps_first_dialogs_of_a_page() -> None:
    chats, client, _ = gateway(lambda _: dialog_page([1, 2, 3]), maximum=2, truncate=True)
    result, _ = await chats.catalog()
    assert len(result) == 2
    assert len(chats.cache) == 2
    dialog_calls = [
        c
        for c in client.await_args_list
        if isinstance(c.args[0], functions.messages.GetDialogsRequest)
    ]
    assert len(dialog_calls) == 1
    await chats.close()


async def test_truncate_stops_after_pinned_dialogs_fill_the_limit() -> None:
    settings = Settings(max_dialogs=1, truncate_dialogs=True)

    def respond(request):
        if isinstance(request, functions.updates.GetStateRequest):
            return None
        if isinstance(request, functions.messages.GetDialogFiltersRequest):
            return SimpleNamespace(filters=[])
        if isinstance(request, functions.messages.GetDialogsRequest):
            raise AssertionError("no dialog pages once pinned dialogs fill the limit")
        return pinned_page([1, 2])

    client = AsyncMock(side_effect=respond)
    client.is_connected = lambda: True
    backend = TelegramBackend(
        settings, runtime=TelegramRuntime(settings, client=client), chat_cache={}
    )
    result, _ = await backend.catalog()
    assert len(result) == 1
    await backend.close()
