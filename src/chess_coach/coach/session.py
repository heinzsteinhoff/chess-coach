"""Session management for coaching conversations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class CoachingMode(Enum):
    GAME_ANALYSIS = "analysis"
    POSITION_DISCUSSION = "position"
    OPENING_COACH = "opening"
    HISTORY_REVIEW = "history"


@dataclass
class Session:
    """A coaching session with conversation history."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mode: CoachingMode = CoachingMode.GAME_ANALYSIS
    created_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime | None = None
    messages: list[dict] = field(default_factory=list)
    game_pgn: str | None = None
    game_metadata: dict = field(default_factory=dict)
    identified_patterns: list[dict] = field(default_factory=list)

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation."""
        self.messages.append({"role": "assistant", "content": content})

    def add_raw_messages(self, messages: list[dict]) -> None:
        """Add raw API messages (including tool_use/tool_result blocks)."""
        self.messages.extend(messages)

    def get_api_messages(self) -> list[dict]:
        """Return messages formatted for the Anthropic API."""
        return self.messages

    def end(self) -> None:
        """Mark the session as ended."""
        self.ended_at = datetime.now()
