from __future__ import annotations

import shlex

from aiogram import Dispatcher, F
from aiogram.types import Message

from shared.config import Settings
from shared.services import create_post_event_for_target
from shared.services.errors import ServiceError
from shared.storage import Storage
from tg_bot.handlers.permissions import Role, ensure_role

COMMENTS_HELP = (
    "Команды для комментариев:\n"
    "• /comments target latest — запуск на последний пост\n"
    "• /comments target <url|id> — запуск на конкретный пост\n"
)


def register_comments(dp: Dispatcher, store: Storage, settings: Settings) -> None:
    @dp.message(F.text.startswith("/comments"))
    async def _comments_handler(message: Message) -> None:
        if not message.text:
            return

        parts = shlex.split(message.text.strip())
        if len(parts) == 1:
            await message.answer(COMMENTS_HELP)
            return

        action = parts[1].lower()
        if action != "target":
            await message.answer("Формат: /comments target latest|<url|id>")
            return

        if not await ensure_role(
            message,
            settings,
            {Role.ADMIN, Role.OPERATOR},
            "запуск событий для комментариев",
        ):
            return

        if len(parts) < 3:
            await message.answer("Формат: /comments target latest|<url|id>")
            return

        target = parts[2].strip()
        selection = "latest" if target.lower() == "latest" else "explicit"
        channel_name = message.chat.title or str(message.chat.id)

        try:
            result = create_post_event_for_target(
                store,
                chat_id=message.chat.id,
                channel_name=channel_name,
                selection=selection,
                target=None if selection == "latest" else target,
            )
        except ServiceError as exc:
            response = exc.message
            if exc.details:
                response = "\n".join([exc.message, *exc.details])
            await message.answer(response)
            return

        if result.created:
            await message.answer(
                "Событие создано для "
                f"{'последнего поста' if result.selection == 'latest' else 'поста'}."
            )
        else:
            await message.answer(
                "Событие уже существует для этого поста. "
                "Если нужно повторить, удалите старую запись или выберите другой пост."
            )
