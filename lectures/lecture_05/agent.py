"""Screen-aware PydanticAI agent for the immersive browser UI."""

from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import BinaryContent, ToolReturn
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from audit_log import append_event
from screen_tools import capture_screen


PROJECT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = PROJECT_DIR.parent.parent
load_dotenv(WORKSPACE_DIR / ".env")

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
PROMPT_PATH = PROJECT_DIR / "prompts" / "prompt.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

_history: list[Any] = []
_history_lock = threading.Lock()


class AgentDeps:
    def __init__(self) -> None:
        self.tool_events: list[dict[str, str]] = []
        self.last_shot: dict[str, str] | None = None


def _build_agent() -> Agent[None, str]:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing from the workspace .env")
    provider = OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=api_key)
    model = OpenAIResponsesModel(MODEL_NAME, provider=provider)
    return Agent(
        model,
        deps_type=AgentDeps,
        output_type=str,
        instructions=SYSTEM_PROMPT,
        retries=1,
    )


agent = _build_agent()


@agent.tool
def look_at_screen(ctx: RunContext[AgentDeps], region: str = "window") -> ToolReturn[Any]:
    """Capture the current immersive browser screen and inspect its visible content."""

    shot = capture_screen(region=region if region in {"window", "full"} else "window")
    metadata = {
        "captured_at": shot.captured_at,
        "region": shot.region,
        "width": shot.width,
        "height": shot.height,
    }
    ctx.deps.tool_events.append({"name": "Look at screen"})
    ctx.deps.last_shot = {"captured_at": shot.captured_at, "region": shot.region}
    return ToolReturn(
        return_value=metadata,
        content=[
            BinaryContent(
                data=shot.png,
                media_type="image/png",
                identifier=f"screen-{shot.captured_at}",
                vendor_metadata={"detail": "high"},
            )
        ],
    )


def run_agent(user_text: str) -> dict[str, Any]:
    """Run one turn and return the exact shape expected by ``app.py``."""

    global _history
    text = user_text.strip()
    if not text:
        return {"text": "Please enter a message.", "tool_events": [], "last_shot": None}

    with _history_lock:
        deps = AgentDeps()
        try:
            # Capture before every response so each turn sees the browser as it
            # looked when the user sent the message, even if the model decides
            # that no additional tool call is needed.
            current_shot = capture_screen(region="window")
            current_image = BinaryContent(
                data=current_shot.png,
                media_type="image/png",
                identifier=f"screen-{current_shot.captured_at}",
                vendor_metadata={"detail": "high"},
            )
            deps.tool_events.append({"name": "Look at screen"})
            deps.last_shot = {
                "captured_at": current_shot.captured_at,
                "region": current_shot.region,
            }
            result = agent.run_sync(
                [text, current_image],
                deps=deps,
                message_history=_history,
            )
            # Retain recent multimodal context without allowing old full-screen
            # images to make later turns grow without bound.
            _history = result.all_messages()[-12:]
            response_text = result.output
            append_event(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request": text,
                    "tool_events": deps.tool_events,
                    "last_shot": deps.last_shot,
                }
            )
            return {
                "text": response_text,
                "tool_events": deps.tool_events,
                "last_shot": deps.last_shot,
            }
        except Exception:
            # Keep a failed turn from corrupting the usable conversation history.
            raise
