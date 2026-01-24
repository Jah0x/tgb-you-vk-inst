from __future__ import annotations

import json
import logging
from datetime import timedelta

from redis import Redis
from rq import Queue

from shared.config import load_settings
from shared.storage.db import Storage
from worker.scheduling import parse_duration_seconds

DEFAULT_ESCALATION = [
    {"level": 1, "rule": "0s"},
    {"level": 2, "rule": "5m"},
    {"level": 3, "rule": "15m"},
]


def process_channel_events(payload: str) -> None:
    logging.basicConfig(level=logging.INFO)
    data = json.loads(payload)
    channel_id = data["channel_id"]
    settings = load_settings()
    store = Storage(settings.db_url)
    redis_conn = Redis.from_url(settings.redis_url)
    events_queue = Queue(settings.rq_post_events_queue, connection=redis_conn)

    pending = store.list_pending_post_events(channel_id=channel_id)
    if not pending:
        logging.info("No pending post events for channel_id=%s", channel_id)
        return

    for event in pending:
        events_queue.enqueue(
            "worker.tasks.post_events.handle_post_event",
            json.dumps({"channel_id": event.channel_id, "post_key": event.post_key}),
            job_id=f"post-event-{event.id}",
        )
        store.mark_post_event_processed(event.id)


def handle_post_event(payload: str) -> None:
    logging.basicConfig(level=logging.INFO)
    data = json.loads(payload)
    channel_id = data["channel_id"]
    post_key = data["post_key"]
    settings = load_settings()
    store = Storage(settings.db_url)
    escalation_rules = store.list_escalation_rules(channel_id)
    if escalation_rules:
        steps = [{"level": rule.level, "rule": rule.rule} for rule in escalation_rules]
    else:
        steps = DEFAULT_ESCALATION

    redis_conn = Redis.from_url(settings.redis_url)
    grid_queue = Queue(settings.rq_grid_actions_queue, connection=redis_conn)

    for step in steps:
        delay_seconds = parse_duration_seconds(step["rule"], default=0)
        action = _action_for_level(step["level"])
        payload = json.dumps(
            {
                "channel_id": channel_id,
                "post_key": post_key,
                "action": action,
                "metadata": {"level": step["level"]},
            }
        )
        if delay_seconds > 0:
            grid_queue.enqueue_in(
                timedelta(seconds=delay_seconds),
                "worker.tasks.grid_actions.apply_grid_action",
                payload,
            )
        else:
            grid_queue.enqueue(
                "worker.tasks.grid_actions.apply_grid_action",
                payload,
            )


def _action_for_level(level: int) -> str:
    if level == 1:
        return "reaction:1"
    if level == 2:
        return "reaction:2"
    return "comment"
