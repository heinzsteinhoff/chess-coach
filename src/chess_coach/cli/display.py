"""Rich-based terminal rendering for chess boards, evaluations, and analysis."""

from __future__ import annotations

import chess
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


console = Console()

# Unicode chess pieces
PIECE_SYMBOLS = {
    "K": "\u2654", "Q": "\u2655", "R": "\u2656", "B": "\u2657", "N": "\u2658", "P": "\u2659",
    "k": "\u265a", "q": "\u265b", "r": "\u265c", "b": "\u265d", "n": "\u265e", "p": "\u265f",
}

LIGHT_SQUARE = "on grey85"
DARK_SQUARE = "on grey50"


def render_board(board: chess.Board, flipped: bool = False) -> Panel:
    """Render a chess board using Unicode pieces with colored squares."""
    text = Text()
    ranks = range(8) if flipped else range(7, -1, -1)
    files = range(7, -1, -1) if flipped else range(8)

    for rank in ranks:
        # Rank label
        text.append(f" {rank + 1} ", style="bold")
        for file in files:
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            is_light = (rank + file) % 2 == 1
            bg = LIGHT_SQUARE if is_light else DARK_SQUARE

            if piece:
                symbol = PIECE_SYMBOLS.get(piece.symbol(), "?")
                color = "white" if piece.color == chess.WHITE else "black"
                text.append(f" {symbol} ", style=f"{color} {bg}")
            else:
                text.append("   ", style=bg)
        text.append("\n")

    # File labels
    file_labels = "abcdefgh" if not flipped else "hgfedcba"
    text.append("   ")
    for f in file_labels:
        text.append(f" {f} ")

    turn = "White" if board.turn == chess.WHITE else "Black"
    title = f"Position — {turn} to move"
    return Panel(text, title=title, border_style="blue")


def render_eval_bar(score_cp: int | None, score_mate: int | None, width: int = 30) -> str:
    """Render a horizontal evaluation bar like chess.com / lichess."""
    if score_mate is not None:
        if score_mate > 0:
            label = f"#({score_mate})"
            white_portion = width
        else:
            label = f"#({score_mate})"
            white_portion = 0
    elif score_cp is not None:
        # Clamp to ±1000 for display
        clamped = max(-1000, min(1000, score_cp))
        # Map [-1000, 1000] to [0, width]
        white_portion = int((clamped + 1000) / 2000 * width)
        if score_cp >= 0:
            label = f"+{score_cp / 100:.1f}"
        else:
            label = f"{score_cp / 100:.1f}"
    else:
        label = "?.?"
        white_portion = width // 2

    bar = "\u2588" * white_portion + "\u2591" * (width - white_portion)
    return f"[{bar}] {label}"


def render_eval_text(score_cp: int | None, score_mate: int | None) -> str:
    """Convert evaluation to human-readable text."""
    if score_mate is not None:
        if score_mate > 0:
            return f"White has mate in {score_mate}"
        return f"Black has mate in {abs(score_mate)}"

    if score_cp is None:
        return "Unknown evaluation"

    cp = score_cp
    if abs(cp) <= 30:
        return "roughly equal"
    if abs(cp) <= 60:
        side = "White" if cp > 0 else "Black"
        return f"slight edge for {side}"
    if abs(cp) <= 120:
        side = "White" if cp > 0 else "Black"
        return f"clear advantage for {side}"
    if abs(cp) <= 300:
        side = "White" if cp > 0 else "Black"
        return f"{side} is much better"

    side = "White" if cp > 0 else "Black"
    return f"{side} is winning"


def render_move_classification(classification: str) -> str:
    """Color-coded move classification."""
    colors = {
        "best": "[bold green]!!  Best[/]",
        "excellent": "[green]!  Excellent[/]",
        "good": "[dim green]Good[/]",
        "inaccuracy": "[yellow]?! Inaccuracy[/]",
        "mistake": "[red]?  Mistake[/]",
        "blunder": "[bold red]?? Blunder[/]",
    }
    return colors.get(classification, classification)


def render_move_table(moves: list[dict]) -> Table:
    """Render a move-by-move analysis table."""
    table = Table(title="Game Analysis", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("White", style="bold", min_width=8)
    table.add_column("Eval", justify="right", min_width=6)
    table.add_column("Black", style="bold", min_width=8)
    table.add_column("Eval", justify="right", min_width=6)
    table.add_column("Notes", min_width=20)

    for move_data in moves:
        move_num = str(move_data.get("number", ""))
        white_move = move_data.get("white_move", "")
        white_eval = move_data.get("white_eval", "")
        black_move = move_data.get("black_move", "")
        black_eval = move_data.get("black_eval", "")
        notes = move_data.get("notes", "")

        table.add_row(move_num, white_move, white_eval, black_move, black_eval, notes)

    return table


def print_welcome() -> None:
    """Print the welcome banner."""
    console.print(
        Panel(
            "[bold]Chess Coach[/bold]\n"
            "Your AI chess training partner powered by Claude + Stockfish\n\n"
            "Commands: analyze | position | opening | history | serve",
            title="♟ Chess Coach",
            border_style="bold blue",
        )
    )


def print_thinking() -> None:
    """Show a thinking indicator."""
    console.print("[dim]Coach is thinking...[/dim]")


def print_coach_response(text: str) -> None:
    """Print a formatted coach response."""
    from rich.markdown import Markdown

    console.print()
    console.print(Panel(Markdown(text), title="Coach", border_style="green"))
    console.print()
