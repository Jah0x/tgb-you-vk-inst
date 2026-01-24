from __future__ import annotations

import shlex

from aiogram import Dispatcher, F
from aiogram.types import Message

from shared.config import Settings
from shared.services import create_complaint_action_for_target
from shared.services.errors import ServiceError
from shared.services.grids import COMPLAINT_REASONS
from shared.storage import Storage
from tg_bot.handlers.permissions import Role, ensure_role

COMPLAINTS_HELP = (
    "Команды для жалоб:\n"
    "• /complaints target latest --reason=<reason> [--delay=5m] [--timer=5m]\n"
    "• /complaints target <url|id> --reason=<reason> [--timers=5m,10m]\n"
    "\n"
    "Допустимые причины: " + ", ".join(sorted(COMPLAINT_REASONS)) + "\n"
    "Примеры: /complaints target latest --reason=spam --delay=10m\n"
    "         /complaints target <url> --reason=fraud --timers=5m,15m"
)


def _parse_complaints_options(tokens: list[str]) -> tuple[str | None, list[str], str | int | None]:
    reason: str | None = None
    timers: list[str] = []
    delay: str | int | None = None

    for token in tokens:
        if token.startswith("--reason="):
            reason = token.split("=", 1)[1].strip()
        elif token.startswith("--delay="):
            value = token.split("=", 1)[1].strip()
            delay = int(value) if value.isdigit() else value
        elif token.startswith("--timer="):
            value = token.split("=", 1)[1].strip()
            if value:
                timers.append(value)
        elif token.startswith("--timers="):
            values = token.split("=", 1)[1]
            timers.extend([item.strip() for item in values.split(",") if item.strip()])
    return reason, timers, delay


async def _service_error_response(message: Message, exc: ServiceError) -> None:
    response = exc.message
    if exc.details:
        response = "\n".join([exc.message, *exc.details])
    await message.answer(response)


def register_complaints(dp: Dispatcher, store: Storage, settings: Settings) -> None:
    @dp.message(F.text.startswith("/complaints"))
    async def _complaints_handler(message: Message) -> None:
        if not message.text:
            return

        parts = shlex.split(message.text.strip())
        if len(parts) == 1:
            await message.answer(COMPLAINTS_HELP)
            return

        action = parts[1].lower()
        if action != "target":
            await message.answer("Формат: /complaints target latest|<url|id> --reason=<reason>")
            return

        if not await ensure_role(
            message,
            settings,
            {Role.ADMIN, Role.OPERATOR},
            "запуск жалоб",
        ):
            return

        if len(parts) < 3:
            await message.answer("Формат: /complaints target latest|<url|id> --reason=<reason>")
            return

        target = parts[2].strip()
        selection = "latest" if target.lower() == "latest" else "explicit"
        reason, timers, delay = _parse_complaints_options(parts[3:])
        if not reason:
            await message.answer(
                "Укажите причину жалобы: --reason=<reason>\n" + COMPLAINTS_HELP
            )
            return

        channel_name = message.chat.title or str(message.chat.id)

        try:
            result = create_complaint_action_for_target(
                store,
                settings,
                chat_id=message.chat.id,
                channel_name=channel_name,
                selection=selection,
                target=None if selection == "latest" else target,
                reason=reason,
                timers=timers or None,
                delay=delay,
            )
        except ServiceError as exc:
            await _service_error_response(message, exc)
            return

        await message.answer(
            "Жалоба поставлена в очередь для "
            f"{'последнего поста' if result.selection == 'latest' else 'поста'}. "
            f"Причина: {result.reason}. "
            f"Задач в очереди: {result.queued_jobs}."
        )
