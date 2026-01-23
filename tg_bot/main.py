from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from redis import Redis
from rq import Queue

from shared.config import load_settings
from shared.jobs.serializer import to_json
from shared.providers import instagram as _instagram_provider  # noqa: F401
from shared.providers import vk as _vk_provider  # noqa: F401
from shared.providers import youtube as _youtube_provider  # noqa: F401
from shared.router.detector import detect


async def handle_message(message: Message, queue: Queue) -> None:
    if not message.text:
        await message.answer(
            "Пришли ссылку (YouTube, Instagram Reels и VK сейчас поддерживаются)."
        )
        return

    detected = detect(message.text)
    if not detected:
        await message.answer(
            "Пришли ссылку (YouTube, Instagram Reels и VK сейчас поддерживаются)."
        )
        return

    provider, url = detected
    job = provider.build_job(
        url=url,
        chat_id=message.chat.id,
        reply_to_message_id=message.message_id,
        options=None,
    )
    queue.enqueue("worker.tasks.process_job", to_json(job), job_id=job.id)
    await message.answer("Принял, качаю…")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required")

    redis_conn = Redis.from_url(settings.redis_url)
    queue = Queue(settings.rq_queue, connection=redis_conn)
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    @dp.message(F.text)
    async def _message_handler(message: Message) -> None:
        await handle_message(message, queue)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
