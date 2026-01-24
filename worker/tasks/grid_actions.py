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
        config = data.get("config") or {}
        if action in {"spam_post", "spam_comment", "spam_message"}:
            payload_data = config.get("payload") or {}
            logging.info(
                "Grid spam action: grid_name=%s chat_id=%s accounts=%s action=%s payload=%s",
                grid_name,
                chat_id,
                accounts,
                action,
                payload_data,
            )
        elif action == "complaint":
            payload_data = config.get("payload") or {}
            logging.info(
                "Grid complaint action: grid_name=%s chat_id=%s accounts=%s payload=%s",
                grid_name,
                chat_id,
                accounts,
                payload_data,
            )
        else:
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
    if action == "complaint":
        logging.info(
            "Grid complaint action: channel_id=%s post_key=%s metadata=%s",
            channel_id,
            post_key,
            metadata,
        )
    else:
        logging.info(
            "Grid action: channel_id=%s post_key=%s action=%s metadata=%s",
            channel_id,
            post_key,
            action,
            metadata,
        )
