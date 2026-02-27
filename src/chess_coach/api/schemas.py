"""Pydantic request/response models for the API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# --- Requests ---

class SessionCreate(BaseModel):
    mode: Literal["analysis", "position", "opening"] = "position"
    pgn: str | None = None
    fen: str | None = None
    side: Literal["white", "black", "both"] | None = None


class CoachMessage(BaseModel):
    content: str


class EvalRequest(BaseModel):
    fen: str
    depth: int = Field(default=20, ge=1, le=30)


class AnalyzeRequest(BaseModel):
    pgn: str
    side: Literal["white", "black", "both"] = "white"


# --- Responses ---

class SessionResponse(BaseModel):
    id: str
    mode: str
    created_at: str
    ended_at: str | None = None
    summary: str | None = None


class SessionDetailResponse(SessionResponse):
    messages: list[dict] = []
    patterns: list[dict] = []
    game_pgn: str | None = None


class EvalResponse(BaseModel):
    score_cp: int | None = None
    score_mate: int | None = None
    best_move_uci: str
    best_move_san: str
    pv: list[str]
    pv_san: list[str]
    depth: int
    evaluation_text: str


class TopMoveResponse(BaseModel):
    moves: list[EvalResponse]


class PatternSummary(BaseModel):
    pattern_type: str
    count: int
    descriptions: str


class GameResponse(BaseModel):
    id: int
    white: str | None = None
    black: str | None = None
    result: str | None = None
    eco: str | None = None
    opening_name: str | None = None
    date_played: str | None = None
    avg_centipawn_loss: float | None = None


# --- WebSocket messages ---

class WSIncoming(BaseModel):
    type: Literal["message"] = "message"
    content: str


class WSOutgoing(BaseModel):
    type: Literal["chunk", "board_update", "eval_update", "done", "error"]
    content: str | None = None
    fen: str | None = None
    eval: dict | None = None
