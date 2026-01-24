from __future__ import annotations

from aiogram import Dispatcher

from tg_bot.handlers.accounts import register_accounts
from tg_bot.handlers.grids import register_grids
from tg_bot.handlers.help import register_help
from tg_bot.store import BotStore


def register_handlers(dp: Dispatcher, store: BotStore) -> None:
    register_help(dp)
    register_accounts(dp, store)
    register_grids(dp, store)
