"""CRUD operations for sessions, patterns, and games."""

from __future__ import annotations

import json
from datetime import datetime

from chess_coach.coach.session import Session
from chess_coach.storage.database import Database


class Repository:
    """Data access layer for chess coach storage."""

    def __init__(self, db: Database):
        self._db = db

    def save_session(self, session: Session) -> None:
        """Save a coaching session with its messages and patterns."""
        conn = self._db.conn

        # Insert session
        conn.execute(
            """INSERT OR REPLACE INTO sessions
               (id, mode, created_at, ended_at, game_pgn, game_metadata_json, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session.id,
                session.mode.value,
                session.created_at.isoformat(),
                session.ended_at.isoformat() if session.ended_at else None,
                session.game_pgn,
                json.dumps(session.game_metadata) if session.game_metadata else None,
                None,  # Summary can be generated later
            ),
        )

        # Insert messages
        for msg in session.messages:
            # Only store user/assistant text messages for history
            role = msg.get("role", "")
            if role in ("user", "assistant"):
                content = msg.get("content", "")
                if isinstance(content, str):
                    content_json = json.dumps({"text": content})
                else:
                    content_json = json.dumps(content, default=str)

                conn.execute(
                    """INSERT INTO messages (session_id, role, content_json, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (session.id, role, content_json, datetime.now().isoformat()),
                )

        # Insert patterns
        for pattern in session.identified_patterns:
            conn.execute(
                """INSERT INTO patterns
                   (session_id, pattern_type, description, positions_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    session.id,
                    pattern.get("type", "unknown"),
                    pattern.get("description", ""),
                    json.dumps(pattern.get("positions", [])),
                    datetime.now().isoformat(),
                ),
            )

        conn.commit()

    def list_sessions(self, limit: int = 20) -> list[dict]:
        """List recent sessions."""
        cursor = self._db.conn.execute(
            """SELECT id, mode, created_at, ended_at, summary
               FROM sessions
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_session(self, session_id: str) -> dict | None:
        """Get a session by ID with its messages."""
        cursor = self._db.conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        session = dict(row)

        # Get messages
        msg_cursor = self._db.conn.execute(
            """SELECT role, content_json, created_at
               FROM messages
               WHERE session_id = ?
               ORDER BY id""",
            (session_id,),
        )
        session["messages"] = [dict(r) for r in msg_cursor.fetchall()]

        # Get patterns
        pat_cursor = self._db.conn.execute(
            """SELECT pattern_type, description, positions_json, created_at
               FROM patterns
               WHERE session_id = ?""",
            (session_id,),
        )
        session["patterns"] = [dict(r) for r in pat_cursor.fetchall()]

        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its related data."""
        conn = self._db.conn
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM patterns WHERE session_id = ?", (session_id,))
        cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cursor.rowcount > 0

    def get_pattern_summary(self) -> list[dict]:
        """Get aggregated pattern data across all sessions."""
        cursor = self._db.conn.execute(
            """SELECT pattern_type,
                      COUNT(*) as count,
                      GROUP_CONCAT(description, ' | ') as descriptions
               FROM patterns
               GROUP BY pattern_type
               ORDER BY count DESC"""
        )
        return [dict(row) for row in cursor.fetchall()]

    def save_game(
        self,
        session_id: str | None,
        pgn: str,
        white: str | None = None,
        black: str | None = None,
        result: str | None = None,
        eco: str | None = None,
        opening_name: str | None = None,
        date_played: str | None = None,
        avg_centipawn_loss: float | None = None,
    ) -> int:
        """Save an analyzed game record."""
        cursor = self._db.conn.execute(
            """INSERT INTO games
               (session_id, pgn, white, black, result, eco, opening_name,
                date_played, avg_centipawn_loss, imported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id, pgn, white, black, result, eco, opening_name,
                date_played, avg_centipawn_loss, datetime.now().isoformat(),
            ),
        )
        self._db.conn.commit()
        return cursor.lastrowid

    def list_games(self, limit: int = 20) -> list[dict]:
        """List recent games."""
        cursor = self._db.conn.execute(
            """SELECT id, white, black, result, eco, opening_name,
                      date_played, avg_centipawn_loss, imported_at
               FROM games
               ORDER BY imported_at DESC
               LIMIT ?""",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]
