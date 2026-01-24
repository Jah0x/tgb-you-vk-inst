from __future__ import annotations

from aiogram import Dispatcher, F
from aiogram.types import Message

from shared.services import add_accounts, list_accounts
from shared.services.errors import ServiceError
from shared.storage import Storage
from shared.config import Settings
from tg_bot.handlers.permissions import Role, ensure_role
from tg_bot.handlers.utils import format_accounts

ACCOUNTS_HELP = (
    "Команды для аккаунтов:\n"
    "• /accounts add <name1,name2> — добавить один или несколько аккаунтов (админ)\n"
    "• /accounts list — показать список аккаунтов (админ/оператор)\n"
    "\n"
    "Имя аккаунта: латиница, цифры, символы _ . - (до 64 символов)."
)

ACCOUNT_ADD_HELP = (
    "Форма добавления аккаунта:\n"
    "1) Имя аккаунта (до 64 символов): латиница, цифры, символы _ . -\n"
    "2) Для нескольких аккаунтов используйте запятую.\n"
    "Пример: /accounts add brand_ru,brand_en\n"
    "\n"
    "Подсказки по cookies/токенам:\n"
    "• Бот не принимает cookies/токены в сообщениях.\n"
    "• Instagram/VK cookies задаются через файлы Netscape и переменные "
    "INSTAGRAM_COOKIES_PATH/VK_COOKIES_PATH.\n"
    "• Секреты и токены храните во внешнем хранилище (env/secret manager)."
)

def register_accounts(dp: Dispatcher, store: Storage, settings: Settings) -> None:
    @dp.message(F.text.startswith("/accounts"))
    async def _accounts_handler(message: Message) -> None:
        if not message.text:
            return

        parts = message.text.strip().split(maxsplit=2)
        if len(parts) == 1:
            await message.answer(ACCOUNTS_HELP)
            return

        action = parts[1].lower()
        if action == "list":
            if not await ensure_role(
                message,
                settings,
                {Role.ADMIN, Role.OPERATOR},
                "просмотр списка аккаунтов",
            ):
                return
            accounts = list_accounts(store, message.chat.id).accounts
            await message.answer(
                "Ваши аккаунты:\n" + format_accounts(accounts)
                if accounts
                else "Список аккаунтов пуст. Добавьте аккаунты командой /accounts add."
            )
            return

        if action == "add":
            if not await ensure_role(
                message,
                settings,
                {Role.ADMIN},
                "добавление аккаунтов",
            ):
                return
            if len(parts) < 3:
                await message.answer(
                    "Укажите аккаунты: /accounts add name1,name2\n"
                    + ACCOUNT_ADD_HELP
                    + "\n\n"
                    + ACCOUNTS_HELP
                )
                return

            try:
                result = add_accounts(store, message.chat.id, parts[2])
            except ServiceError as exc:
                response = [exc.message, *exc.details] if exc.details else [exc.message]
                await message.answer("\n".join(response))
                return

            added, skipped = result.added, result.skipped
            response_lines = []
            if added:
                response_lines.append("Добавлены: " + ", ".join(added))
            if skipped:
                response_lines.append("Уже были в списке: " + ", ".join(skipped))
            await message.answer("\n".join(response_lines))
            return

        await message.answer(ACCOUNTS_HELP)
