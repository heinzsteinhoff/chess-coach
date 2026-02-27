"""Stockfish UCI engine wrapper using python-chess."""

from __future__ import annotations

import chess
import chess.engine
from dataclasses import dataclass, asdict
import json


@dataclass
class EvalResult:
    """Result of a position evaluation."""

    score_cp: int | None  # Centipawn score from white's perspective (None if mate)
    score_mate: int | None  # Mate in N moves (None if not mate, negative = black mates)
    best_move: str  # Best move in UCI notation
    best_move_san: str  # Best move in SAN notation
    pv: list[str]  # Principal variation in UCI notation
    pv_san: list[str]  # Principal variation in SAN notation
    depth: int

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class MoveQuality:
    """Assessment of how good a specific move was."""

    move_uci: str
    move_san: str
    eval_before: EvalResult
    eval_after: EvalResult
    centipawn_loss: int | None  # None if mate involved
    classification: str  # "best", "excellent", "good", "inaccuracy", "mistake", "blunder"

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class StockfishEngine:
    """Wrapper around Stockfish via python-chess's UCI interface."""

    def __init__(
        self,
        path: str = "stockfish",
        depth: int = 20,
        threads: int = 2,
        hash_mb: int = 256,
    ):
        self._path = path
        self._depth = depth
        self._engine: chess.engine.SimpleEngine | None = None
        self._options = {"Threads": threads, "Hash": hash_mb}

    def start(self) -> None:
        """Start the Stockfish process."""
        self._engine = chess.engine.SimpleEngine.popen_uci(self._path)
        self._engine.configure(self._options)

    def stop(self) -> None:
        """Stop the Stockfish process."""
        if self._engine:
            self._engine.quit()
            self._engine = None

    def __enter__(self) -> StockfishEngine:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()

    def _ensure_running(self) -> chess.engine.SimpleEngine:
        if self._engine is None:
            raise RuntimeError("Stockfish engine not started. Call start() first.")
        return self._engine

    def evaluate(self, fen: str, depth: int | None = None) -> EvalResult:
        """Evaluate a position and return score, best move, and principal variation."""
        engine = self._ensure_running()
        board = chess.Board(fen)
        info = engine.analyse(board, chess.engine.Limit(depth=depth or self._depth))

        score = info["score"].white()
        pv_moves = info.get("pv", [])

        # Convert PV to SAN
        pv_san = []
        temp_board = board.copy()
        for move in pv_moves:
            pv_san.append(temp_board.san(move))
            temp_board.push(move)

        best_move = pv_moves[0] if pv_moves else None

        return EvalResult(
            score_cp=score.score() if not score.is_mate() else None,
            score_mate=score.mate() if score.is_mate() else None,
            best_move=str(best_move) if best_move else "",
            best_move_san=board.san(best_move) if best_move else "",
            pv=[str(m) for m in pv_moves],
            pv_san=pv_san,
            depth=info.get("depth", 0),
        )

    def best_move(self, fen: str, time_limit: float = 1.0) -> tuple[str, str]:
        """Get the best move in a position. Returns (uci, san)."""
        engine = self._ensure_running()
        board = chess.Board(fen)
        result = engine.play(board, chess.engine.Limit(time=time_limit))
        move = result.move
        return str(move), board.san(move)

    def evaluate_move_quality(self, fen: str, move_uci: str) -> MoveQuality:
        """Evaluate how good a specific move was by comparing evals before and after."""
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci)
        move_san = board.san(move)

        eval_before = self.evaluate(fen)

        board.push(move)
        eval_after = self.evaluate(board.fen())

        # Compute centipawn loss
        cp_loss = self._compute_cp_loss(eval_before, eval_after, board.turn)
        classification = self._classify_move(cp_loss, eval_before, eval_after)

        return MoveQuality(
            move_uci=move_uci,
            move_san=move_san,
            eval_before=eval_before,
            eval_after=eval_after,
            centipawn_loss=cp_loss,
            classification=classification,
        )

    def get_top_moves(self, fen: str, num_moves: int = 3, depth: int | None = None) -> list[EvalResult]:
        """Get the top N candidate moves with evaluations using Multi-PV."""
        engine = self._ensure_running()
        board = chess.Board(fen)

        results = []
        with engine.analysis(board, chess.engine.Limit(depth=depth or self._depth), multipv=num_moves) as analysis:
            # Collect final results at target depth
            last_infos: dict[int, chess.engine.InfoDict] = {}
            for info in analysis:
                if "multipv" in info:
                    last_infos[info["multipv"]] = info
                if info.get("depth", 0) >= (depth or self._depth):
                    # Check if we have all PVs at this depth
                    if len(last_infos) >= num_moves:
                        break

        for pv_num in sorted(last_infos.keys()):
            info = last_infos[pv_num]
            score = info["score"].white()
            pv_moves = info.get("pv", [])

            pv_san = []
            temp_board = board.copy()
            for move in pv_moves:
                pv_san.append(temp_board.san(move))
                temp_board.push(move)

            best_move = pv_moves[0] if pv_moves else None
            results.append(
                EvalResult(
                    score_cp=score.score() if not score.is_mate() else None,
                    score_mate=score.mate() if score.is_mate() else None,
                    best_move=str(best_move) if best_move else "",
                    best_move_san=board.san(best_move) if best_move else "",
                    pv=[str(m) for m in pv_moves],
                    pv_san=pv_san,
                    depth=info.get("depth", 0),
                )
            )

        return results

    @staticmethod
    def _compute_cp_loss(
        eval_before: EvalResult, eval_after: EvalResult, turn_after: chess.Color
    ) -> int | None:
        """Compute centipawn loss from the perspective of the player who moved.

        turn_after is the color whose turn it is AFTER the move (i.e., the opponent).
        """
        if eval_before.score_cp is None or eval_after.score_cp is None:
            return None

        # eval_after is from white's perspective. After the move, it's the opponent's turn.
        # If it was white who moved (turn_after == BLACK), loss = before - after
        # If it was black who moved (turn_after == WHITE), loss = after - before (since
        # a higher score for white means worse for black)
        if turn_after == chess.BLACK:
            # White just moved
            return max(0, eval_before.score_cp - eval_after.score_cp)
        else:
            # Black just moved
            return max(0, eval_after.score_cp - eval_before.score_cp)

    @staticmethod
    def _classify_move(
        cp_loss: int | None, eval_before: EvalResult, eval_after: EvalResult
    ) -> str:
        """Classify a move based on centipawn loss."""
        # If mate is involved, handle specially
        if eval_before.score_mate is not None or eval_after.score_mate is not None:
            if eval_before.score_mate is not None and eval_after.score_mate is None:
                return "blunder"  # Lost a winning mate
            if eval_before.score_mate is None and eval_after.score_mate is not None:
                return "blunder"  # Allowed opponent to get mate
            return "good"

        if cp_loss is None:
            return "good"
        if cp_loss <= 10:
            return "best"
        if cp_loss <= 25:
            return "excellent"
        if cp_loss <= 50:
            return "good"
        if cp_loss <= 100:
            return "inaccuracy"
        if cp_loss <= 200:
            return "mistake"
        return "blunder"
