from __future__ import annotations

from aiogram import Dispatcher, F
from aiogram.types import Message

from tg_bot.handlers.accounts import ACCOUNTS_HELP
from tg_bot.handlers.complaints import COMPLAINTS_HELP
from tg_bot.handlers.comments import COMMENTS_HELP
from tg_bot.handlers.grids import GRIDS_HELP

ACCESS_RULES = (
    "Роли и доступ:\n"
    "• Админ: управление аккаунтами и сетками (создание, добавление, запуск).\n"
    "• Оператор: просмотр списков и запуск сеток.\n"
    "Роли задаются через переменные окружения ADMIN_CHAT_IDS и "
    "OPERATOR_CHAT_IDS (список chat_id через запятую)."
)

HELP_TEXT = (
    "Доступные команды:\n"
    "/accounts — управление аккаунтами\n"
    "/comments — управление комментариями\n"
    "/complaints — управление жалобами\n"
    "/grids — управление сетками\n"
    "/help — справка\n"
    "\n"
    + ACCOUNTS_HELP
    + "\n\n"
    + COMMENTS_HELP
    + "\n\n"
    + COMPLAINTS_HELP
    + "\n\n"
    + GRIDS_HELP
    + "\n\n"
    + ACCESS_RULES
)


def register_help(dp: Dispatcher) -> None:
    @dp.message(F.text.in_({"/help", "/start"}))
    async def _help_handler(message: Message) -> None:
        await message.answer(HELP_TEXT)
