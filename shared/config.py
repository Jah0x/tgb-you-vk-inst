from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    bot_token: str
    redis_url: str
    rq_queue: str
    data_dir: str
    max_duration_sec: int
    max_filesize_mb: int
    instagram_cookies_path: str | None


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    rq_queue = os.getenv("RQ_QUEUE", "downloads")
    data_dir = os.getenv("DATA_DIR", "/data")
    max_duration_sec = int(os.getenv("MAX_DURATION_SEC", "180"))
    max_filesize_mb = int(os.getenv("MAX_FILESIZE_MB", "45"))
    instagram_cookies_path = os.getenv("INSTAGRAM_COOKIES_PATH") or None
    return Settings(
        bot_token=bot_token,
        redis_url=redis_url,
        rq_queue=rq_queue,
        data_dir=data_dir,
        max_duration_sec=max_duration_sec,
        max_filesize_mb=max_filesize_mb,
        instagram_cookies_path=instagram_cookies_path,
    )
