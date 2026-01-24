from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta

from redis import Redis
from rq import Queue

from shared.config import Settings
from shared.models import PostEvent
from shared.services.errors import ValidationError
from shared.services.grids import COMPLAINT_REASONS
from shared.storage import Storage
from worker.scheduling import parse_duration_seconds


@dataclass(frozen=True)
class PostEventList:
    events: list[PostEvent]


@dataclass(frozen=True)
class PostEventCreateResponse:
    created: bool
    channel_id: int
    selection: str
    post_key: str


@dataclass(frozen=True)
class ComplaintActionCreateResponse:
    queued_jobs: int
    channel_id: int
    selection: str
    post_key: str
    reason: str


def add_post_event(store: Storage, channel_id: int, post_key: str) -> bool:
    return store.add_post_event(channel_id, post_key)


def list_pending_post_events(
    store: Storage, channel_id: int | None = None, limit: int = 100
) -> PostEventList:
    events = store.list_pending_post_events(channel_id=channel_id, limit=limit)
    return PostEventList(events=events)


def mark_post_event_processed(store: Storage, event_id: int) -> None:
    store.mark_post_event_processed(event_id)


def create_post_event_for_target(
    store: Storage,
    chat_id: int,
    channel_name: str,
    selection: str,
    target: str | None,
) -> PostEventCreateResponse:
    normalized_selection = selection.strip().lower()
    if normalized_selection not in {"latest", "explicit"}:
        raise ValidationError(
            "Неизвестный режим выбора поста.",
            details=["Используйте latest или explicit."],
        )
    if normalized_selection == "explicit":
        if not target:
            raise ValidationError(
                "Не указан URL или ID поста.",
                details=["Формат: /comments target <url|id>"],
            )
        post_key = target.strip()
    else:
        post_key = "latest"

    channel_id = store.get_or_create_channel(chat_id, channel_name)
    created = store.add_post_event(channel_id, post_key)
    return PostEventCreateResponse(
        created=created,
        channel_id=channel_id,
        selection=normalized_selection,
        post_key=post_key,
    )


def create_complaint_action_for_target(
    store: Storage,
    settings: Settings,
    chat_id: int,
    channel_name: str,
    selection: str,
    target: str | None,
    reason: str,
    timers: list[str] | None = None,
    delay: str | int | None = None,
) -> ComplaintActionCreateResponse:
    normalized_selection = selection.strip().lower()
    if normalized_selection not in {"latest", "explicit"}:
        raise ValidationError(
            "Неизвестный режим выбора поста.",
            details=["Используйте latest или explicit."],
        )
    if normalized_selection == "explicit":
        if not target:
            raise ValidationError(
                "Не указан URL или ID поста.",
                details=["Формат: /complaints target <url|id> --reason=<reason>"],
            )
        post_key = target.strip()
    else:
        post_key = "latest"

    if not reason or not reason.strip():
        raise ValidationError(
            "Некорректный параметр reason.",
            details=["reason должен быть непустой строкой."],
        )
    normalized_reason = reason.strip().lower()
    if normalized_reason not in COMPLAINT_REASONS:
        raise ValidationError(
            "Некорректный параметр reason.",
            details=["Допустимые причины: " + ", ".join(sorted(COMPLAINT_REASONS))],
        )

    channel_id = store.get_or_create_channel(chat_id, channel_name)
    redis_conn = Redis.from_url(settings.redis_url)
    grid_queue = Queue(settings.rq_grid_actions_queue, connection=redis_conn)

    metadata: dict[str, object] = {
        "reason": normalized_reason,
        "selection": normalized_selection,
        "target": None if normalized_selection == "latest" else post_key,
    }
    if timers:
        metadata["timers"] = timers
    if delay is not None:
        metadata["delay"] = delay

    delays: list[int] = []
    if timers:
        for timer in timers:
            delay_value = parse_duration_seconds(timer, default=0)
            delays.append(delay_value)
    elif delay is not None:
        delay_value = (
            delay if isinstance(delay, int) else parse_duration_seconds(str(delay), default=0)
        )
        delays.append(delay_value)
    else:
        delays.append(0)

    queued_jobs = 0
    for delay_seconds in delays:
        payload = json.dumps(
            {
                "channel_id": channel_id,
                "post_key": post_key,
                "action": "complaint",
                "metadata": metadata,
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
        queued_jobs += 1

    return ComplaintActionCreateResponse(
        queued_jobs=queued_jobs,
        channel_id=channel_id,
        selection=normalized_selection,
        post_key=post_key,
        reason=normalized_reason,
    )
