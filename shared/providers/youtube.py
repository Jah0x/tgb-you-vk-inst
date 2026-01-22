from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from shared.jobs.models import Job
from shared.providers.base import Provider
from shared.router.registry import register


_YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)[\w-]+|youtu\.be/[\w-]+)",
    re.IGNORECASE,
)


@register
class YouTubeProvider:
    name = "youtube"
    priority = 100

    def match(self, text: str) -> bool:
        return bool(_YOUTUBE_REGEX.search(text))

    def extract_url(self, text: str) -> str | None:
        match = _YOUTUBE_REGEX.search(text)
        if not match:
            return None
        url = match.group(0)
        if not url.startswith("http"):
            return f"https://{url}"
        return url

    def normalize(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.netloc.endswith("youtu.be"):
            video_id = parsed.path.strip("/")
            return f"https://www.youtube.com/watch?v={video_id}"
        if "/shorts/" in parsed.path:
            video_id = parsed.path.split("/shorts/")[-1].strip("/")
            return f"https://www.youtube.com/watch?v={video_id}"
        if parsed.path.endswith("/watch"):
            query = parse_qs(parsed.query)
            video_id = query.get("v", [""])[0]
            return f"https://www.youtube.com/watch?v={video_id}"
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
