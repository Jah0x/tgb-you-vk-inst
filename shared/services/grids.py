from __future__ import annotations

import json
from dataclasses import dataclass

from redis import Redis
from rq import Queue

from shared.config import Settings
from shared.services.errors import ConflictError, NotFoundError, ValidationError
from shared.services.utils import parse_name_list, validate_names
from shared.storage import Storage


@dataclass(frozen=True)
class GridInfo:
    name: str
    accounts: list[str]


@dataclass(frozen=True)
class GridListResponse:
    grids: list[GridInfo]


@dataclass(frozen=True)
class GridCreateResponse:
    name: str


@dataclass(frozen=True)
class GridAccountsResponse:
    added: list[str]
    skipped: list[str]


@dataclass(frozen=True)
class GridRunResponse:
    accounts: list[str]
    actions: list[str]
    queued_jobs: int


def list_grids(store: Storage, chat_id: int) -> GridListResponse:
    grids = [GridInfo(name=name, accounts=accounts) for name, accounts in store.list_grids(chat_id)]
    return GridListResponse(grids=grids)


def create_grid(store: Storage, chat_id: int, name: str) -> GridCreateResponse:
    invalid = validate_names([name])
    if invalid:
        raise ValidationError(
            "Некорректное имя сетки.",
            ["Разрешены латиница, цифры и символы _ . -"],
        )
    if not store.create_grid(chat_id, name):
        raise ConflictError(
            f"Сетка {name} уже существует.",
            ["Используйте другое имя."],
        )
    return GridCreateResponse(name=name)


def delete_grid(store: Storage, chat_id: int, name: str) -> None:
    invalid = validate_names([name])
    if invalid:
        raise ValidationError(
            "Некорректное имя сетки.",
            ["Разрешены латиница, цифры и символы _ . -"],
        )
    if not store.delete_grid(chat_id, name):
        raise NotFoundError(
            "Сетка не найдена.",
            [f"Сетка {name} не найдена."],
        )


def _resolve_account_selection(
    store: Storage, chat_id: int, raw: str
) -> list[str]:
    raw = raw.strip()
    if raw.lower() == "all":
        accounts = store.list_accounts(chat_id)
        if not accounts:
            raise ValidationError(
                "Список аккаунтов пуст.",
                ["Добавьте аккаунты командой /accounts add."],
            )
        return accounts

    names = parse_name_list(raw)
    if not names:
        raise ValidationError(
            "Не удалось распознать список аккаунтов.",
            ["Пример: name1,name2 или all."],
        )

    invalid = validate_names(names)
    if invalid:
        raise ValidationError(
            "Некорректные имена аккаунтов.",
            [
                "Некорректные имена аккаунтов: " + ", ".join(invalid),
                "Используйте латиницу, цифры и символы _ . -",
            ],
        )

    found, missing = store.resolve_accounts(chat_id, names)
    if missing:
        raise NotFoundError(
            "Не найдены аккаунты.",
            [
                "Не найдены аккаунты: " + ", ".join(missing),
                "Добавьте их командой /accounts add.",
            ],
        )
    return found


def add_accounts_to_grid(
    store: Storage, chat_id: int, grid_name: str, raw_accounts: str
) -> GridAccountsResponse:
    invalid = validate_names([grid_name])
    if invalid:
        raise ValidationError(
            "Некорректное имя сетки.",
            ["Разрешены латиница, цифры и символы _ . -"],
        )
    if store.get_grid_id(chat_id, grid_name) is None:
        raise NotFoundError(
            f"Сетка {grid_name} не найдена.",
            ["Создайте её командой /grids create."],
        )

    accounts = _resolve_account_selection(store, chat_id, raw_accounts)
    added, skipped = store.add_accounts_to_grid(chat_id, grid_name, accounts)
    return GridAccountsResponse(added=added, skipped=skipped)


def run_grid(
    store: Storage,
    settings: Settings,
    chat_id: int,
    grid_name: str,
    raw_accounts: str,
) -> GridRunResponse:
    invalid = validate_names([grid_name])
    if invalid:
        raise ValidationError(
            "Некорректное имя сетки.",
            ["Разрешены латиница, цифры и символы _ . -"],
        )
    if store.get_grid_id(chat_id, grid_name) is None:
        raise NotFoundError(
            f"Сетка {grid_name} не найдена.",
            ["Создайте её командой /grids create."],
        )

    accounts = _resolve_account_selection(store, chat_id, raw_accounts)
    actions = store.list_grid_actions(chat_id, grid_name)
    if not actions:
        raise ValidationError(
            "Для сетки не настроены действия.",
            ["Добавьте действия для сетки перед запуском."],
        )

    redis_conn = Redis.from_url(settings.redis_url)
    grid_queue = Queue(settings.rq_grid_actions_queue, connection=redis_conn)
    action_names = [action.action for action in actions]
    for action in action_names:
        payload = json.dumps(
            {
                "grid_name": grid_name,
                "chat_id": chat_id,
                "accounts": accounts,
                "action": action,
            }
        )
        grid_queue.enqueue(
            "worker.tasks.grid_actions.apply_grid_action",
            payload,
        )

    return GridRunResponse(
        accounts=accounts,
        actions=action_names,
        queued_jobs=len(action_names),
    )


def schedule_grid_run(
    store: Storage,
    settings: Settings,
    chat_id: int,
    grid_name: str,
    raw_accounts: str,
) -> GridRunResponse:
    return run_grid(store, settings, chat_id, grid_name, raw_accounts)
