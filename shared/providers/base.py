from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from shared.jobs.models import Job


class Provider(Protocol):
    name: str
    priority: int

    def match(self, text: str) -> bool:
        ...

    def extract_url(self, text: str) -> str | None:
        ...

    def normalize(self, url: str) -> str:
        ...

    def build_job(
        self,
        url: str,
        chat_id: int,
        reply_to_message_id: int | None,
        options: dict | None,
    ) -> Job:
        ...


@dataclass(frozen=True)
class ProviderMetadata:
    name: str
    priority: int
