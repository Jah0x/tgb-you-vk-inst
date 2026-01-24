from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    id: int
    chat_id: int
    name: str


@dataclass(frozen=True)
class Grid:
    id: int
    chat_id: int
    name: str


@dataclass(frozen=True)
class GridAccount:
    id: int
    grid_id: int
    account_id: int


@dataclass(frozen=True)
class Channel:
    id: int
    chat_id: int
    name: str


@dataclass(frozen=True)
class ScheduleRule:
    id: int
    channel_id: int
    rule: str
    is_active: bool


@dataclass(frozen=True)
class EscalationRule:
    id: int
    channel_id: int
    rule: str
    level: int


@dataclass(frozen=True)
class PostEvent:
    id: int
    channel_id: int
    post_key: str
    status: str
