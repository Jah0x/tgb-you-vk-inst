from __future__ import annotations

import json
import random
from datetime import timedelta
from dataclasses import dataclass
from typing import Any

from redis import Redis
from rq import Queue

from shared.config import Settings
from shared.services.errors import ConflictError, NotFoundError, ValidationError
from shared.services.utils import parse_name_list, validate_names
from shared.storage import Storage
from shared.models import GridActionConfig


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
class GridAccountsRemoveResponse:
    removed: list[str]
    skipped: list[str]


@dataclass(frozen=True)
class GridRunResponse:
    accounts: list[str]
    actions: list[str]
    queued_jobs: int


@dataclass(frozen=True)
class GridActionsResponse:
    actions: list["GridActionInfo"]


@dataclass(frozen=True)
class GridActionConfigPayload:
    type: str | None
    payload: dict[str, Any] | None
    min_delay_s: int | None
    max_delay_s: int | None
    random_jitter_enabled: bool | None
    account_selector: str | None
    account_allocation: str | None
    account_allocation_value: str | None


@dataclass(frozen=True)
class GridActionConfigInfo:
    type: str
    payload: dict[str, Any] | None
    min_delay_s: int | None
    max_delay_s: int | None
    random_jitter_enabled: bool
    account_selector: str | None
    account_allocation: str | None
    account_allocation_value: str | None


@dataclass(frozen=True)
class GridActionInfo:
    action: str
    config: GridActionConfigInfo | None


@dataclass(frozen=True)
class GridActionResponse:
    action: GridActionInfo


SPAM_ACTION_TYPES = {"spam_post", "spam_comment", "spam_message"}
COMPLAINT_REASONS = {"spam", "fraud", "violence", "adult", "other"}
ALLOWED_GRID_ACTION_TYPES = {"reaction", "comment", "complaint", *SPAM_ACTION_TYPES}
SPAM_PAYLOAD_FIELDS = {"files", "text", "album_url", "text_template", "random_variants"}
ACTION_PAYLOAD_FIELDS = {
    "reaction": {"count"},
    "comment": {"text"},
    "complaint": {"reason", "target", "selection", "timers", "delay"},
    "spam_post": SPAM_PAYLOAD_FIELDS,
    "spam_comment": SPAM_PAYLOAD_FIELDS,
    "spam_message": SPAM_PAYLOAD_FIELDS,
}


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


def list_grid_actions(store: Storage, chat_id: int, grid_name: str) -> GridActionsResponse:
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
    actions = []
    for action, config in store.list_grid_actions_with_configs(chat_id, grid_name):
        config_info = _format_action_config_info(config)
        actions.append(GridActionInfo(action=action.action, config=config_info))
    return GridActionsResponse(actions=actions)


def add_grid_action(
    store: Storage,
    chat_id: int,
    grid_name: str,
    action: str,
    config: GridActionConfigPayload | None = None,
) -> GridActionResponse:
    invalid = validate_names([grid_name, action])
    if invalid:
        raise ValidationError(
            "Некорректные значения.",
            ["Разрешены латиница, цифры и символы _ . -"],
        )
    if store.get_grid_id(chat_id, grid_name) is None:
        raise NotFoundError(
            f"Сетка {grid_name} не найдена.",
            ["Создайте её командой /grids create."],
        )
    grid_action_id = store.add_grid_action(chat_id, grid_name, action)
    if grid_action_id is None:
        raise ConflictError(
            "Действие уже добавлено.",
            [f"Действие {action} уже есть в сетке {grid_name}."],
        )
    config_info = _validate_grid_action_config(action, config)
    if config_info:
        store.upsert_grid_action_config(
            grid_action_id=grid_action_id,
            action_type=config_info.type,
            payload_json=json.dumps(config_info.payload) if config_info.payload else None,
            min_delay_s=config_info.min_delay_s,
            max_delay_s=config_info.max_delay_s,
            random_jitter_enabled=config_info.random_jitter_enabled,
            account_selector=config_info.account_selector,
            account_allocation=config_info.account_allocation,
            account_allocation_value=config_info.account_allocation_value,
        )
    return GridActionResponse(
        action=GridActionInfo(action=action, config=config_info)
    )


def update_grid_action_materials(
    store: Storage,
    chat_id: int,
    grid_name: str,
    action: str,
    payload: dict[str, Any],
) -> GridActionResponse:
    invalid = validate_names([grid_name, action])
    if invalid:
        raise ValidationError(
            "Некорректные значения.",
            ["Разрешены латиница, цифры и символы _ . -"],
        )
    if store.get_grid_id(chat_id, grid_name) is None:
        raise NotFoundError(
            f"Сетка {grid_name} не найдена.",
            ["Создайте её командой /grids create."],
        )
    action_entry = store.get_grid_action_with_config(chat_id, grid_name, action)
    if action_entry is None:
        raise NotFoundError(
            "Действие не найдено.",
            [f"Действие {action} не найдено в сетке {grid_name}."],
        )
    grid_action, existing_config = action_entry
    config_payload = GridActionConfigPayload(
        type=existing_config.type if existing_config else action,
        payload=payload,
        min_delay_s=existing_config.min_delay_s if existing_config else None,
        max_delay_s=existing_config.max_delay_s if existing_config else None,
        random_jitter_enabled=existing_config.random_jitter_enabled if existing_config else False,
        account_selector=existing_config.account_selector if existing_config else None,
        account_allocation=existing_config.account_allocation if existing_config else None,
        account_allocation_value=existing_config.account_allocation_value if existing_config else None,
    )
    config_info = _validate_grid_action_config(action, config_payload)
    if config_info is None:
        raise ValidationError(
            "Некорректные параметры действия.",
            ["Payload должен быть объектом."],
        )
    store.upsert_grid_action_config(
        grid_action_id=grid_action.id,
        action_type=config_info.type,
        payload_json=json.dumps(config_info.payload) if config_info.payload else None,
        min_delay_s=config_info.min_delay_s,
        max_delay_s=config_info.max_delay_s,
        random_jitter_enabled=config_info.random_jitter_enabled,
        account_selector=config_info.account_selector,
        account_allocation=config_info.account_allocation,
        account_allocation_value=config_info.account_allocation_value,
    )
    return GridActionResponse(
        action=GridActionInfo(action=action, config=config_info)
    )


def remove_grid_action(store: Storage, chat_id: int, grid_name: str, action: str) -> None:
    invalid = validate_names([grid_name, action])
    if invalid:
        raise ValidationError(
            "Некорректные значения.",
            ["Разрешены латиница, цифры и символы _ . -"],
        )
    if store.get_grid_id(chat_id, grid_name) is None:
        raise NotFoundError(
            f"Сетка {grid_name} не найдена.",
            ["Создайте её командой /grids create."],
        )
    if not store.remove_grid_action(chat_id, grid_name, action):
        raise NotFoundError(
            "Действие не найдено.",
            [f"Действие {action} не найдено в сетке {grid_name}."],
        )


def _format_action_config_info(
    config: GridActionConfig | None,
) -> GridActionConfigInfo | None:
    if config is None:
        return None
    payload: dict[str, Any] | None
    if config.payload_json:
        payload = json.loads(config.payload_json)
    else:
        payload = None
    return GridActionConfigInfo(
        type=config.type,
        payload=payload,
        min_delay_s=config.min_delay_s,
        max_delay_s=config.max_delay_s,
        random_jitter_enabled=config.random_jitter_enabled,
        account_selector=config.account_selector,
        account_allocation=config.account_allocation,
        account_allocation_value=config.account_allocation_value,
    )


def _normalize_list_field(value: object, field_name: str) -> list[str]:
    if isinstance(value, list):
        cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if len(cleaned) != len(value):
            raise ValidationError(
                f"Некорректный параметр {field_name}.",
                [f"{field_name} должен быть списком строк."],
            )
        return cleaned
    if isinstance(value, str):
        split_values = [
            item.strip() for item in value.replace("|", ",").split(",") if item.strip()
        ]
        if not split_values:
            raise ValidationError(
                f"Некорректный параметр {field_name}.",
                [f"{field_name} должен содержать хотя бы одно значение."],
            )
        return split_values
    raise ValidationError(
        f"Некорректный параметр {field_name}.",
        [f"{field_name} должен быть строкой или списком строк."],
    )


def _validate_spam_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if "files" in normalized:
        normalized["files"] = _normalize_list_field(normalized["files"], "files")
    if "random_variants" in normalized:
        normalized["random_variants"] = _normalize_list_field(
            normalized["random_variants"], "random_variants"
        )
    if "text" in normalized:
        text = normalized["text"]
        if not isinstance(text, str) or not text.strip():
            raise ValidationError(
                "Некорректный параметр text.",
                ["text должен быть непустой строкой."],
            )
        normalized["text"] = text.strip()
    if "text_template" in normalized:
        text_template = normalized["text_template"]
        if not isinstance(text_template, str) or not text_template.strip():
            raise ValidationError(
                "Некорректный параметр text_template.",
                ["text_template должен быть непустой строкой."],
            )
        normalized["text_template"] = text_template.strip()
    if "album_url" in normalized:
        album_url = normalized["album_url"]
        if not isinstance(album_url, str) or not album_url.strip():
            raise ValidationError(
                "Некорректный параметр album_url.",
                ["album_url должен быть непустой строкой."],
            )
        normalized["album_url"] = album_url.strip()
    return normalized


def _validate_complaint_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    reason = normalized.get("reason")
    if reason is None:
        raise ValidationError(
            "Некорректный параметр reason.",
            ["reason обязателен для жалобы."],
        )
    if not isinstance(reason, str) or not reason.strip():
        raise ValidationError(
            "Некорректный параметр reason.",
            ["reason должен быть непустой строкой."],
        )
    reason_value = reason.strip().lower()
    if reason_value not in COMPLAINT_REASONS:
        raise ValidationError(
            "Некорректный параметр reason.",
            ["Допустимые причины: " + ", ".join(sorted(COMPLAINT_REASONS))],
        )
    normalized["reason"] = reason_value

    selection = normalized.get("selection")
    if selection is not None:
        if not isinstance(selection, str) or not selection.strip():
            raise ValidationError(
                "Некорректный параметр selection.",
                ["selection должен быть строкой."],
            )
        selection_value = selection.strip().lower()
        if selection_value not in {"latest", "explicit"}:
            raise ValidationError(
                "Некорректный параметр selection.",
                ["Используйте latest или explicit."],
            )
        normalized["selection"] = selection_value
    else:
        selection_value = None

    target = normalized.get("target")
    if target is not None:
        if not isinstance(target, str) or not target.strip():
            raise ValidationError(
                "Некорректный параметр target.",
                ["target должен быть непустой строкой."],
            )
        normalized["target"] = target.strip()

    if selection_value == "explicit" and not normalized.get("target"):
        raise ValidationError(
            "Некорректный параметр target.",
            ["Для selection=explicit укажите target."],
        )

    if "timers" in normalized:
        normalized["timers"] = _normalize_list_field(normalized["timers"], "timers")

    if "delay" in normalized:
        delay = normalized["delay"]
        if isinstance(delay, int):
            if delay < 0:
                raise ValidationError(
                    "Некорректный параметр delay.",
                    ["delay должен быть неотрицательным числом."],
                )
        elif isinstance(delay, str):
            if not delay.strip():
                raise ValidationError(
                    "Некорректный параметр delay.",
                    ["delay должен быть непустой строкой."],
                )
            normalized["delay"] = delay.strip()
        else:
            raise ValidationError(
                "Некорректный параметр delay.",
                ["delay должен быть строкой или числом."],
            )
    return normalized


def _validate_grid_action_config(
    action: str, config: GridActionConfigPayload | None
) -> GridActionConfigInfo | None:
    if config is None:
        return None

    action_type = (config.type or action).strip().lower()
    if action_type not in ALLOWED_GRID_ACTION_TYPES:
        raise ValidationError(
            "Некорректный тип действия.",
            [
                "Допустимые типы: " + ", ".join(sorted(ALLOWED_GRID_ACTION_TYPES)),
            ],
        )

    payload = config.payload or {}
    if not isinstance(payload, dict):
        raise ValidationError(
            "Некорректные параметры действия.",
            ["Payload должен быть объектом."],
        )
    allowed_fields = ACTION_PAYLOAD_FIELDS.get(action_type, set())
    unknown_fields = [key for key in payload.keys() if key not in allowed_fields]
    if unknown_fields:
        raise ValidationError(
            "Некорректные параметры действия.",
            [
                "Неизвестные параметры: " + ", ".join(sorted(unknown_fields)),
            ],
        )
    if action_type in SPAM_ACTION_TYPES:
        payload = _validate_spam_payload(payload)
    if action_type == "complaint":
        payload = _validate_complaint_payload(payload)
    if "count" in payload:
        count = payload["count"]
        if not isinstance(count, int) or count <= 0:
            raise ValidationError(
                "Некорректный параметр count.",
                ["count должен быть положительным числом."],
            )
    if "text" in payload:
        text = payload["text"]
        if not isinstance(text, str) or not text.strip():
            raise ValidationError(
                "Некорректный параметр text.",
                ["text должен быть непустой строкой."],
            )

    min_delay_s = config.min_delay_s
    max_delay_s = config.max_delay_s
    if (min_delay_s is None) != (max_delay_s is None):
        raise ValidationError(
            "Некорректные интервалы.",
            ["Укажите оба значения: min и max."],
        )
    if min_delay_s is not None and max_delay_s is not None:
        if min_delay_s < 0 or max_delay_s < 0:
            raise ValidationError(
                "Некорректные интервалы.",
                ["Интервалы должны быть неотрицательными."],
            )
        if min_delay_s > max_delay_s:
            raise ValidationError(
                "Некорректные интервалы.",
                ["min не может быть больше max."],
            )

    random_jitter_enabled = bool(config.random_jitter_enabled)
    if random_jitter_enabled and (min_delay_s is None or max_delay_s is None):
        raise ValidationError(
            "Некорректный jitter.",
            ["Для jitter укажите min и max."],
        )

    account_selector = config.account_selector
    if account_selector:
        selector = account_selector.strip()
        if selector.lower() != "all":
            names = parse_name_list(selector)
            if not names:
                raise ValidationError(
                    "Некорректный выбор аккаунтов.",
                    ["Укажите список аккаунтов или all."],
                )
            invalid_names = validate_names(names)
            if invalid_names:
                raise ValidationError(
                    "Некорректные имена аккаунтов.",
                    [
                        "Некорректные имена аккаунтов: " + ", ".join(invalid_names),
                        "Используйте латиницу, цифры и символы _ . -",
                    ],
                )
            account_selector = ",".join(names)
        else:
            account_selector = "all"

    account_allocation = config.account_allocation
    account_allocation_value = config.account_allocation_value
    if account_allocation_value is not None and not account_allocation:
        raise ValidationError(
            "Некорректное распределение аккаунтов.",
            ["Укажите тип распределения."],
        )
    if account_allocation:
        allocation_type = account_allocation.strip().lower()
        allowed_allocation_types = {"count", "percent", "explicit_list"}
        if allocation_type not in allowed_allocation_types:
            raise ValidationError(
                "Некорректное распределение аккаунтов.",
                ["Допустимые типы: " + ", ".join(sorted(allowed_allocation_types))],
            )
        if account_allocation_value is None:
            raise ValidationError(
                "Некорректное распределение аккаунтов.",
                ["Укажите значение для распределения аккаунтов."],
            )
        if allocation_type in {"count", "percent"}:
            if isinstance(account_allocation_value, str):
                raw_value = account_allocation_value.strip()
                if not raw_value.isdigit():
                    raise ValidationError(
                        "Некорректное распределение аккаунтов.",
                        ["Значение должно быть числом."],
                    )
                value_int = int(raw_value)
            elif isinstance(account_allocation_value, int):
                value_int = account_allocation_value
            else:
                raise ValidationError(
                    "Некорректное распределение аккаунтов.",
                    ["Значение должно быть числом."],
                )
            if value_int <= 0:
                raise ValidationError(
                    "Некорректное распределение аккаунтов.",
                    ["Значение должно быть положительным числом."],
                )
            if allocation_type == "percent" and value_int > 100:
                raise ValidationError(
                    "Некорректное распределение аккаунтов.",
                    ["Процент не может быть больше 100."],
                )
            account_allocation_value = str(value_int)
        else:
            if isinstance(account_allocation_value, list):
                raw_names = account_allocation_value
            else:
                raw_names = parse_name_list(str(account_allocation_value))
            if not raw_names:
                raise ValidationError(
                    "Некорректное распределение аккаунтов.",
                    ["Укажите список аккаунтов."],
                )
            invalid_names = validate_names(raw_names)
            if invalid_names:
                raise ValidationError(
                    "Некорректные имена аккаунтов.",
                    [
                        "Некорректные имена аккаунтов: " + ", ".join(invalid_names),
                        "Используйте латиницу, цифры и символы _ . -",
                    ],
                )
            account_allocation_value = ",".join(raw_names)
        account_allocation = allocation_type

    payload_value = payload or None
    return GridActionConfigInfo(
        type=action_type,
        payload=payload_value,
        min_delay_s=min_delay_s,
        max_delay_s=max_delay_s,
        random_jitter_enabled=random_jitter_enabled,
        account_selector=account_selector,
        account_allocation=account_allocation,
        account_allocation_value=account_allocation_value,
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


def _apply_account_selector(accounts: list[str], selector: str | None) -> list[str]:
    if not selector or selector.lower() == "all":
        return accounts
    selected_names = set(parse_name_list(selector))
    return [name for name in accounts if name in selected_names]


def _apply_account_allocation(
    accounts: list[str],
    allocation_type: str,
    allocation_value: str,
) -> list[str]:
    if allocation_type == "count":
        count = int(allocation_value)
        return accounts[:count]
    if allocation_type == "percent":
        percent = int(allocation_value)
        if not accounts:
            return []
        count = max(1, int(len(accounts) * percent / 100))
        return accounts[:count]
    explicit_names = parse_name_list(allocation_value)
    available = set(accounts)
    return [name for name in explicit_names if name in available]


def _allocate_accounts_for_action(
    accounts: list[str],
    available_accounts: list[str],
    config: GridActionConfig | None,
) -> tuple[list[str], list[str]]:
    if config and config.account_allocation:
        base_accounts = available_accounts
    else:
        base_accounts = accounts
    selected = _apply_account_selector(base_accounts, config.account_selector if config else None)
    if config and config.account_allocation and config.account_allocation_value:
        assigned = _apply_account_allocation(
            selected,
            config.account_allocation,
            config.account_allocation_value,
        )
        assigned_set = set(assigned)
        remaining = [name for name in available_accounts if name not in assigned_set]
        return assigned, remaining
    return selected, available_accounts


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


def _resolve_grid_removal_selection(
    store: Storage, chat_id: int, grid_name: str, raw_accounts: str
) -> list[str]:
    raw_accounts = raw_accounts.strip()
    if raw_accounts.lower() == "all":
        grid_accounts: list[str] = []
        for name, accounts in store.list_grids(chat_id):
            if name == grid_name:
                grid_accounts = accounts
                break
        if not grid_accounts:
            raise ValidationError(
                "В сетке нет аккаунтов.",
                ["Добавьте аккаунты командой /grids add-account."],
            )
        return grid_accounts

    return _resolve_account_selection(store, chat_id, raw_accounts)


def remove_accounts_from_grid(
    store: Storage, chat_id: int, grid_name: str, raw_accounts: str
) -> GridAccountsRemoveResponse:
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

    accounts = _resolve_grid_removal_selection(store, chat_id, grid_name, raw_accounts)
    removed, skipped = store.remove_accounts_from_grid(chat_id, grid_name, accounts)
    return GridAccountsRemoveResponse(removed=removed, skipped=skipped)


def _resolve_grid_action_delay_seconds(config: GridActionConfig) -> int:
    min_delay_s = config.min_delay_s
    max_delay_s = config.max_delay_s
    if min_delay_s is None or max_delay_s is None:
        return 0
    if config.random_jitter_enabled:
        return random.randint(min_delay_s, max_delay_s)
    return min_delay_s


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
    actions_with_configs = store.list_grid_actions_with_configs(chat_id, grid_name)
    if not actions_with_configs:
        raise ValidationError(
            "Для сетки не настроены действия.",
            ["Добавьте действия для сетки перед запуском."],
        )

    redis_conn = Redis.from_url(settings.redis_url)
    grid_queue = Queue(settings.rq_grid_actions_queue, connection=redis_conn)
    action_names: list[str] = []
    queued_jobs = 0
    available_accounts = accounts.copy()
    for action, config in actions_with_configs:
        action_names.append(action.action)
        assigned_accounts, available_accounts = _allocate_accounts_for_action(
            accounts,
            available_accounts,
            config,
        )
        if not assigned_accounts:
            continue
        config_payload: dict[str, Any] | None = None
        if config and config.payload_json:
            try:
                config_payload = json.loads(config.payload_json)
            except json.JSONDecodeError:
                config_payload = None
        payload = json.dumps(
            {
                "grid_name": grid_name,
                "chat_id": chat_id,
                "accounts": assigned_accounts,
                "action": action.action,
                "config": {
                    "type": config.type if config else None,
                    "payload": config_payload,
                }
                if config
                else None,
            }
        )
        delay_seconds = _resolve_grid_action_delay_seconds(config)
        if delay_seconds > 0:
            grid_queue.enqueue_in(
                timedelta(seconds=delay_seconds),
                "worker.tasks.grid_actions.apply_grid_action",
                payload,
            )
        else:
            grid_queue.enqueue(
                "worker.tasks.grid_actions.apply_grid_action",
                payload,
            )
        queued_jobs += 1

    return GridRunResponse(
        accounts=accounts,
        actions=action_names,
        queued_jobs=queued_jobs,
    )


def schedule_grid_run(
    store: Storage,
    settings: Settings,
    chat_id: int,
    grid_name: str,
    raw_accounts: str,
) -> GridRunResponse:
    return run_grid(store, settings, chat_id, grid_name, raw_accounts)
