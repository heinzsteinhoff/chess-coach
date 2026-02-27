"""Main CLI application with Click commands."""

from __future__ import annotations

import io
import sys

import chess
import chess.pgn
import click
from dotenv import load_dotenv

load_dotenv()
from rich.console import Console
from rich.prompt import Prompt

import anthropic

from chess_coach.config import Config
from chess_coach.coach.session import CoachingMode, Session
from chess_coach.coach.system_prompts import (
    GAME_ANALYSIS_PROMPT,
    HISTORY_ANALYSIS_PROMPT,
    OPENING_COACH_KID_PROMPT,
    POSITION_DISCUSSION_PROMPT,
)
from chess_coach.coach.tool_loop import ToolDispatcher, coach_turn
from chess_coach.cli.display import (
    console,
    print_coach_response,
    print_welcome,
    render_board,
    render_eval_bar,
    render_eval_text,
)
from chess_coach.engine.stockfish import StockfishEngine
from chess_coach.storage.database import Database
from chess_coach.storage.repository import Repository


@click.group()
@click.option("--stockfish-path", envvar="STOCKFISH_PATH", default=None, help="Path to Stockfish binary")
@click.option("--model", envvar="CLAUDE_MODEL", default=None, help="Claude model to use")
@click.option("--db-path", envvar="CHESS_COACH_DB", default=None, help="Path to session database")
@click.pass_context
def cli(ctx: click.Context, stockfish_path: str | None, model: str | None, db_path: str | None) -> None:
    """Chess Coach — your AI chess training partner."""
    ctx.ensure_object(dict)
    config = Config.from_env()
    if stockfish_path:
        config.stockfish_path = stockfish_path
    if model:
        config.claude_model = model
    if db_path:
        from pathlib import Path
        config.db_path = Path(db_path)
    ctx.obj["config"] = config


def _create_engine(config: Config) -> StockfishEngine:
    """Create and start the Stockfish engine."""
    engine = StockfishEngine(
        path=config.stockfish_path,
        depth=config.stockfish_depth,
        threads=config.stockfish_threads,
        hash_mb=config.stockfish_hash_mb,
    )
    try:
        engine.start()
    except Exception as e:
        console.print(f"[bold red]Error:[/] Could not start Stockfish at '{config.stockfish_path}'")
        console.print(f"[dim]{e}[/dim]")
        console.print("\nMake sure Stockfish is installed and accessible.")
        console.print("Install: sudo apt install stockfish  OR  brew install stockfish")
        console.print("Or set STOCKFISH_PATH environment variable to the binary path.")
        raise SystemExit(1)
    return engine


def _create_client() -> anthropic.Anthropic:
    """Create the Anthropic API client."""
    try:
        return anthropic.Anthropic()
    except anthropic.AuthenticationError:
        console.print("[bold red]Error:[/] ANTHROPIC_API_KEY not set or invalid.")
        console.print("Set it with: export ANTHROPIC_API_KEY=your-key-here")
        raise SystemExit(1)


def _coaching_loop(
    session: Session,
    system_prompt: str,
    dispatcher: ToolDispatcher,
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int,
    initial_message: str | None = None,
) -> None:
    """Run the interactive coaching conversation loop."""
    messages = session.get_api_messages()

    if initial_message:
        session.add_user_message(initial_message)

    # First turn
    if messages:
        console.print("[dim]Coach is analyzing...[/dim]")
        response = coach_turn(
            client=client,
            messages=session.get_api_messages(),
            system_prompt=system_prompt,
            dispatcher=dispatcher,
            model=model,
            max_tokens=max_tokens,
        )
        session.add_assistant_message(response)
        print_coach_response(response)

    # Interactive loop
    while True:
        try:
            user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session ended.[/dim]")
            break

        if not user_input.strip():
            continue

        if user_input.strip().lower() in ("/quit", "/exit", "/q"):
            console.print("[dim]Session ended.[/dim]")
            break

        if user_input.strip().lower() == "/board":
            # Show current board state if we have a FEN
            console.print("[dim]Use this in position or analysis mode with a loaded position.[/dim]")
            continue

        session.add_user_message(user_input)

        console.print("[dim]Coach is thinking...[/dim]")
        response = coach_turn(
            client=client,
            messages=session.get_api_messages(),
            system_prompt=system_prompt,
            dispatcher=dispatcher,
            model=model,
            max_tokens=max_tokens,
        )
        session.add_assistant_message(response)
        print_coach_response(response)

    session.end()


@cli.command()
@click.pass_context
def analyze(ctx: click.Context) -> None:
    """Analyze a complete game from PGN."""
    config: Config = ctx.obj["config"]
    print_welcome()

    console.print("\n[bold blue]Game Analysis Mode[/bold blue]")
    console.print("Paste your PGN below. Press Enter twice when done.\n")

    # Read multiline PGN
    lines = []
    empty_count = 0
    try:
        while True:
            line = input()
            if line.strip() == "":
                empty_count += 1
                if empty_count >= 2:
                    break
                lines.append(line)
            else:
                empty_count = 0
                lines.append(line)
    except (KeyboardInterrupt, EOFError):
        if not lines:
            console.print("[dim]No PGN provided. Exiting.[/dim]")
            return

    pgn_text = "\n".join(lines).strip()
    if not pgn_text:
        console.print("[red]No PGN provided.[/red]")
        return

    # Parse PGN
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if game is None:
            console.print("[red]Could not parse PGN.[/red]")
            return
    except Exception as e:
        console.print(f"[red]Invalid PGN: {e}[/red]")
        return

    # Extract game info
    headers = dict(game.headers)
    white = headers.get("White", "Unknown")
    black = headers.get("Black", "Unknown")
    result = headers.get("Result", "*")
    opening = headers.get("Opening", headers.get("ECO", "Unknown"))

    console.print(f"\n[bold]Game:[/bold] {white} vs {black}")
    console.print(f"[bold]Result:[/bold] {result}")
    console.print(f"[bold]Opening:[/bold] {opening}")

    # Build move list with FEN at each position
    board = game.board()
    moves_data = []
    for move in game.mainline_moves():
        fen_before = board.fen()
        san = board.san(move)
        uci = move.uci()
        board.push(move)
        moves_data.append({
            "fen_before": fen_before,
            "fen_after": board.fen(),
            "san": san,
            "uci": uci,
            "move_number": board.fullmove_number,
            "color": "black" if board.turn == chess.WHITE else "white",  # who just moved
        })

    # Show final position
    console.print()
    console.print(render_board(board))

    # Prepare coaching message
    moves_text = []
    move_num = 1
    for i, m in enumerate(moves_data):
        if m["color"] == "white":
            moves_text.append(f"{move_num}. {m['san']}")
        else:
            moves_text[-1] += f" {m['san']}"
            move_num += 1

    initial_msg = (
        f"Please analyze this chess game:\n\n"
        f"White: {white}\nBlack: {black}\nResult: {result}\nOpening: {opening}\n\n"
        f"Moves: {' '.join(moves_text)}\n\n"
        f"PGN:\n{pgn_text}\n\n"
        f"The game has {len(moves_data)} half-moves. "
        f"Please walk through the game and identify the critical moments, "
        f"mistakes, and patterns. For each critical position, use the FEN to evaluate with your tools. "
        f"Here are the FEN positions at each move for your reference:\n\n"
    )

    # Add key positions (every move would be too much, focus on transitions)
    for i, m in enumerate(moves_data):
        initial_msg += f"After {m['color']}'s {m['san']} (move {m['move_number']}): FEN = {m['fen_after']}\n"

    # Ask which side the user played
    side = Prompt.ask(
        "Which side did you play?",
        choices=["white", "black", "both"],
        default="white",
    )
    initial_msg += f"\nThe student played as {side}. Focus your analysis on {side}'s play."

    # Setup and run
    engine = _create_engine(config)
    client = _create_client()
    dispatcher = ToolDispatcher(engine)
    session = Session(mode=CoachingMode.GAME_ANALYSIS, game_pgn=pgn_text)

    try:
        _coaching_loop(
            session=session,
            system_prompt=GAME_ANALYSIS_PROMPT,
            dispatcher=dispatcher,
            client=client,
            model=config.claude_model,
            max_tokens=config.claude_max_tokens,
            initial_message=initial_msg,
        )
    finally:
        engine.stop()

    # Save session
    _save_session(session, config)


@cli.command()
@click.pass_context
def position(ctx: click.Context) -> None:
    """Discuss a specific position from FEN."""
    config: Config = ctx.obj["config"]
    print_welcome()

    console.print("\n[bold green]Position Discussion Mode[/bold green]")
    fen = Prompt.ask("Paste the FEN string")

    # Validate FEN
    try:
        board = chess.Board(fen)
    except ValueError as e:
        console.print(f"[red]Invalid FEN: {e}[/red]")
        return

    # Display board
    console.print()
    console.print(render_board(board))

    # Quick Stockfish eval
    engine = _create_engine(config)
    client = _create_client()
    dispatcher = ToolDispatcher(engine)

    eval_result = engine.evaluate(fen)
    eval_bar = render_eval_bar(eval_result.score_cp, eval_result.score_mate)
    eval_text = render_eval_text(eval_result.score_cp, eval_result.score_mate)
    console.print(f"\n[dim]Quick eval: {eval_bar} ({eval_text})[/dim]")

    # Build initial message
    turn = "White" if board.turn == chess.WHITE else "Black"
    initial_msg = (
        f"Here is a chess position I'd like to discuss:\n\n"
        f"FEN: {fen}\n"
        f"It is {turn}'s turn to move.\n\n"
        f"Please analyze this position thoroughly. What are the key features? "
        f"What should each side be doing? What are the best candidate moves?"
    )

    session = Session(mode=CoachingMode.POSITION_DISCUSSION)

    try:
        _coaching_loop(
            session=session,
            system_prompt=POSITION_DISCUSSION_PROMPT,
            dispatcher=dispatcher,
            client=client,
            model=config.claude_model,
            max_tokens=config.claude_max_tokens,
            initial_message=initial_msg,
        )
    finally:
        engine.stop()

    _save_session(session, config)


@cli.command()
@click.pass_context
def opening(ctx: click.Context) -> None:
    """King's Indian Defense coaching."""
    config: Config = ctx.obj["config"]
    print_welcome()

    console.print("\n[bold yellow]Opening Coach: King's Indian Defense[/bold yellow]")
    console.print("\nChoose a mode:")
    console.print("  [bold]1[/bold] — Learn main lines (walk through key variations)")
    console.print("  [bold]2[/bold] — Analyze your KID game (paste a PGN)")
    console.print("  [bold]3[/bold] — Quiz me (test your KID knowledge)")

    choice = Prompt.ask("Select mode", choices=["1", "2", "3"], default="1")

    engine = _create_engine(config)
    client = _create_client()
    dispatcher = ToolDispatcher(engine)
    session = Session(mode=CoachingMode.OPENING_COACH)

    if choice == "1":
        initial_msg = (
            "I want to learn the King's Indian Defense. "
            "Please walk me through the main lines, starting with the Classical variation. "
            "For each move, explain the IDEAS behind it — what Black is trying to achieve, "
            "what White's plan is, and why this specific move order matters. "
            "Show me the key positions where Black needs to make important decisions. "
            "Start from 1. d4 Nf6 2. c4 g6."
        )
    elif choice == "2":
        console.print("\nPaste your KID game PGN. Press Enter twice when done.\n")
        lines = []
        empty_count = 0
        try:
            while True:
                line = input()
                if line.strip() == "":
                    empty_count += 1
                    if empty_count >= 2:
                        break
                    lines.append(line)
                else:
                    empty_count = 0
                    lines.append(line)
        except (KeyboardInterrupt, EOFError):
            pass

        pgn_text = "\n".join(lines).strip()
        if not pgn_text:
            console.print("[red]No PGN provided.[/red]")
            engine.stop()
            return

        initial_msg = (
            f"Please analyze this King's Indian Defense game with special attention to "
            f"the typical KID strategic themes:\n\n{pgn_text}\n\n"
            f"Focus on: Was the kingside attack timed correctly? Was ...f5 played at the "
            f"right moment? How was the pawn structure handled? Were there missed thematic ideas?"
        )
    else:
        initial_msg = (
            "Quiz me on the King's Indian Defense! Show me a position from a KID game "
            "and ask me what I would play. Start with an intermediate-level position from "
            "the Classical variation. After I answer, evaluate my choice and explain the "
            "correct continuation with its strategic ideas."
        )

    try:
        _coaching_loop(
            session=session,
            system_prompt=OPENING_COACH_KID_PROMPT,
            dispatcher=dispatcher,
            client=client,
            model=config.claude_model,
            max_tokens=config.claude_max_tokens,
            initial_message=initial_msg,
        )
    finally:
        engine.stop()

    _save_session(session, config)


@cli.command()
@click.pass_context
def history(ctx: click.Context) -> None:
    """Review past sessions and identify cross-game patterns."""
    config: Config = ctx.obj["config"]
    print_welcome()

    console.print("\n[bold magenta]Session History & Patterns[/bold magenta]")

    db = Database(config.db_path)
    db.connect()
    repo = Repository(db)

    try:
        sessions = repo.list_sessions(limit=20)
        if not sessions:
            console.print("[dim]No sessions found. Start analyzing some games first![/dim]")
            return

        console.print(f"\n[bold]Last {len(sessions)} sessions:[/bold]\n")
        for s in sessions:
            mode_color = {
                "analysis": "blue",
                "position": "green",
                "opening": "yellow",
                "history": "magenta",
            }.get(s["mode"], "white")
            console.print(
                f"  [{mode_color}]{s['mode']:>10}[/] | {s['created_at'][:16]} | "
                f"{s.get('summary', 'No summary')}"
            )

        # Get cross-game patterns
        patterns = repo.get_pattern_summary()
        if patterns:
            console.print("\n[bold]Recurring Patterns Across Games:[/bold]\n")
            for p in patterns:
                console.print(
                    f"  [yellow]{p['pattern_type']}[/yellow] ({p['count']} occurrences): "
                    f"{p['descriptions'][:100]}"
                )

            # Ask Claude to summarize
            client = _create_client()
            pattern_text = "\n".join(
                f"- {p['pattern_type']} ({p['count']}x): {p['descriptions']}"
                for p in patterns
            )
            console.print("\n[dim]Getting coaching summary...[/dim]")

            response = client.messages.create(
                model=config.claude_model,
                max_tokens=config.claude_max_tokens,
                system=HISTORY_ANALYSIS_PROMPT,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Here are the recurring patterns from the student's recent games:\n\n"
                        f"{pattern_text}\n\n"
                        f"Please provide a coaching summary with specific improvement suggestions."
                    ),
                }],
            )
            print_coach_response(response.content[0].text)
    finally:
        db.close()


@cli.command()
@click.option("--host", default=None, help="API server host")
@click.option("--port", default=None, type=int, help="API server port")
@click.pass_context
def serve(ctx: click.Context, host: str | None, port: int | None) -> None:
    """Start the API server for web frontend integration."""
    config: Config = ctx.obj["config"]
    if host:
        config.api_host = host
    if port:
        config.api_port = port

    console.print(f"\n[bold]Starting Chess Coach API server[/bold]")
    console.print(f"  Host: {config.api_host}")
    console.print(f"  Port: {config.api_port}")
    console.print(f"  CORS: {config.cors_origins}")
    console.print(f"\n  API docs: http://{config.api_host}:{config.api_port}/docs\n")

    import uvicorn
    from chess_coach.api.server import create_app

    app = create_app(config)
    uvicorn.run(app, host=config.api_host, port=config.api_port)


def _save_session(session: Session, config: Config) -> None:
    """Save a completed session to the database."""
    try:
        db = Database(config.db_path)
        db.connect()
        repo = Repository(db)
        repo.save_session(session)
        db.close()
        console.print(f"[dim]Session saved ({session.id[:8]}...)[/dim]")
    except Exception as e:
        console.print(f"[dim]Could not save session: {e}[/dim]")


if __name__ == "__main__":
    cli()
