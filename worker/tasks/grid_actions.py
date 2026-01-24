from __future__ import annotations

import json
import logging


def apply_grid_action(payload: str) -> None:
    logging.basicConfig(level=logging.INFO)
    data = json.loads(payload)
    if "grid_name" in data:
        grid_name = data["grid_name"]
        chat_id = data["chat_id"]
        accounts = data.get("accounts") or []
        action = data["action"]
        logging.info(
            "Grid action: grid_name=%s chat_id=%s accounts=%s action=%s",
            grid_name,
            chat_id,
            accounts,
            action,
        )
        return

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
