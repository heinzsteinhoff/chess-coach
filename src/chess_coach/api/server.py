"""FastAPI application setup with lifespan management."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chess_coach.config import Config
from chess_coach.engine.stockfish import StockfishEngine
from chess_coach.storage.database import Database

load_dotenv()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage Stockfish engine and database lifecycle."""
    config: Config = app.state.config

    # Start Stockfish
    engine = StockfishEngine(
        path=config.stockfish_path,
        depth=config.stockfish_depth,
        threads=config.stockfish_threads,
        hash_mb=config.stockfish_hash_mb,
    )
    try:
        engine.start()
        logger.info("Stockfish started at: %s", config.stockfish_path)
    except Exception as e:
        logger.error("Failed to start Stockfish at '%s': %s", config.stockfish_path, e)
    app.state.engine = engine

    db = Database(config.db_path)
    db.connect()
    app.state.db = db

    yield

    engine.stop()
    db.close()


def create_app(config: Config | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = Config.from_env()

    app = FastAPI(
        title="Chess Coach API",
        description="AI chess coaching powered by Claude + Stockfish",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.config = config

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from chess_coach.api.routes import router
    from chess_coach.api.websocket import ws_router

    app.include_router(router, prefix="/api")
    app.include_router(ws_router, prefix="/api")

    return app


# Module-level app instance for Railway/uvicorn import (chess_coach.api.server:app)
app = create_app()
