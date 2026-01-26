from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class TgAccountRecord:
    phone: str
    status: str
    has_session: bool
    created_at: str | None
    last_login_at: str | None
    last_code_sent_at: str | None


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS tg_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'new',
    session_string TEXT,
    phone_code_hash TEXT,
    last_code_sent_at TEXT,
    last_login_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS tg_accounts (
    id SERIAL PRIMARY KEY,
    phone TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'new',
    session_string TEXT,
    phone_code_hash TEXT,
    last_code_sent_at TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
)
"""


def _parse_scheme(db_url: str) -> str:
    parsed = urlparse(db_url)
    return parsed.scheme


def init_tg_db(db_url: str) -> None:
    scheme = _parse_scheme(db_url)
    if scheme.startswith("sqlite"):
        conn = sqlite3.connect(_sqlite_path(db_url))
        try:
            conn.execute(SQLITE_SCHEMA)
            conn.commit()
        finally:
            conn.close()
        return
    if scheme in {"postgres", "postgresql"}:
        import psycopg2

        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(POSTGRES_SCHEMA)
            conn.commit()
        return
    raise ValueError(f"Unsupported tg db scheme: {scheme}")


def _sqlite_path(db_url: str) -> str:
    parsed = urlparse(db_url)
    if parsed.scheme != "sqlite":
        raise ValueError("Only sqlite DB_URL is supported")
    if parsed.path:
        return parsed.path
    raise ValueError("DB_URL must include a path, e.g. sqlite:////data/app.db")


def list_tg_accounts(db_url: str) -> list[TgAccountRecord]:
    scheme = _parse_scheme(db_url)
    if scheme.startswith("sqlite"):
        conn = sqlite3.connect(_sqlite_path(db_url))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT phone, status, session_string, created_at, last_login_at, last_code_sent_at
                FROM tg_accounts
                ORDER BY created_at DESC
                """
            ).fetchall()
        finally:
            conn.close()
        return [
            TgAccountRecord(
                phone=row["phone"],
                status=row["status"],
                has_session=bool(row["session_string"]),
                created_at=row["created_at"],
                last_login_at=row["last_login_at"],
                last_code_sent_at=row["last_code_sent_at"],
            )
            for row in rows
        ]
    if scheme in {"postgres", "postgresql"}:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        with psycopg2.connect(db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT phone, status, session_string, created_at, last_login_at, last_code_sent_at
                    FROM tg_accounts
                    ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
        return [
            TgAccountRecord(
                phone=row["phone"],
                status=row["status"],
                has_session=bool(row["session_string"]),
                created_at=_format_datetime(row.get("created_at")),
                last_login_at=_format_datetime(row.get("last_login_at")),
                last_code_sent_at=_format_datetime(row.get("last_code_sent_at")),
            )
            for row in rows
        ]
    raise ValueError(f"Unsupported tg db scheme: {scheme}")


def record_code_sent(db_url: str, phone: str, code_hash: str) -> None:
    scheme = _parse_scheme(db_url)
    if scheme.startswith("sqlite"):
        conn = sqlite3.connect(_sqlite_path(db_url))
        try:
            conn.execute(
                """
                INSERT INTO tg_accounts (phone, status, phone_code_hash, last_code_sent_at)
                VALUES (?, 'code_sent', ?, CURRENT_TIMESTAMP)
                ON CONFLICT(phone) DO UPDATE SET
                    status = excluded.status,
                    phone_code_hash = excluded.phone_code_hash,
                    last_code_sent_at = excluded.last_code_sent_at
                """,
                (phone, code_hash),
            )
            conn.commit()
        finally:
            conn.close()
        return
    if scheme in {"postgres", "postgresql"}:
        import psycopg2

        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tg_accounts (phone, status, phone_code_hash, last_code_sent_at)
                    VALUES (%s, 'code_sent', %s, NOW())
                    ON CONFLICT (phone) DO UPDATE SET
                        status = EXCLUDED.status,
                        phone_code_hash = EXCLUDED.phone_code_hash,
                        last_code_sent_at = EXCLUDED.last_code_sent_at
                    """,
                    (phone, code_hash),
                )
            conn.commit()
        return
    raise ValueError(f"Unsupported tg db scheme: {scheme}")


def record_session(db_url: str, phone: str, session_string: str) -> None:
    scheme = _parse_scheme(db_url)
    if scheme.startswith("sqlite"):
        conn = sqlite3.connect(_sqlite_path(db_url))
        try:
            conn.execute(
                """
                INSERT INTO tg_accounts (phone, status, session_string, last_login_at, phone_code_hash)
                VALUES (?, 'active', ?, CURRENT_TIMESTAMP, NULL)
                ON CONFLICT(phone) DO UPDATE SET
                    status = excluded.status,
                    session_string = excluded.session_string,
                    last_login_at = excluded.last_login_at,
                    phone_code_hash = NULL
                """,
                (phone, session_string),
            )
            conn.commit()
        finally:
            conn.close()
        return
    if scheme in {"postgres", "postgresql"}:
        import psycopg2

        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tg_accounts (phone, status, session_string, last_login_at, phone_code_hash)
                    VALUES (%s, 'active', %s, NOW(), NULL)
                    ON CONFLICT (phone) DO UPDATE SET
                        status = EXCLUDED.status,
                        session_string = EXCLUDED.session_string,
                        last_login_at = EXCLUDED.last_login_at,
                        phone_code_hash = NULL
                    """,
                    (phone, session_string),
                )
            conn.commit()
        return
    raise ValueError(f"Unsupported tg db scheme: {scheme}")


def get_code_hash(db_url: str, phone: str) -> str | None:
    scheme = _parse_scheme(db_url)
    if scheme.startswith("sqlite"):
        conn = sqlite3.connect(_sqlite_path(db_url))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT phone_code_hash FROM tg_accounts WHERE phone = ?",
                (phone,),
            ).fetchone()
        finally:
            conn.close()
        return row["phone_code_hash"] if row else None
    if scheme in {"postgres", "postgresql"}:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        with psycopg2.connect(db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT phone_code_hash FROM tg_accounts WHERE phone = %s",
                    (phone,),
                )
                row = cur.fetchone()
        return row["phone_code_hash"] if row else None
    raise ValueError(f"Unsupported tg db scheme: {scheme}")


def _format_datetime(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
