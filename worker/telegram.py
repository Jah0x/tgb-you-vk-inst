from __future__ import annotations

import asyncio
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

from shared.config import Settings


async def _send_video(
    bot: Bot,
    chat_id: int,
    file_path: Path,
    reply_to_message_id: int | None,
) -> None:
    await bot.send_video(
        chat_id=chat_id,
        video=FSInputFile(file_path),
        reply_to_message_id=reply_to_message_id,
    )


async def _send_document(
    bot: Bot,
    chat_id: int,
    file_path: Path,
    reply_to_message_id: int | None,
) -> None:
    await bot.send_document(
        chat_id=chat_id,
        document=FSInputFile(file_path),
        reply_to_message_id=reply_to_message_id,
    )


def send_result(
    settings: Settings,
    chat_id: int,
    file_path: Path,
    reply_to_message_id: int | None,
) -> None:
    async def _runner() -> None:
        bot = Bot(token=settings.bot_token)
        try:
            await _send_video(bot, chat_id, file_path, reply_to_message_id)
        except Exception:
            await _send_document(bot, chat_id, file_path, reply_to_message_id)
        finally:
            await bot.session.close()

    asyncio.run(_runner())
