# Chess Coach API

A conversational chess coaching backend powered by Claude + Stockfish. Claude handles all coaching language (plans, explanations, patterns), Stockfish handles all calculation (evaluation, best moves).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/sessions` | Create a coaching session |
| `GET` | `/api/sessions` | List sessions |
| `GET` | `/api/sessions/{id}` | Get session with messages |
| `DELETE` | `/api/sessions/{id}` | Delete session |
| `POST` | `/api/evaluate` | Quick position evaluation (FEN → score) |
| `POST` | `/api/evaluate/top-moves` | Top N candidate moves |
| `POST` | `/api/analyze` | Submit PGN for analysis |
| `GET` | `/api/history/patterns` | Cross-game pattern summary |
| `GET` | `/api/history/games` | List analyzed games |
| `GET` | `/api/openings/kid` | King's Indian Defense lines |
| `WS` | `/api/ws/coach/{session_id}` | Real-time coaching chat |

### WebSocket Protocol

```
Client → {"type": "message", "content": "What's the plan for white?"}
Server → {"type": "chunk", "content": "In this position..."}
Server → {"type": "chunk", "content": " white should..."}
Server → {"type": "eval_update", "eval": {"score_cp": 45, ...}}
Server → {"type": "done"}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `STOCKFISH_PATH` | No | Path to Stockfish binary (default: `stockfish`) |
| `CLAUDE_MODEL` | No | Claude model ID (default: `claude-sonnet-4-20250514`) |
| `CHESS_COACH_DB` | No | SQLite database path |
| `API_PORT` | No | Server port (default: `8000`) |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |

## Local Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
chess-coach serve        # Start API on port 8000
```

## Deploy on Railway

1. Connect this repo to Railway
2. Set `ANTHROPIC_API_KEY` in Railway environment variables
3. Stockfish is installed automatically via `nixpacks.toml`
4. Railway reads the `Procfile` to start the server

Interactive docs at `https://your-app.railway.app/docs`
