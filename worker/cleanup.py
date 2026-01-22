from __future__ import annotations

import time
from pathlib import Path


def cleanup_cache(cache_dir: Path, ttl_seconds: int) -> None:
    if not cache_dir.exists():
        return
    now = time.time()
    for item in cache_dir.glob("*"):
        if not item.is_file():
            continue
        age = now - item.stat().st_mtime
        if age > ttl_seconds:
            item.unlink(missing_ok=True)
