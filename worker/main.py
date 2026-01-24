from __future__ import annotations

import logging
from pathlib import Path

from redis import Redis
from rq import Connection, Queue, Worker

from shared.config import load_settings
from shared.storage import init_db
from worker.cleanup import cleanup_cache


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required")

    redis_conn = Redis.from_url(settings.redis_url)
    cache_dir = Path(settings.data_dir) / "cache"
    cleanup_cache(cache_dir, ttl_seconds=24 * 60 * 60)
    init_db(settings.db_url)

    with Connection(redis_conn):
        queue = Queue(settings.rq_queue)
        worker = Worker([queue])
        worker.work()


if __name__ == "__main__":
    main()
