from __future__ import annotations

import re

from shared.jobs.models import Job
from shared.providers.base import Provider
from shared.router.registry import register


_VK_REGEX = re.compile(
    r"(https?://)?(www\.)?(m\.)?vk\.(com|ru)/[^\s]+",
    re.IGNORECASE,
)


@register
class VkProvider:
    name = "vk"
    priority = 80

    def match(self, text: str) -> bool:
        return bool(_VK_REGEX.search(text))

    def extract_url(self, text: str) -> str | None:
        match = _VK_REGEX.search(text)
        if not match:
            return None
        url = match.group(0).rstrip(")")
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
