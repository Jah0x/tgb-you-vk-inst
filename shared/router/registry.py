from __future__ import annotations

from collections.abc import Iterable

from shared.providers.base import Provider

_PROVIDER_CLASSES: list[type[Provider]] = []


def register(provider_cls: type[Provider]) -> type[Provider]:
    _PROVIDER_CLASSES.append(provider_cls)
    return provider_cls


def get_providers() -> list[Provider]:
    providers = [provider_cls() for provider_cls in _PROVIDER_CLASSES]
    return sorted(providers, key=lambda provider: provider.priority, reverse=True)


def iter_provider_classes() -> Iterable[type[Provider]]:
    return list(_PROVIDER_CLASSES)
