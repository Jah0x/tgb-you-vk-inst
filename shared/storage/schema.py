from __future__ import annotations

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chat_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS grids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chat_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS grid_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grid_id INTEGER NOT NULL,
        account_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(grid_id, account_id),
        FOREIGN KEY(grid_id) REFERENCES grids(id) ON DELETE CASCADE,
        FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS grid_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grid_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(grid_id) REFERENCES grids(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS grid_action_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grid_action_id INTEGER NOT NULL UNIQUE,
        type TEXT NOT NULL,
        payload_json TEXT,
        min_delay_s INTEGER,
        max_delay_s INTEGER,
        random_jitter_enabled INTEGER NOT NULL DEFAULT 0,
        account_selector TEXT,
        account_allocation TEXT,
        account_allocation_value TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(grid_action_id) REFERENCES grid_actions(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chat_id, name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schedule_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id INTEGER NOT NULL,
        rule TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS escalation_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id INTEGER NOT NULL,
        rule TEXT NOT NULL,
        level INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schedule_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_id INTEGER NOT NULL UNIQUE,
        last_run_at TEXT,
        FOREIGN KEY(rule_id) REFERENCES schedule_rules(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS post_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id INTEGER NOT NULL,
        post_key TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        processed_at TEXT,
        UNIQUE(channel_id, post_key),
        FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        applied_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """,
]
