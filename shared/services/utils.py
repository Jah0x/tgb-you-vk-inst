from __future__ import annotations

import re

NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def parse_name_list(raw: str) -> list[str]:
    parts = [part.strip() for part in raw.split(",")]
    return [part for part in parts if part]


def validate_names(names: list[str]) -> list[str]:
    return [name for name in names if not NAME_RE.match(name)]
