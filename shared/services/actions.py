from __future__ import annotations

from dataclasses import dataclass

from shared.models import PostEvent
from shared.storage import Storage


@dataclass(frozen=True)
class PostEventList:
    events: list[PostEvent]


def add_post_event(store: Storage, channel_id: int, post_key: str) -> bool:
    return store.add_post_event(channel_id, post_key)


def list_pending_post_events(
    store: Storage, channel_id: int | None = None, limit: int = 100
) -> PostEventList:
    events = store.list_pending_post_events(channel_id=channel_id, limit=limit)
    return PostEventList(events=events)


def mark_post_event_processed(store: Storage, event_id: int) -> None:
    store.mark_post_event_processed(event_id)
