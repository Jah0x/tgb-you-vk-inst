from __future__ import annotations

from aiogram import Dispatcher, F
from aiogram.types import Message

from tg_bot.handlers.accounts import ACCOUNTS_HELP
from tg_bot.handlers.grids import GRIDS_HELP

HELP_TEXT = (
    "Доступные команды:\n"
    "/accounts — управление аккаунтами\n"
    "/grids — управление сетками\n"
    "/help — справка\n"
    "\n"
    + ACCOUNTS_HELP
    + "\n\n"
    + GRIDS_HELP
)


def register_help(dp: Dispatcher) -> None:
    @dp.message(F.text.in_({"/help", "/start"}))
    async def _help_handler(message: Message) -> None:
        await message.answer(HELP_TEXT)
