from __future__ import annotations

import hashlib
from pathlib import Path


def cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def cache_path(cache_dir: Path, url: str, suffix: str = "mp4") -> Path:
    return cache_dir / f"{cache_key(url)}.{suffix}"
