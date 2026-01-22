from __future__ import annotations

from shared.providers.base import Provider
from shared.router.registry import get_providers


def detect(text: str) -> tuple[Provider, str] | None:
    for provider in get_providers():
        if not provider.match(text):
            continue
        extracted = provider.extract_url(text)
        if not extracted:
            continue
        normalized = provider.normalize(extracted)
        return provider, normalized
    return None
