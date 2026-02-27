"""Application configuration with defaults and environment variable overrides."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

# Common Stockfish install locations
_STOCKFISH_CANDIDATES = [
    "stockfish",                    # on PATH
    "/usr/games/stockfish",         # apt install stockfish (Debian/Ubuntu)
    "/usr/local/bin/stockfish",     # brew / manual install
    "/usr/bin/stockfish",           # some distros
]


def _find_stockfish() -> str:
    """Find the Stockfish binary, checking common install locations."""
    for candidate in _STOCKFISH_CANDIDATES:
        if shutil.which(candidate):
            return candidate
    return "stockfish"  # fallback, will fail with a clear error later


@dataclass
class Config:
    stockfish_path: str = field(default_factory=_find_stockfish)
    stockfish_depth: int = 20
    stockfish_threads: int = 2
    stockfish_hash_mb: int = 256

    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 4096

    db_path: Path = field(default_factory=lambda: Path.home() / ".chess_coach" / "history.db")

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = field(default_factory=lambda: ["*"])

    @classmethod
    def from_env(cls) -> Config:
        """Create config from environment variables with fallbacks to defaults."""
        config = cls()
        if val := os.getenv("STOCKFISH_PATH"):
            config.stockfish_path = val
        if val := os.getenv("STOCKFISH_DEPTH"):
            config.stockfish_depth = int(val)
        if val := os.getenv("CLAUDE_MODEL"):
            config.claude_model = val
        if val := os.getenv("CHESS_COACH_DB"):
            config.db_path = Path(val)
        if val := os.getenv("API_HOST"):
            config.api_host = val
        if val := os.getenv("API_PORT"):
            config.api_port = int(val)
        if val := os.getenv("CORS_ORIGINS"):
            config.cors_origins = [o.strip() for o in val.split(",")]
        return config
