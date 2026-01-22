from __future__ import annotations

import re

from shared.jobs.models import Job
from shared.providers.base import Provider
from shared.router.registry import register


_INSTAGRAM_REGEX = re.compile(
    r"(https?://)?(www\.)?instagram\.com/(reel|reels)/[\w-]+",
    re.IGNORECASE,
)


@register
class InstagramProvider:
    name = "instagram"
    priority = 90

    def match(self, text: str) -> bool:
        return bool(_INSTAGRAM_REGEX.search(text))

    def extract_url(self, text: str) -> str | None:
        match = _INSTAGRAM_REGEX.search(text)
        if not match:
            return None
        url = match.group(0)
        if not url.startswith("http"):
            return f"https://{url}"
        return url

    def normalize(self, url: str) -> str:
        return url.rstrip("/")

    def build_job(
        self,
        url: str,
        chat_id: int,
        reply_to_message_id: int | None,
        options: dict | None,
    ) -> Job:
        return Job(
            provider=self.name,
            url=url,
            chat_id=chat_id,
            reply_to_message_id=reply_to_message_id,
            options=options,
        )
