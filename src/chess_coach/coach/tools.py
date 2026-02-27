"""Stockfish tool definitions for the Anthropic tool_use API."""

STOCKFISH_TOOLS = [
    {
        "name": "evaluate_position",
        "description": (
            "Evaluate a chess position using Stockfish engine. "
            "Returns centipawn score (positive = white advantage), best move, "
            "and principal variation (the expected best play sequence). "
            "Use this when you need an objective assessment of who stands better."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fen": {
                    "type": "string",
                    "description": "FEN string of the position to evaluate",
                },
                "depth": {
                    "type": "integer",
                    "description": "Search depth (default 20, max 30). Higher = slower but more accurate",
                },
            },
            "required": ["fen"],
        },
    },
    {
        "name": "get_best_move",
        "description": (
            "Get the single best move in a position according to Stockfish. "
            "Returns the move in both UCI and standard algebraic notation. "
            "Use this when asked what the best continuation is."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fen": {
                    "type": "string",
                    "description": "FEN string of the position",
                },
                "time_limit": {
                    "type": "number",
                    "description": "Time in seconds for Stockfish to think (default 1.0)",
                },
            },
            "required": ["fen"],
        },
    },
    {
        "name": "evaluate_move_quality",
        "description": (
            "Evaluate how good a specific move was by comparing the position "
            "evaluation before and after the move. Returns centipawn loss and "
            "a classification: best, excellent, good, inaccuracy, mistake, or blunder. "
            "Use this to judge whether a player's move was a mistake."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fen": {
                    "type": "string",
                    "description": "FEN string of the position BEFORE the move was played",
                },
                "move": {
                    "type": "string",
                    "description": "The move in UCI notation (e.g., 'e2e4', 'g1f3', 'e7e8q')",
                },
            },
            "required": ["fen", "move"],
        },
    },
    {
        "name": "get_top_moves",
        "description": (
            "Get the top N candidate moves in a position with their evaluations. "
            "Shows alternatives the player could have considered. Each move includes "
            "its evaluation score and the expected continuation. "
            "Use this to explore what options were available."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fen": {
                    "type": "string",
                    "description": "FEN string of the position",
                },
                "num_moves": {
                    "type": "integer",
                    "description": "Number of top moves to return (default 3, max 5)",
                },
            },
            "required": ["fen"],
        },
    },
]
