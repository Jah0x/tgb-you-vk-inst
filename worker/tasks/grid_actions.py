from __future__ import annotations

import json
import logging


def apply_grid_action(payload: str) -> None:
    logging.basicConfig(level=logging.INFO)
    data = json.loads(payload)
    channel_id = data["channel_id"]
    post_key = data["post_key"]
    action = data["action"]
    metadata = data.get("metadata") or {}
    logging.info(
        "Grid action: channel_id=%s post_key=%s action=%s metadata=%s",
        channel_id,
        post_key,
        action,
        metadata,
    )
