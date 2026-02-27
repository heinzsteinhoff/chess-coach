"""WebSocket endpoint for real-time coaching conversations."""

from __future__ import annotations

import json

import anthropic
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from chess_coach.api.schemas import WSOutgoing
from chess_coach.coach.session import CoachingMode, Session
from chess_coach.coach.system_prompts import (
    GAME_ANALYSIS_PROMPT,
    OPENING_COACH_KID_PROMPT,
    POSITION_DISCUSSION_PROMPT,
)
from chess_coach.coach.tool_loop import ToolDispatcher
from chess_coach.coach.tools import STOCKFISH_TOOLS
from chess_coach.storage.repository import Repository

ws_router = APIRouter()

MODE_PROMPTS = {
    CoachingMode.GAME_ANALYSIS: GAME_ANALYSIS_PROMPT,
    CoachingMode.POSITION_DISCUSSION: POSITION_DISCUSSION_PROMPT,
    CoachingMode.OPENING_COACH: OPENING_COACH_KID_PROMPT,
}


@ws_router.websocket("/ws/coach/{session_id}")
async def coaching_websocket(websocket: WebSocket, session_id: str) -> None:
    """Real-time coaching conversation via WebSocket.

    The client sends messages like: {"type": "message", "content": "What's the plan?"}
    The server streams back:
        {"type": "chunk", "content": "In this position..."}
        {"type": "done"}
    """
    await websocket.accept()

    config = websocket.app.state.config
    engine = websocket.app.state.engine
    db = websocket.app.state.db
    repo = Repository(db)

    # Load or create session
    session_data = repo.get_session(session_id)
    if session_data:
        mode = CoachingMode(session_data["mode"])
        session = Session(id=session_id, mode=mode)
        # Restore messages from DB
        for msg in session_data.get("messages", []):
            content = msg.get("content_json", "{}")
            try:
                parsed = json.loads(content)
                text = parsed.get("text", content)
            except (json.JSONDecodeError, AttributeError):
                text = str(content)
            session.messages.append({"role": msg["role"], "content": text})
    else:
        session = Session(id=session_id, mode=CoachingMode.POSITION_DISCUSSION)

    system_prompt = MODE_PROMPTS.get(session.mode, POSITION_DISCUSSION_PROMPT)
    dispatcher = ToolDispatcher(engine)

    try:
        client = anthropic.Anthropic()
    except Exception as e:
        await websocket.send_json(
            WSOutgoing(type="error", content=f"API key error: {e}").model_dump()
        )
        await websocket.close()
        return

    try:
        while True:
            # Wait for client message
            data = await websocket.receive_json()
            user_content = data.get("content", "")
            if not user_content:
                continue

            session.add_user_message(user_content)
            messages = session.get_api_messages()

            # Run the tool-use loop with streaming
            try:
                final_text = await _streaming_coach_turn(
                    websocket=websocket,
                    client=client,
                    messages=messages,
                    system_prompt=system_prompt,
                    dispatcher=dispatcher,
                    model=config.claude_model,
                    max_tokens=config.claude_max_tokens,
                )
                session.add_assistant_message(final_text)

                # Send done signal
                await websocket.send_json(
                    WSOutgoing(type="done").model_dump()
                )

            except Exception as e:
                await websocket.send_json(
                    WSOutgoing(type="error", content=str(e)).model_dump()
                )

    except WebSocketDisconnect:
        pass
    finally:
        # Save session on disconnect
        session.end()
        try:
            repo.save_session(session)
        except Exception:
            pass


async def _streaming_coach_turn(
    websocket: WebSocket,
    client: anthropic.Anthropic,
    messages: list[dict],
    system_prompt: str,
    dispatcher: ToolDispatcher,
    model: str,
    max_tokens: int,
) -> str:
    """Execute a coaching turn with streaming over WebSocket.

    Returns the final accumulated text response.
    """
    accumulated_text = ""

    while True:
        # Use streaming to forward chunks to the WebSocket
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            tools=STOCKFISH_TOOLS,
            messages=messages,
        ) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        chunk = event.delta.text
                        accumulated_text += chunk
                        await websocket.send_json(
                            WSOutgoing(type="chunk", content=chunk).model_dump()
                        )

        response = stream.get_final_message()
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # No tool calls — we're done
            return accumulated_text

        # Handle tool calls
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in tool_use_blocks:
            result = dispatcher.dispatch(block.name, block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

            # Notify client about eval updates when we evaluate positions
            if block.name == "evaluate_position":
                try:
                    eval_data = json.loads(result)
                    if "error" not in eval_data:
                        await websocket.send_json(
                            WSOutgoing(
                                type="eval_update",
                                eval=eval_data,
                            ).model_dump()
                        )
                except json.JSONDecodeError:
                    pass

        messages.append({"role": "user", "content": tool_results})
        accumulated_text = ""  # Reset for next round of text
