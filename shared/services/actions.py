from __future__ import annotations

from dataclasses import dataclass

from shared.models import PostEvent
from shared.services.errors import ValidationError
from shared.storage import Storage


@dataclass(frozen=True)
class PostEventList:
    events: list[PostEvent]


@dataclass(frozen=True)
class PostEventCreateResponse:
    created: bool
    channel_id: int
    selection: str
    post_key: str


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
