from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone

from redis import Redis
from rq import Queue

from shared.config import load_settings
from shared.storage.db import Storage
from worker.scheduling import parse_duration_seconds, utc_now_iso


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    store = Storage(settings.db_url)
    events_queue = Queue(settings.rq_post_events_queue, connection=redis_conn)

    while True:
        now = datetime.now(tz=timezone.utc)
        for rule in store.list_active_schedule_rules():
            interval_seconds = parse_duration_seconds(rule.rule, default=0)
            if interval_seconds <= 0:
                logging.warning(
                    "Schedule rule %s has invalid interval '%s'", rule.id, rule.rule
                )
                continue
            last_run = store.get_schedule_state(rule.id)
            if _is_due(now, last_run, interval_seconds):
                events_queue.enqueue(
                    "worker.tasks.post_events.process_channel_events",
                    json.dumps({"channel_id": rule.channel_id, "rule_id": rule.id}),
                    job_id=f"schedule-rule-{rule.id}",
                )
                store.update_schedule_state(rule.id, utc_now_iso())
        time.sleep(settings.scheduler_poll_seconds)


def _is_due(now: datetime, last_run: str | None, interval_seconds: int) -> bool:
    if not last_run:
        return True
    try:
        last_run_dt = datetime.fromisoformat(last_run)
    except ValueError:
        return True
    return now - last_run_dt >= timedelta(seconds=interval_seconds)


if __name__ == "__main__":
    main()
