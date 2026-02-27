"""Core orchestration: the tool_use dispatch loop connecting Claude to Stockfish."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Callable

import anthropic

from chess_coach.coach.tools import STOCKFISH_TOOLS
from chess_coach.engine.stockfish import StockfishEngine
import chess


class ToolDispatcher:
    """Routes Claude's tool_use calls to the local Stockfish engine."""

    def __init__(self, engine: StockfishEngine):
        self._engine = engine
        self._handlers: dict[str, Callable] = {
            "evaluate_position": self._handle_evaluate,
            "get_best_move": self._handle_best_move,
            "evaluate_move_quality": self._handle_move_quality,
            "get_top_moves": self._handle_top_moves,
        }

    def dispatch(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool call and return the result as a JSON string."""
        handler = self._handlers.get(tool_name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        try:
            # Validate FEN if present
            if "fen" in tool_input:
                chess.Board(tool_input["fen"])  # Raises ValueError if invalid
            return handler(tool_input)
        except ValueError as e:
            return json.dumps({"error": f"Invalid input: {e}"})
        except Exception as e:
            return json.dumps({"error": f"Engine error: {e}"})

    def _handle_evaluate(self, inp: dict) -> str:
        result = self._engine.evaluate(inp["fen"], inp.get("depth"))
        return result.to_json()

    def _handle_best_move(self, inp: dict) -> str:
        uci, san = self._engine.best_move(inp["fen"], inp.get("time_limit", 1.0))
        return json.dumps({"best_move_uci": uci, "best_move_san": san})

    def _handle_move_quality(self, inp: dict) -> str:
        result = self._engine.evaluate_move_quality(inp["fen"], inp["move"])
        return result.to_json()

    def _handle_top_moves(self, inp: dict) -> str:
        results = self._engine.get_top_moves(inp["fen"], inp.get("num_moves", 3))
        return json.dumps([asdict(r) for r in results])


def coach_turn(
    client: anthropic.Anthropic,
    messages: list[dict],
    system_prompt: str,
    dispatcher: ToolDispatcher,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    on_text_chunk: Callable[[str], None] | None = None,
) -> str:
    """Execute a single coaching turn with tool-use loop.

    Sends messages to Claude, handles any tool calls by dispatching to Stockfish,
    feeds results back, and loops until Claude produces a final text response.

    Args:
        client: Anthropic API client.
        messages: Full conversation history.
        system_prompt: System prompt for the coaching mode.
        dispatcher: Tool dispatcher connected to Stockfish.
        model: Claude model to use.
        max_tokens: Maximum tokens in the response.
        on_text_chunk: Optional callback for streaming text chunks to the UI.

    Returns:
        The final text response from Claude.
    """
    while True:
        if on_text_chunk:
            # Use streaming for real-time output
            response_content = _stream_response(
                client, messages, system_prompt, model, max_tokens, on_text_chunk
            )
        else:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                tools=STOCKFISH_TOOLS,
                messages=messages,
            )
            response_content = response.content

        # Separate tool_use blocks from text blocks
        tool_use_blocks = [b for b in response_content if b.type == "tool_use"]
        text_blocks = [b for b in response_content if b.type == "text"]

        if not tool_use_blocks:
            # No tool calls — we're done
            return "\n".join(b.text for b in text_blocks)

        # There are tool calls — execute them and continue
        # Add assistant's response to messages
        messages.append({"role": "assistant", "content": response_content})

        # Execute each tool call
        tool_results = []
        for block in tool_use_blocks:
            result = dispatcher.dispatch(block.name, block.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                }
            )

        messages.append({"role": "user", "content": tool_results})
        # Loop continues — Claude will see tool results and respond


def _stream_response(
    client: anthropic.Anthropic,
    messages: list[dict],
    system_prompt: str,
    model: str,
    max_tokens: int,
    on_text_chunk: Callable[[str], None],
) -> list:
    """Stream a response, calling on_text_chunk for each text delta.

    Returns the full list of content blocks (same format as non-streaming).
    """
    content_blocks: list = []

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        tools=STOCKFISH_TOOLS,
        messages=messages,
    ) as stream:
        for event in stream:
            if event.type == "content_block_start":
                content_blocks.append(event.content_block)
            elif event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    on_text_chunk(event.delta.text)

    # Return the final message's content blocks
    return stream.get_final_message().content
