from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from shared.storage.schema import SCHEMA_STATEMENTS


def _sqlite_path(db_url: str) -> Path:
    parsed = urlparse(db_url)
    if parsed.scheme != "sqlite":
        raise ValueError("Only sqlite DB_URL is supported")
    if parsed.path:
        return Path(parsed.path)
    raise ValueError("DB_URL must include a path, e.g. sqlite:////data/app.db")


def init_db(db_url: str) -> None:
    db_path = _sqlite_path(db_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)
        conn.commit()
    finally:
        conn.close()


class Storage:
    def __init__(self, db_url: str) -> None:
        self._db_path = _sqlite_path(db_url)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def list_accounts(self, chat_id: int) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name FROM accounts WHERE chat_id = ? ORDER BY name",
                (chat_id,),
            ).fetchall()
        return [row["name"] for row in rows]

    def add_accounts(self, chat_id: int, names: list[str]) -> tuple[list[str], list[str]]:
        added: list[str] = []
        skipped: list[str] = []
        with self._connect() as conn:
            for name in names:
                try:
                    conn.execute(
                        "INSERT INTO accounts (chat_id, name) VALUES (?, ?)",
                        (chat_id, name),
                    )
                    added.append(name)
                except sqlite3.IntegrityError:
                    skipped.append(name)
            conn.commit()
        return added, skipped

    def create_grid(self, chat_id: int, name: str) -> bool:
        with self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO grids (chat_id, name) VALUES (?, ?)",
                    (chat_id, name),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def list_grids(self, chat_id: int) -> list[tuple[str, list[str]]]:
        with self._connect() as conn:
            grids = conn.execute(
                "SELECT id, name FROM grids WHERE chat_id = ? ORDER BY name",
                (chat_id,),
            ).fetchall()
            result: list[tuple[str, list[str]]] = []
            for grid in grids:
                accounts = conn.execute(
                    """
                    SELECT a.name
                    FROM accounts a
                    JOIN grid_accounts ga ON ga.account_id = a.id
                    WHERE ga.grid_id = ?
                    ORDER BY a.name
                    """,
                    (grid["id"],),
                ).fetchall()
                result.append((grid["name"], [row["name"] for row in accounts]))
        return result

    def get_grid_id(self, chat_id: int, name: str) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM grids WHERE chat_id = ? AND name = ?",
                (chat_id, name),
            ).fetchone()
        return row["id"] if row else None

    def add_accounts_to_grid(
        self, chat_id: int, grid_name: str, account_names: list[str]
    ) -> tuple[list[str], list[str]]:
        added: list[str] = []
        skipped: list[str] = []
        with self._connect() as conn:
            grid = conn.execute(
                "SELECT id FROM grids WHERE chat_id = ? AND name = ?",
                (chat_id, grid_name),
            ).fetchone()
            if not grid:
                return added, account_names
            grid_id = grid["id"]
            for name in account_names:
                account = conn.execute(
                    "SELECT id FROM accounts WHERE chat_id = ? AND name = ?",
                    (chat_id, name),
                ).fetchone()
                if not account:
                    skipped.append(name)
                    continue
                try:
                    conn.execute(
                        "INSERT INTO grid_accounts (grid_id, account_id) VALUES (?, ?)",
                        (grid_id, account["id"]),
                    )
                    added.append(name)
                except sqlite3.IntegrityError:
                    skipped.append(name)
            conn.commit()
        return added, skipped

    def resolve_accounts(self, chat_id: int, names: list[str]) -> tuple[list[str], list[str]]:
        existing = set(self.list_accounts(chat_id))
        found = [name for name in names if name in existing]
        missing = [name for name in names if name not in existing]
        return found, missing
