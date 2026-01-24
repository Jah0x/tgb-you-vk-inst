from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    bot_token: str
    redis_url: str
    rq_queue: str
    rq_grid_actions_queue: str
    rq_post_events_queue: str
    db_url: str
    data_dir: str
    max_duration_sec: int
    max_filesize_mb: int
    instagram_cookies_path: str | None
    vk_cookies_path: str | None
    scheduler_poll_seconds: int
    admin_chat_ids: frozenset[int]
    operator_chat_ids: frozenset[int]


def _parse_chat_ids(raw: str | None) -> frozenset[int]:
    if not raw:
        return frozenset()
    ids = []
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item:
            continue
        if not item.lstrip("-").isdigit():
            continue
        ids.append(int(item))
    return frozenset(ids)


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    rq_queue = os.getenv("RQ_QUEUE", "downloads")
    rq_grid_actions_queue = os.getenv("RQ_GRID_ACTIONS_QUEUE", "grid_actions")
    rq_post_events_queue = os.getenv("RQ_POST_EVENTS_QUEUE", "post_events")
    db_url = os.getenv("DB_URL", "sqlite:////data/app.db")
    data_dir = os.getenv("DATA_DIR", "/data")
    max_duration_sec = int(os.getenv("MAX_DURATION_SEC", "180"))
    max_filesize_mb = int(os.getenv("MAX_FILESIZE_MB", "45"))
    instagram_cookies_path = os.getenv("INSTAGRAM_COOKIES_PATH") or None
    vk_cookies_path = os.getenv("VK_COOKIES_PATH") or None
    scheduler_poll_seconds = int(os.getenv("SCHEDULER_POLL_SECONDS", "30"))
    admin_chat_ids = _parse_chat_ids(os.getenv("ADMIN_CHAT_IDS"))
    operator_chat_ids = _parse_chat_ids(os.getenv("OPERATOR_CHAT_IDS"))
    return Settings(
        bot_token=bot_token,
        redis_url=redis_url,
        rq_queue=rq_queue,
        rq_grid_actions_queue=rq_grid_actions_queue,
        rq_post_events_queue=rq_post_events_queue,
        db_url=db_url,
        data_dir=data_dir,
        max_duration_sec=max_duration_sec,
        max_filesize_mb=max_filesize_mb,
        instagram_cookies_path=instagram_cookies_path,
        vk_cookies_path=vk_cookies_path,
        scheduler_poll_seconds=scheduler_poll_seconds,
        admin_chat_ids=admin_chat_ids,
        operator_chat_ids=operator_chat_ids,
    )
