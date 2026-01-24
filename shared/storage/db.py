from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from shared.models import EscalationRule, GridAction, PostEvent, ScheduleRule
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

    def delete_account(self, chat_id: int, name: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM accounts WHERE chat_id = ? AND name = ?",
                (chat_id, name),
            )
            conn.commit()
        return cursor.rowcount > 0

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

    def delete_grid(self, chat_id: int, name: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM grids WHERE chat_id = ? AND name = ?",
                (chat_id, name),
            )
            conn.commit()
        return cursor.rowcount > 0

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

    def list_grid_actions(self, chat_id: int, grid_name: str) -> list[GridAction]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT ga.id, ga.grid_id, ga.action
                FROM grid_actions ga
                JOIN grids g ON g.id = ga.grid_id
                WHERE g.chat_id = ? AND g.name = ?
                ORDER BY ga.id
                """,
                (chat_id, grid_name),
            ).fetchall()
        return [
            GridAction(id=row["id"], grid_id=row["grid_id"], action=row["action"])
            for row in rows
        ]

    def add_grid_action(self, chat_id: int, grid_name: str, action: str) -> bool:
        with self._connect() as conn:
            grid = conn.execute(
                "SELECT id FROM grids WHERE chat_id = ? AND name = ?",
                (chat_id, grid_name),
            ).fetchone()
            if not grid:
                return False
            grid_id = grid["id"]
            existing = conn.execute(
                "SELECT 1 FROM grid_actions WHERE grid_id = ? AND action = ?",
                (grid_id, action),
            ).fetchone()
            if existing:
                return False
            conn.execute(
                "INSERT INTO grid_actions (grid_id, action) VALUES (?, ?)",
                (grid_id, action),
            )
            conn.commit()
        return True

    def remove_grid_action(self, chat_id: int, grid_name: str, action: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM grid_actions
                WHERE action = ?
                  AND grid_id = (
                      SELECT id FROM grids WHERE chat_id = ? AND name = ?
                  )
                """,
                (action, chat_id, grid_name),
            )
            conn.commit()
        return cursor.rowcount > 0

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

    def remove_accounts_from_grid(
        self, chat_id: int, grid_name: str, account_names: list[str]
    ) -> tuple[list[str], list[str]]:
        removed: list[str] = []
        skipped: list[str] = []
        with self._connect() as conn:
            grid = conn.execute(
                "SELECT id FROM grids WHERE chat_id = ? AND name = ?",
                (chat_id, grid_name),
            ).fetchone()
            if not grid:
                return removed, account_names
            grid_id = grid["id"]
            for name in account_names:
                account = conn.execute(
                    "SELECT id FROM accounts WHERE chat_id = ? AND name = ?",
                    (chat_id, name),
                ).fetchone()
                if not account:
                    skipped.append(name)
                    continue
                cursor = conn.execute(
                    "DELETE FROM grid_accounts WHERE grid_id = ? AND account_id = ?",
                    (grid_id, account["id"]),
                )
                if cursor.rowcount > 0:
                    removed.append(name)
                else:
                    skipped.append(name)
            conn.commit()
        return removed, skipped

    def resolve_accounts(self, chat_id: int, names: list[str]) -> tuple[list[str], list[str]]:
        existing = set(self.list_accounts(chat_id))
        found = [name for name in names if name in existing]
        missing = [name for name in names if name not in existing]
        return found, missing

    def list_active_schedule_rules(self) -> list[ScheduleRule]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, channel_id, rule, is_active
                FROM schedule_rules
                WHERE is_active = 1
                ORDER BY id
                """
            ).fetchall()
        return [
            ScheduleRule(
                id=row["id"],
                channel_id=row["channel_id"],
                rule=row["rule"],
                is_active=bool(row["is_active"]),
            )
            for row in rows
        ]

    def list_escalation_rules(self, channel_id: int) -> list[EscalationRule]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, channel_id, rule, level
                FROM escalation_rules
                WHERE channel_id = ?
                ORDER BY level
                """,
                (channel_id,),
            ).fetchall()
        return [
            EscalationRule(
                id=row["id"],
                channel_id=row["channel_id"],
                rule=row["rule"],
                level=row["level"],
            )
            for row in rows
        ]

    def get_schedule_state(self, rule_id: int) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_run_at FROM schedule_state WHERE rule_id = ?",
                (rule_id,),
            ).fetchone()
        return row["last_run_at"] if row else None

    def update_schedule_state(self, rule_id: int, last_run_at: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO schedule_state (rule_id, last_run_at)
                VALUES (?, ?)
                ON CONFLICT(rule_id) DO UPDATE SET last_run_at = excluded.last_run_at
                """,
                (rule_id, last_run_at),
            )
            conn.commit()

    def add_post_event(self, channel_id: int, post_key: str) -> bool:
        with self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO post_events (channel_id, post_key) VALUES (?, ?)",
                    (channel_id, post_key),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def list_pending_post_events(
        self, channel_id: int | None = None, limit: int = 100
    ) -> list[PostEvent]:
        with self._connect() as conn:
            if channel_id is None:
                rows = conn.execute(
                    """
                    SELECT id, channel_id, post_key, status
                    FROM post_events
                    WHERE status = 'pending'
                    ORDER BY id
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, channel_id, post_key, status
                    FROM post_events
                    WHERE status = 'pending' AND channel_id = ?
                    ORDER BY id
                    LIMIT ?
                    """,
                    (channel_id, limit),
                ).fetchall()
        return [
            PostEvent(
                id=row["id"],
                channel_id=row["channel_id"],
                post_key=row["post_key"],
                status=row["status"],
            )
            for row in rows
        ]

    def mark_post_event_processed(self, event_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE post_events
                SET status = 'processed', processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (event_id,),
            )
            conn.commit()
