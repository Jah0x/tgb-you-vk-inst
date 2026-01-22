from __future__ import annotations

import logging
from pathlib import Path

from shared.config import load_settings
from shared.jobs.serializer import from_json
from worker.handlers import instagram, youtube
from worker.telegram import send_result


HANDLERS = {
    "youtube": youtube.handle,
    "instagram": instagram.handle,
}


def process_job(payload: str) -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    job = from_json(payload)
    handler = HANDLERS.get(job.provider)
    if not handler:
        raise RuntimeError(f"Unsupported provider: {job.provider}")

    result_path = handler(job, settings)
    send_result(
        settings=settings,
        chat_id=job.chat_id,
        file_path=Path(result_path),
        reply_to_message_id=job.reply_to_message_id,
    )
