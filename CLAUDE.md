# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Setup (requires Python >=3.11)
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
pytest tests/test_storage.py::test_save_and_list_sessions  # single test

# Lint
ruff check src/

# CLI commands
chess-coach analyze      # Game analysis from PGN
chess-coach position     # Position discussion from FEN
chess-coach opening      # King's Indian Defense coaching
chess-coach history      # Cross-game pattern review
chess-coach serve        # Start FastAPI server (default port 8000)

# Run as module
python -m chess_coach
```

## Required Environment

- `ANTHROPIC_API_KEY` — required for all coaching features
- Stockfish binary in PATH, or set `STOCKFISH_PATH` to the binary location
- Optional: `CLAUDE_MODEL`, `CHESS_COACH_DB`, `API_PORT`, `CORS_ORIGINS`

## Architecture

The system uses a **layered architecture** where Claude and Stockfish have strict separation: Claude never calculates, Stockfish never explains.

```
CLI (click+rich)  ←→  API (FastAPI+WebSocket)
         ↘                  ↙
        Coach Layer (shared core)
              ↓ ↑ tool_use loop
         Engine Layer (Stockfish UCI)
              ↓
         Storage Layer (SQLite)
```

**CLI and API are thin wrappers** over the same Coach Layer — no logic duplication.

### Coach Layer (`coach/`)

The core orchestration lives in `tool_loop.py`:
1. `coach_turn()` sends messages to Claude with Stockfish tool definitions
2. When Claude responds with `tool_use` blocks, `ToolDispatcher` routes calls to local Stockfish
3. Tool results feed back to Claude; loop repeats until Claude produces text-only response
4. Supports both buffered (CLI) and streaming (WebSocket) modes

Four tools are defined in `tools.py`: `evaluate_position`, `get_best_move`, `evaluate_move_quality`, `get_top_moves`. These are Anthropic API tool schemas dispatched locally — no MCP server.

System prompts in `system_prompts.py` define coaching behavior per mode (analysis, position, opening, history).

### Engine Layer (`engine/stockfish.py`)

Wraps `python-chess`'s `chess.engine.SimpleEngine`. Returns `EvalResult` and `MoveQuality` dataclasses. Move classification thresholds: ≤10cp best, ≤25 excellent, ≤50 good, ≤100 inaccuracy, ≤200 mistake, >200 blunder.

### API Layer (`api/`)

- REST routes in `routes.py`, WebSocket in `websocket.py`
- WebSocket protocol: client sends `{"type":"message","content":"..."}`, server streams `{"type":"chunk","content":"..."}` then `{"type":"done"}`
- `server.py` uses FastAPI lifespan to manage Stockfish engine + DB lifecycle
- Pydantic schemas in `schemas.py`

### Storage Layer (`storage/`)

SQLite with WAL mode. Four tables: `sessions`, `messages`, `patterns`, `games`. Repository pattern in `repository.py`. Cross-game pattern aggregation via `get_pattern_summary()` (GROUP BY pattern_type).

### Config (`config.py`)

Single `Config` dataclass with precedence: defaults → env vars (`Config.from_env()`) → CLI flags.

## Key Conventions

- All chess logic goes through `python-chess` — never parse FEN/PGN manually
- `ToolDispatcher` validates FEN before passing to Stockfish; returns `{"error":"..."}` JSON on failure
- Sessions are stateless from Claude's perspective — full conversation history lives in `Session.messages`
- The `openings/kid.py` module contains KID variation data (Classical, Sämisch, Four Pawns, Fianchetto, Averbakh)
- src-layout: packages under `src/chess_coach/`, entry point `chess_coach.cli.app:cli`
