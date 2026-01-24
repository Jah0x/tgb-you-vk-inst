from __future__ import annotations

from aiogram import Dispatcher, F
from aiogram.types import Message

from shared.services import add_accounts_to_grid, create_grid, list_grids, run_grid
from shared.services.errors import ServiceError
from shared.storage import Storage
from tg_bot.handlers.utils import format_accounts

GRIDS_HELP = (
    "Команды для сеток:\n"
    "• /grids create <grid_name> — создать новую сетку\n"
    "• /grids add-account <grid_name> <name1,name2|all> — добавить аккаунты в сетку\n"
    "• /grids list — показать сетки и их аккаунты\n"
    "• /grids run <grid_name> <name1,name2|all> — запустить сетку\n"
    "\n"
    "Имя сетки: латиница, цифры, символы _ . - (до 64 символов)."
)


async def _respond_with_grids(message: Message, store: Storage) -> None:
    grids = list_grids(store, message.chat.id).grids
    if not grids:
        await message.answer(
            "Сеток пока нет. Создайте сетку командой /grids create <grid_name>."
        )
        return

    lines = ["Ваши сетки:"]
    for grid in grids:
        lines.append(f"• {grid.name}")
        if grid.accounts:
            lines.append("  " + format_accounts(grid.accounts).replace("\n", "\n  "))
        else:
            lines.append("  (пока нет аккаунтов)")
    await message.answer("\n".join(lines))


def _service_error_response(exc: ServiceError) -> str:
    return "\n".join([exc.message, *exc.details]) if exc.details else exc.message


def register_grids(dp: Dispatcher, store: Storage) -> None:
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
            try:
                create_grid(store, message.chat.id, name)
            except ServiceError as exc:
                await message.answer(_service_error_response(exc))
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
            try:
                result = add_accounts_to_grid(store, message.chat.id, grid_name, parts[3])
            except ServiceError as exc:
                await message.answer(_service_error_response(exc))
                return

            added, skipped = result.added, result.skipped
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
            try:
                accounts = run_grid(store, message.chat.id, grid_name, parts[3])
            except ServiceError as exc:
                await message.answer(_service_error_response(exc))
                return

            await message.answer(
                "Запускаю сетку "
                f"{grid_name} для аккаунтов: {', '.join(accounts)}."
            )
            return

        await message.answer(GRIDS_HELP)
