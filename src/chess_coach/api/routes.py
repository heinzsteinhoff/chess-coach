"""REST API endpoints for sessions, games, history, and evaluation."""

from __future__ import annotations

import io

import chess
import chess.pgn
from fastapi import APIRouter, HTTPException, Request

from chess_coach.api.schemas import (
    AnalyzeRequest,
    EvalRequest,
    EvalResponse,
    GameResponse,
    PatternSummary,
    SessionCreate,
    SessionDetailResponse,
    SessionResponse,
    TopMoveResponse,
)
from chess_coach.cli.display import render_eval_text
from chess_coach.coach.session import CoachingMode, Session
from chess_coach.engine.stockfish import StockfishEngine
from chess_coach.storage.database import Database
from chess_coach.storage.repository import Repository

router = APIRouter()


def _get_engine(request: Request) -> StockfishEngine:
    return request.app.state.engine


def _get_repo(request: Request) -> Repository:
    return Repository(request.app.state.db)


@router.get("/health")
def health_check(request: Request) -> dict:
    """Health check for Railway/load balancers."""
    engine = _get_engine(request)
    return {
        "status": "healthy",
        "engine": "running" if engine._engine is not None else "stopped",
    }


@router.post("/sessions", response_model=SessionResponse)
def create_session(body: SessionCreate, request: Request) -> dict:
    """Create a new coaching session."""
    repo = _get_repo(request)

    mode = CoachingMode(body.mode)
    session = Session(mode=mode, game_pgn=body.pgn)

    # Validate FEN if provided
    if body.fen:
        try:
            chess.Board(body.fen)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid FEN: {e}")

    repo.save_session(session)
    return {
        "id": session.id,
        "mode": session.mode.value,
        "created_at": session.created_at.isoformat(),
        "ended_at": None,
        "summary": None,
    }


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(request: Request, limit: int = 20) -> list[dict]:
    """List recent coaching sessions."""
    repo = _get_repo(request)
    return repo.list_sessions(limit=limit)


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: str, request: Request) -> dict:
    """Get a session with messages and patterns."""
    repo = _get_repo(request)
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, request: Request) -> dict:
    """Delete a session."""
    repo = _get_repo(request)
    if not repo.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}


@router.post("/evaluate", response_model=EvalResponse)
def evaluate_position(body: EvalRequest, request: Request) -> dict:
    """Quick position evaluation via Stockfish (no coaching)."""
    engine = _get_engine(request)

    try:
        board = chess.Board(body.fen)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {e}")

    result = engine.evaluate(body.fen, depth=body.depth)
    return {
        "score_cp": result.score_cp,
        "score_mate": result.score_mate,
        "best_move_uci": result.best_move,
        "best_move_san": result.best_move_san,
        "pv": result.pv,
        "pv_san": result.pv_san,
        "depth": result.depth,
        "evaluation_text": render_eval_text(result.score_cp, result.score_mate),
    }


@router.post("/evaluate/top-moves", response_model=TopMoveResponse)
def get_top_moves(body: EvalRequest, request: Request, num_moves: int = 3) -> dict:
    """Get top N candidate moves with evaluations."""
    engine = _get_engine(request)

    try:
        chess.Board(body.fen)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {e}")

    results = engine.get_top_moves(body.fen, num_moves=num_moves, depth=body.depth)
    return {
        "moves": [
            {
                "score_cp": r.score_cp,
                "score_mate": r.score_mate,
                "best_move_uci": r.best_move,
                "best_move_san": r.best_move_san,
                "pv": r.pv,
                "pv_san": r.pv_san,
                "depth": r.depth,
                "evaluation_text": render_eval_text(r.score_cp, r.score_mate),
            }
            for r in results
        ]
    }


@router.post("/analyze", response_model=SessionResponse)
def analyze_game(body: AnalyzeRequest, request: Request) -> dict:
    """Submit a PGN for analysis. Creates a session."""
    try:
        game = chess.pgn.read_game(io.StringIO(body.pgn))
        if game is None:
            raise HTTPException(status_code=400, detail="Could not parse PGN")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PGN: {e}")

    repo = _get_repo(request)
    session = Session(mode=CoachingMode.GAME_ANALYSIS, game_pgn=body.pgn)

    headers = dict(game.headers)
    session.game_metadata = {
        "white": headers.get("White"),
        "black": headers.get("Black"),
        "result": headers.get("Result"),
        "eco": headers.get("ECO"),
        "opening": headers.get("Opening"),
        "side": body.side,
    }

    repo.save_session(session)

    # Save game record
    repo.save_game(
        session_id=session.id,
        pgn=body.pgn,
        white=headers.get("White"),
        black=headers.get("Black"),
        result=headers.get("Result"),
        eco=headers.get("ECO"),
        opening_name=headers.get("Opening"),
        date_played=headers.get("Date"),
    )

    return {
        "id": session.id,
        "mode": session.mode.value,
        "created_at": session.created_at.isoformat(),
        "ended_at": None,
        "summary": None,
    }


@router.get("/history/patterns", response_model=list[PatternSummary])
def get_patterns(request: Request) -> list[dict]:
    """Get cross-game pattern summary."""
    repo = _get_repo(request)
    return repo.get_pattern_summary()


@router.get("/history/games", response_model=list[GameResponse])
def list_games(request: Request, limit: int = 20) -> list[dict]:
    """List analyzed games."""
    repo = _get_repo(request)
    return repo.list_games(limit=limit)


@router.get("/openings/kid")
def get_kid_lines() -> dict:
    """Get King's Indian Defense main lines data."""
    from chess_coach.openings.kid import KID_LINES
    return {"opening": "King's Indian Defense", "variations": KID_LINES}
