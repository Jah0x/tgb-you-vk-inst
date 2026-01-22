from __future__ import annotations

from shared.jobs.models import Job
from shared.providers.base import Provider


class VkProvider:
    name = "vk"
    priority = 50

    def match(self, text: str) -> bool:
        return "vk.com" in text

    def extract_url(self, text: str) -> str | None:
        return None

    def normalize(self, url: str) -> str:
        return url

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
