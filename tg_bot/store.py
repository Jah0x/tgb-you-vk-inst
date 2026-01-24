from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Grid:
    name: str
    account_names: list[str] = field(default_factory=list)


class BotStore:
    def __init__(self) -> None:
        self._accounts: dict[int, list[str]] = {}
        self._grids: dict[int, dict[str, Grid]] = {}

    def list_accounts(self, chat_id: int) -> list[str]:
        return list(self._accounts.get(chat_id, []))

    def add_accounts(self, chat_id: int, names: list[str]) -> tuple[list[str], list[str]]:
        existing = self._accounts.setdefault(chat_id, [])
        added: list[str] = []
        skipped: list[str] = []
        for name in names:
            if name in existing:
                skipped.append(name)
                continue
            existing.append(name)
            added.append(name)
        return added, skipped

    def create_grid(self, chat_id: int, name: str) -> bool:
        grids = self._grids.setdefault(chat_id, {})
        if name in grids:
            return False
        grids[name] = Grid(name=name)
        return True

    def list_grids(self, chat_id: int) -> list[Grid]:
        grids = self._grids.get(chat_id, {})
        return list(grids.values())

    def get_grid(self, chat_id: int, name: str) -> Grid | None:
        grids = self._grids.get(chat_id, {})
        return grids.get(name)

    def add_accounts_to_grid(
        self, chat_id: int, grid_name: str, account_names: list[str]
    ) -> tuple[list[str], list[str]]:
        grid = self.get_grid(chat_id, grid_name)
        if not grid:
            return [], account_names
        added: list[str] = []
        skipped: list[str] = []
        for name in account_names:
            if name in grid.account_names:
                skipped.append(name)
                continue
            grid.account_names.append(name)
            added.append(name)
        return added, skipped

    def resolve_accounts(self, chat_id: int, names: list[str]) -> tuple[list[str], list[str]]:
        existing = set(self._accounts.get(chat_id, []))
        found = [name for name in names if name in existing]
        missing = [name for name in names if name not in existing]
        return found, missing
