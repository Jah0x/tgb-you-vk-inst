from __future__ import annotations

import shlex
from typing import Any

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
from shared.services.grids import GridActionConfigPayload
from shared.services.errors import ServiceError
from shared.storage import Storage
from tg_bot.handlers.permissions import Role, ensure_role
from tg_bot.handlers.utils import format_accounts

GRIDS_HELP = (
    "Команды для сеток:\n"
    "• /grids create <grid_name> — создать новую сетку (админ)\n"
    "• /grids add-account <grid_name> <name1,name2|all> — добавить аккаунты в сетку (админ)\n"
    "• /grids remove-account <grid_name> <name1,name2|all> — удалить аккаунты из сетки (админ)\n"
    "• /grids add-action <grid_name> <action> [--count=N] [--jitter=on|off] "
    "[--min=SEC] [--max=SEC] [--account=all|name1,name2] "
    "[--alloc-count=N|--alloc-percent=N|--alloc-accounts=name1,name2]\n"
    "  — добавить действие для сетки (админ)\n"
    "• /grids remove-action <grid_name> <action> — удалить действие из сетки (админ)\n"
    "• /grids delete <grid_name> — удалить сетку (админ)\n"
    "• /grids list — показать сетки и их аккаунты (админ/оператор)\n"
    "• /grids actions <grid_name> — показать действия сетки (админ/оператор)\n"
    "• /grids run <grid_name> <name1,name2|all> — запустить сетку (админ/оператор)\n"
    "\n"
    "Имя сетки: латиница, цифры, символы _ . - (до 64 символов)."
)


def _format_grid_action_config(config: GridActionConfigPayload | None) -> str:
    if not config:
        return ""
    parts: list[str] = []
    if config.type:
        parts.append(f"type={config.type}")
    if config.payload:
        parts.append(f"payload={config.payload}")
    if config.min_delay_s is not None and config.max_delay_s is not None:
        parts.append(f"delay={config.min_delay_s}-{config.max_delay_s}s")
    if config.random_jitter_enabled is not None:
        parts.append(
            "jitter=on" if config.random_jitter_enabled else "jitter=off"
        )
    if config.account_selector:
        parts.append(f"accounts={config.account_selector}")
    if config.account_allocation and config.account_allocation_value:
        parts.append(
            f"allocation={config.account_allocation}:{config.account_allocation_value}"
        )
    return " (" + ", ".join(parts) + ")" if parts else ""


def _parse_action_config(tokens: list[str]) -> GridActionConfigPayload | None:
    if not tokens:
        return None
    payload: dict[str, Any] = {}
    min_delay_s: int | None = None
    max_delay_s: int | None = None
    random_jitter_enabled: bool | None = None
    account_selector: str | None = None
    account_allocation: str | None = None
    account_allocation_value: str | None = None

    for token in tokens:
        if token.startswith("--count="):
            value = token.split("=", 1)[1]
            if value.isdigit():
                payload["count"] = int(value)
            else:
                payload["count"] = value
        elif token.startswith("--min="):
            value = token.split("=", 1)[1]
            min_delay_s = int(value) if value.isdigit() else None
        elif token.startswith("--max="):
            value = token.split("=", 1)[1]
            max_delay_s = int(value) if value.isdigit() else None
        elif token.startswith("--jitter="):
            value = token.split("=", 1)[1].lower()
            if value in {"on", "true", "yes", "1"}:
                random_jitter_enabled = True
            elif value in {"off", "false", "no", "0"}:
                random_jitter_enabled = False
        elif token.startswith("--account="):
            account_selector = token.split("=", 1)[1]
        elif token.startswith("--alloc-count="):
            account_allocation = "count"
            account_allocation_value = token.split("=", 1)[1]
        elif token.startswith("--alloc-percent="):
            account_allocation = "percent"
            account_allocation_value = token.split("=", 1)[1]
        elif token.startswith("--alloc-accounts="):
            account_allocation = "explicit_list"
            account_allocation_value = token.split("=", 1)[1]
    return GridActionConfigPayload(
        type=None,
        payload=payload or None,
        min_delay_s=min_delay_s,
        max_delay_s=max_delay_s,
        random_jitter_enabled=random_jitter_enabled,
        account_selector=account_selector,
        account_allocation=account_allocation,
        account_allocation_value=account_allocation_value,
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
                lines = [f"Действия сетки {grid_name}:"]
                for action_info in result.actions:
                    config_payload = None
                    if action_info.config:
                        config_payload = GridActionConfigPayload(
                            type=action_info.config.type,
                            payload=action_info.config.payload,
                            min_delay_s=action_info.config.min_delay_s,
                            max_delay_s=action_info.config.max_delay_s,
                            random_jitter_enabled=action_info.config.random_jitter_enabled,
                            account_selector=action_info.config.account_selector,
                            account_allocation=action_info.config.account_allocation,
                            account_allocation_value=action_info.config.account_allocation_value,
                        )
                    lines.append(
                        f"• {action_info.action}"
                        f"{_format_grid_action_config(config_payload)}"
                    )
                await message.answer("\n".join(lines))
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
            tokens = shlex.split(parts[3].strip())
            if not tokens:
                await message.answer(
                    "Формат: /grids add-action <grid_name> <action>\n" + GRIDS_HELP
                )
                return
            action_name = tokens[0]
            config_payload = _parse_action_config(tokens[1:])
            try:
                add_grid_action(
                    store,
                    message.chat.id,
                    grid_name,
                    action_name,
                    config=config_payload,
                )
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
