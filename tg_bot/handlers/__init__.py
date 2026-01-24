from __future__ import annotations

from aiogram import Dispatcher

from shared.config import Settings
from tg_bot.handlers.accounts import register_accounts
from tg_bot.handlers.grids import register_grids
from tg_bot.handlers.help import register_help
from shared.storage import Storage


def register_handlers(dp: Dispatcher, store: Storage, settings: Settings) -> None:
    register_help(dp)
    register_accounts(dp, store, settings)
    register_grids(dp, store, settings)
