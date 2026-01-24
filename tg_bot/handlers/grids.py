from __future__ import annotations

from aiogram import Dispatcher, F
from aiogram.types import Message

from tg_bot.handlers.utils import format_accounts, parse_name_list, validate_names
from tg_bot.store import BotStore

GRIDS_HELP = (
    "Команды для сеток:\n"
    "• /grids create <grid_name> — создать новую сетку\n"
    "• /grids add-account <grid_name> <name1,name2|all> — добавить аккаунты в сетку\n"
    "• /grids list — показать сетки и их аккаунты\n"
    "• /grids run <grid_name> <name1,name2|all> — запустить сетку\n"
    "\n"
    "Имя сетки: латиница, цифры, символы _ . - (до 64 символов)."
)


async def _respond_with_grids(message: Message, store: BotStore) -> None:
    grids = store.list_grids(message.chat.id)
    if not grids:
        await message.answer(
            "Сеток пока нет. Создайте сетку командой /grids create <grid_name>."
        )
        return

    lines = ["Ваши сетки:"]
    for grid in grids:
        lines.append(f"• {grid.name}")
        if grid.account_names:
            lines.append("  " + format_accounts(grid.account_names).replace("\n", "\n  "))
        else:
            lines.append("  (пока нет аккаунтов)")
    await message.answer("\n".join(lines))


def _resolve_account_selection(
    message: Message, store: BotStore, raw: str
) -> tuple[list[str], list[str] | None]:
    raw = raw.strip()
    if raw.lower() == "all":
        accounts = store.list_accounts(message.chat.id)
        if not accounts:
            return [], ["Список аккаунтов пуст. Добавьте аккаунты командой /accounts add."]
        return accounts, None

    names = parse_name_list(raw)
    if not names:
        return [], [
            "Не удалось распознать список аккаунтов. Пример: name1,name2 или all."
        ]

    invalid = validate_names(names)
    if invalid:
        return [], [
            "Некорректные имена аккаунтов: " + ", ".join(invalid),
            "Используйте латиницу, цифры и символы _ . -",
        ]

    found, missing = store.resolve_accounts(message.chat.id, names)
    if missing:
        return [], [
            "Не найдены аккаунты: " + ", ".join(missing),
            "Добавьте их командой /accounts add.",
        ]
    return found, None


def register_grids(dp: Dispatcher, store: BotStore) -> None:
    @dp.message(F.text.startswith("/grids"))
    async def _grids_handler(message: Message) -> None:
        if not message.text:
            return

        parts = message.text.strip().split(maxsplit=3)
        if len(parts) == 1:
            await message.answer(GRIDS_HELP)
            return

        action = parts[1].lower()
        if action == "list":
            await _respond_with_grids(message, store)
            return

        if action == "create":
            if len(parts) < 3:
                await message.answer(
                    "Укажите имя сетки: /grids create grid_name\n" + GRIDS_HELP
                )
                return

            name = parts[2].strip()
            invalid = validate_names([name])
            if invalid:
                await message.answer(
                    "Некорректное имя сетки. "
                    "Разрешены латиница, цифры и символы _ . -"
                )
                return

            if not store.create_grid(message.chat.id, name):
                await message.answer(
                    f"Сетка {name} уже существует. Используйте другое имя."
                )
                return

            await message.answer(
                f"Сетка {name} создана. Добавьте аккаунты командой /grids add-account."
            )
            return

        if action == "add-account":
            if len(parts) < 4:
                await message.answer(
                    "Формат: /grids add-account <grid_name> <name1,name2|all>\n"
                    + GRIDS_HELP
                )
                return

            grid_name = parts[2].strip()
            invalid = validate_names([grid_name])
            if invalid:
                await message.answer(
                    "Некорректное имя сетки. "
                    "Разрешены латиница, цифры и символы _ . -"
                )
                return

            grid = store.get_grid(message.chat.id, grid_name)
            if not grid:
                await message.answer(
                    f"Сетка {grid_name} не найдена. Создайте её командой /grids create."
                )
                return

            accounts, errors = _resolve_account_selection(message, store, parts[3])
            if errors:
                await message.answer("\n".join(errors))
                return

            added, skipped = store.add_accounts_to_grid(
                message.chat.id, grid_name, accounts
            )
            response_lines = []
            if added:
                response_lines.append("Добавлены: " + ", ".join(added))
            if skipped:
                response_lines.append("Уже были в сетке: " + ", ".join(skipped))
            await message.answer("\n".join(response_lines))
            return

        if action == "run":
            if len(parts) < 4:
                await message.answer(
                    "Формат: /grids run <grid_name> <name1,name2|all>\n" + GRIDS_HELP
                )
                return

            grid_name = parts[2].strip()
            invalid = validate_names([grid_name])
            if invalid:
                await message.answer(
                    "Некорректное имя сетки. "
                    "Разрешены латиница, цифры и символы _ . -"
                )
                return

            grid = store.get_grid(message.chat.id, grid_name)
            if not grid:
                await message.answer(
                    f"Сетка {grid_name} не найдена. Создайте её командой /grids create."
                )
                return

            accounts, errors = _resolve_account_selection(message, store, parts[3])
            if errors:
                await message.answer("\n".join(errors))
                return

            await message.answer(
                "Запускаю сетку "
                f"{grid_name} для аккаунтов: {', '.join(accounts)}."
            )
            return

        await message.answer(GRIDS_HELP)
