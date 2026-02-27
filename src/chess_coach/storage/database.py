"""SQLite database schema and connection management."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """\
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    created_at TEXT NOT NULL,
    ended_at TEXT,
    game_pgn TEXT,
    game_metadata_json TEXT,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    pattern_type TEXT NOT NULL,
    description TEXT NOT NULL,
    positions_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id),
    pgn TEXT NOT NULL,
    white TEXT,
    black TEXT,
    result TEXT,
    eco TEXT,
    opening_name TEXT,
    date_played TEXT,
    avg_centipawn_loss REAL,
    imported_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_session ON patterns(session_id);
CREATE INDEX IF NOT EXISTS idx_games_opening ON games(eco);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""


class Database:
    """SQLite database connection and schema management."""

    def __init__(self, db_path: Path):
        self._path = db_path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        """Connect to the database and ensure schema exists."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._conn

    def __enter__(self) -> Database:
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
