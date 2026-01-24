from __future__ import annotations

from enum import Enum

from aiogram.types import Message

from shared.config import Settings


class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"


def resolve_role(chat_id: int, settings: Settings) -> Role | None:
    if not settings.admin_chat_ids and not settings.operator_chat_ids:
        return Role.ADMIN
    if chat_id in settings.admin_chat_ids:
        return Role.ADMIN
    if chat_id in settings.operator_chat_ids:
        return Role.OPERATOR
    return None


async def ensure_role(
    message: Message,
    settings: Settings,
    allowed_roles: set[Role],
    action_description: str,
) -> bool:
    role = resolve_role(message.chat.id, settings)
    if role in allowed_roles:
        return True
    await message.answer(
        "Недостаточно прав для действия: "
        f"{action_description}.\n"
        "Обратитесь к администратору или проверьте настройки ролей "
        "(ADMIN_CHAT_IDS, OPERATOR_CHAT_IDS)."
    )
    return False
