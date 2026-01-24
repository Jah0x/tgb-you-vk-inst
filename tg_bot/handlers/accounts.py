from __future__ import annotations

from aiogram import Dispatcher, F
from aiogram.types import Message

from tg_bot.handlers.utils import format_accounts, parse_name_list, validate_names
from shared.storage import Storage

ACCOUNTS_HELP = (
    "Команды для аккаунтов:\n"
    "• /accounts add <name1,name2> — добавить один или несколько аккаунтов\n"
    "• /accounts list — показать список аккаунтов\n"
    "\n"
    "Имя аккаунта: латиница, цифры, символы _ . - (до 64 символов)."
)


def register_accounts(dp: Dispatcher, store: Storage) -> None:
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
            accounts = store.list_accounts(message.chat.id)
            await message.answer(
                "Ваши аккаунты:\n" + format_accounts(accounts)
                if accounts
                else "Список аккаунтов пуст. Добавьте аккаунты командой /accounts add."
            )
            return

        if action == "add":
            if len(parts) < 3:
                await message.answer(
                    "Укажите аккаунты: /accounts add name1,name2\n"
                    + ACCOUNTS_HELP
                )
                return

            names = parse_name_list(parts[2])
            if not names:
                await message.answer(
                    "Не удалось распознать аккаунты. Пример: /accounts add name1,name2"
                )
                return

            invalid = validate_names(names)
            if invalid:
                await message.answer(
                    "Некорректные имена: "
                    + ", ".join(invalid)
                    + "\n"
                    + ACCOUNTS_HELP
                )
                return

            added, skipped = store.add_accounts(message.chat.id, names)
            response_lines = []
            if added:
                response_lines.append("Добавлены: " + ", ".join(added))
            if skipped:
                response_lines.append("Уже были в списке: " + ", ".join(skipped))
            await message.answer("\n".join(response_lines))
            return

        await message.answer(ACCOUNTS_HELP)
