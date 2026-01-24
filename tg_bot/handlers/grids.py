from __future__ import annotations

from aiogram import Dispatcher, F
from aiogram.types import Message

from shared.config import Settings
from shared.services import (
    add_accounts_to_grid,
    add_grid_action,
    create_grid,
    delete_grid,
    list_grids,
    list_grid_actions,
    remove_accounts_from_grid,
    remove_grid_action,
    schedule_grid_run,
)
from shared.services.errors import ServiceError
from shared.storage import Storage
from tg_bot.handlers.permissions import Role, ensure_role
from tg_bot.handlers.utils import format_accounts

GRIDS_HELP = (
    "Команды для сеток:\n"
    "• /grids create <grid_name> — создать новую сетку (админ)\n"
    "• /grids add-account <grid_name> <name1,name2|all> — добавить аккаунты в сетку (админ)\n"
    "• /grids remove-account <grid_name> <name1,name2|all> — удалить аккаунты из сетки (админ)\n"
    "• /grids add-action <grid_name> <action> — добавить действие для сетки (админ)\n"
    "• /grids remove-action <grid_name> <action> — удалить действие из сетки (админ)\n"
    "• /grids delete <grid_name> — удалить сетку (админ)\n"
    "• /grids list — показать сетки и их аккаунты (админ/оператор)\n"
    "• /grids actions <grid_name> — показать действия сетки (админ/оператор)\n"
    "• /grids run <grid_name> <name1,name2|all> — запустить сетку (админ/оператор)\n"
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


def register_grids(dp: Dispatcher, store: Storage, settings: Settings) -> None:
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
            if not await ensure_role(
                message,
                settings,
                {Role.ADMIN, Role.OPERATOR},
                "просмотр сеток",
            ):
                return
            await _respond_with_grids(message, store)
            return

        if action == "actions":
            if not await ensure_role(
                message,
                settings,
                {Role.ADMIN, Role.OPERATOR},
                "просмотр действий сеток",
            ):
                return
            if len(parts) < 3:
                await message.answer(
                    "Формат: /grids actions <grid_name>\n" + GRIDS_HELP
                )
                return

            grid_name = parts[2].strip()
            try:
                result = list_grid_actions(store, message.chat.id, grid_name)
            except ServiceError as exc:
                await message.answer(_service_error_response(exc))
                return

            if result.actions:
                await message.answer(
                    "Действия сетки "
                    f"{grid_name}: {', '.join(result.actions)}."
                )
            else:
                await message.answer(f"В сетке {grid_name} пока нет действий.")
            return

        if action == "create":
            if not await ensure_role(
                message,
                settings,
                {Role.ADMIN},
                "создание сеток",
            ):
                return
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

        if action == "delete":
            if not await ensure_role(
                message,
                settings,
                {Role.ADMIN},
                "удаление сеток",
            ):
                return
            if len(parts) < 3:
                await message.answer("Формат: /grids delete <grid_name>\n" + GRIDS_HELP)
                return

            name = parts[2].strip()
            try:
                delete_grid(store, message.chat.id, name)
            except ServiceError as exc:
                await message.answer(_service_error_response(exc))
                return

            await message.answer(f"Сетка {name} удалена.")
            return

        if action == "add-account":
            if not await ensure_role(
                message,
                settings,
                {Role.ADMIN},
                "добавление аккаунтов в сетки",
            ):
                return
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

        if action == "add-action":
            if not await ensure_role(
                message,
                settings,
                {Role.ADMIN},
                "добавление действий в сетки",
            ):
                return
            if len(parts) < 4:
                await message.answer(
                    "Формат: /grids add-action <grid_name> <action>\n" + GRIDS_HELP
                )
                return

            grid_name = parts[2].strip()
            action_name = parts[3].strip()
            try:
                add_grid_action(store, message.chat.id, grid_name, action_name)
            except ServiceError as exc:
                await message.answer(_service_error_response(exc))
                return

            await message.answer(
                f"Действие {action_name} добавлено в сетку {grid_name}."
            )
            return

        if action == "remove-account":
            if not await ensure_role(
                message,
                settings,
                {Role.ADMIN},
                "удаление аккаунтов из сеток",
            ):
                return
            if len(parts) < 4:
                await message.answer(
                    "Формат: /grids remove-account <grid_name> <name1,name2|all>\n"
                    + GRIDS_HELP
                )
                return

            grid_name = parts[2].strip()
            try:
                result = remove_accounts_from_grid(
                    store, message.chat.id, grid_name, parts[3]
                )
            except ServiceError as exc:
                await message.answer(_service_error_response(exc))
                return

            removed, skipped = result.removed, result.skipped
            response_lines = []
            if removed:
                response_lines.append("Удалены из сетки: " + ", ".join(removed))
            if skipped:
                response_lines.append("Не были в сетке: " + ", ".join(skipped))
            await message.answer("\n".join(response_lines))
            return

        if action == "remove-action":
            if not await ensure_role(
                message,
                settings,
                {Role.ADMIN},
                "удаление действий из сеток",
            ):
                return
            if len(parts) < 4:
                await message.answer(
                    "Формат: /grids remove-action <grid_name> <action>\n" + GRIDS_HELP
                )
                return

            grid_name = parts[2].strip()
            action_name = parts[3].strip()
            try:
                remove_grid_action(store, message.chat.id, grid_name, action_name)
            except ServiceError as exc:
                await message.answer(_service_error_response(exc))
                return

            await message.answer(
                f"Действие {action_name} удалено из сетки {grid_name}."
            )
            return

        if action == "run":
            if not await ensure_role(
                message,
                settings,
                {Role.ADMIN, Role.OPERATOR},
                "запуск сеток",
            ):
                return
            if len(parts) < 4:
                await message.answer(
                    "Формат: /grids run <grid_name> <name1,name2|all>\n" + GRIDS_HELP
                )
                return

            grid_name = parts[2].strip()
            try:
                result = schedule_grid_run(
                    store, settings, message.chat.id, grid_name, parts[3]
                )
            except ServiceError as exc:
                await message.answer(_service_error_response(exc))
                return

            await message.answer(
                "Запускаю сетку "
                f"{grid_name} для аккаунтов: {', '.join(result.accounts)}.\n"
                f"Действия: {', '.join(result.actions)}."
            )
            return

        await message.answer(GRIDS_HELP)
