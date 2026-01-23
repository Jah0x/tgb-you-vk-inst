from __future__ import annotations

import shutil
from pathlib import Path

from shared.config import Settings
from shared.jobs.models import Job
from worker.cache import cache_path
from worker.downloaders.yt_dlp import download_video, faststart


def handle(job: Job, settings: Settings) -> Path:
    data_dir = Path(settings.data_dir)
    tmp_dir = data_dir / "tmp" / job.id
    cache_dir = data_dir / "cache"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    cached = cache_path(cache_dir, job.url, "mp4")
    if cached.exists():
        return cached

    formats = [
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "best[height<=720][ext=mp4]/best[height<=720]",
        "best[height<=480][ext=mp4]/best[height<=480]",
    ]
    cookies_path = (
        Path(settings.vk_cookies_path) if settings.vk_cookies_path else None
    )
    downloaded = download_video(
        job.url,
        tmp_dir,
        formats,
        settings.max_duration_sec,
        settings.max_filesize_mb,
        cookies_path,
    )

    faststart(downloaded, cached)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return cached
