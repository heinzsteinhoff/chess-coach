"""Tests for the storage layer."""

import tempfile
from pathlib import Path

from chess_coach.coach.session import CoachingMode, Session
from chess_coach.storage.database import Database
from chess_coach.storage.repository import Repository


def test_database_creates_schema():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        db.connect()
        # Check tables exist
        cursor = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]
        assert "sessions" in tables
        assert "messages" in tables
        assert "patterns" in tables
        assert "games" in tables
        db.close()


def test_save_and_list_sessions():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        db.connect()
        repo = Repository(db)

        session = Session(mode=CoachingMode.POSITION_DISCUSSION)
        session.add_user_message("What's the plan here?")
        session.add_assistant_message("In this position, White should...")
        session.end()

        repo.save_session(session)

        sessions = repo.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["mode"] == "position"
        assert sessions[0]["id"] == session.id

        db.close()


def test_get_session_detail():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        db.connect()
        repo = Repository(db)

        session = Session(mode=CoachingMode.GAME_ANALYSIS, game_pgn="1. e4 e5 *")
        session.add_user_message("Analyze this game")
        session.add_assistant_message("Let me walk through...")
        session.identified_patterns = [
            {"type": "tactical_miss", "description": "Missed fork on move 15", "positions": []},
        ]
        session.end()
        repo.save_session(session)

        detail = repo.get_session(session.id)
        assert detail is not None
        assert len(detail["messages"]) == 2
        assert len(detail["patterns"]) == 1
        assert detail["patterns"][0]["pattern_type"] == "tactical_miss"

        db.close()


def test_delete_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        db.connect()
        repo = Repository(db)

        session = Session(mode=CoachingMode.POSITION_DISCUSSION)
        session.add_user_message("Hello")
        repo.save_session(session)

        assert repo.delete_session(session.id)
        assert repo.get_session(session.id) is None
        assert not repo.delete_session("nonexistent")

        db.close()


def test_pattern_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        db.connect()
        repo = Repository(db)

        # Create two sessions with patterns
        for i in range(2):
            session = Session(mode=CoachingMode.GAME_ANALYSIS)
            session.identified_patterns = [
                {"type": "tactical_miss", "description": f"Missed tactic game {i+1}"},
            ]
            session.end()
            repo.save_session(session)

        session3 = Session(mode=CoachingMode.GAME_ANALYSIS)
        session3.identified_patterns = [
            {"type": "endgame_weakness", "description": "Poor rook endgame"},
        ]
        session3.end()
        repo.save_session(session3)

        patterns = repo.get_pattern_summary()
        assert len(patterns) == 2
        # tactical_miss should be first (2 occurrences)
        assert patterns[0]["pattern_type"] == "tactical_miss"
        assert patterns[0]["count"] == 2

        db.close()


def test_save_and_list_games():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        db.connect()
        repo = Repository(db)

        session = Session(mode=CoachingMode.GAME_ANALYSIS)
        repo.save_session(session)

        game_id = repo.save_game(
            session_id=session.id,
            pgn="1. e4 e5 2. Nf3 Nc6 *",
            white="Player1",
            black="Player2",
            result="1-0",
            eco="C44",
            opening_name="King's Pawn Game",
        )
        assert game_id > 0

        games = repo.list_games()
        assert len(games) == 1
        assert games[0]["white"] == "Player1"

        db.close()
