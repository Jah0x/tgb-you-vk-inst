from __future__ import annotations

import re
from datetime import datetime, timezone

_DURATION_RE = re.compile(r"^(?P<value>\d+)\s*(?P<unit>s|sec|m|min|h|d)?$")


def parse_duration_seconds(rule: str, default: int = 0) -> int:
    text = rule.strip().lower()
    if not text:
        return default
    if text.isdigit():
        return int(text)
    match = _DURATION_RE.match(text)
    if not match:
        return default
    value = int(match.group("value"))
    unit = match.group("unit") or "s"
    if unit in {"s", "sec"}:
        return value
    if unit in {"m", "min"}:
        return value * 60
    if unit == "h":
        return value * 60 * 60
    if unit == "d":
        return value * 60 * 60 * 24
    return default


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
