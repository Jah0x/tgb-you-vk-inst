from __future__ import annotations

from dataclasses import dataclass

from shared.services.errors import NotFoundError, ValidationError
from shared.services.utils import parse_name_list, validate_names
from shared.storage import Storage


@dataclass(frozen=True)
class AccountListResponse:
    accounts: list[str]


@dataclass(frozen=True)
class AccountAddResponse:
    added: list[str]
    skipped: list[str]


def list_accounts(store: Storage, chat_id: int) -> AccountListResponse:
    accounts = store.list_accounts(chat_id)
    return AccountListResponse(accounts=accounts)


def add_accounts(
    store: Storage, chat_id: int, raw_names: str | list[str]
) -> AccountAddResponse:
    if isinstance(raw_names, str):
        names = parse_name_list(raw_names)
    else:
        names = [name.strip() for name in raw_names if name.strip()]

    if not names:
        raise ValidationError(
            "Не удалось распознать аккаунты.",
            ["Пример: /accounts add name1,name2"],
        )

    invalid = validate_names(names)
    if invalid:
        raise ValidationError(
            "Некорректные имена аккаунтов.",
            [
                "Некорректные имена: " + ", ".join(invalid),
                "Используйте латиницу, цифры и символы _ . -",
            ],
        )

    added, skipped = store.add_accounts(chat_id, names)
    return AccountAddResponse(added=added, skipped=skipped)


def delete_account(store: Storage, chat_id: int, name: str) -> None:
    invalid = validate_names([name])
    if invalid:
        raise ValidationError(
            "Некорректное имя аккаунта.",
            ["Используйте латиницу, цифры и символы _ . -"],
        )
    if not store.delete_account(chat_id, name):
        raise NotFoundError(
            "Аккаунт не найден.",
            [f"Аккаунт {name} не найден в списке."],
        )
