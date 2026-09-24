"""Yale SOM course assistant agent: pydantic-ai over search_courses (SQLite)
and OpenAI's native web_search tool, routed through Portkey.

main.py imports run_agent(message) -> {"reply": str, "tools_used": list[str]}.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.capabilities import NativeTool
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.native_tools import WebSearchTool
from pydantic_ai.providers.openai import OpenAIProvider

from tools import search_courses

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Loaded here (not just in main.py) so PORTKEY_API_KEY is in the environment
# by the time this module builds the OpenAI client below. Checks this
# folder, the lecture folder's parent, and the actual workspace root — this
# workspace nests lecture folders one level deeper than a standalone
# project would (see Lecture 07's agent.py for the same fix).
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT.parent.parent / ".env")

MODEL_NAME = "gpt-5.6-luna"
PORTKEY_BASE_URL = os.environ.get("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
PORTKEY_API_KEY = os.environ.get("PORTKEY_API_KEY", "")
PROMPT_PATH = HERE / "prompts" / "prompt.md"
AUDIT_PATH = ROOT / "output" / "audit_trail.json"

_provider = OpenAIProvider(
    base_url=PORTKEY_BASE_URL,
    api_key=PORTKEY_API_KEY,
)
_model = OpenAIResponsesModel(MODEL_NAME, provider=_provider)

agent = Agent(
    _model,
    instructions=PROMPT_PATH.read_text(encoding="utf-8"),
    capabilities=[NativeTool(WebSearchTool())],
    tools=[search_courses],
)


def _tool_name(part: Any) -> str | None:
    return getattr(part, "tool_name", None) or getattr(part, "tool_kind", None)


def _short(value: Any, limit: int = 300) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _inspect_run(result: Any) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    """Walk the message history for tool call/return pairs and intermediate thoughts."""
    tools_used: list[str] = []
    calls_by_id: dict[str, dict[str, Any]] = {}
    call_order: list[str] = []
    thoughts: list[str] = []

    messages = result.all_messages()
    for message in messages:
        for part in message.parts:
            kind = getattr(part, "part_kind", "")
            if kind in ("tool-call", "builtin-tool-call"):
                name = _tool_name(part) or "unknown"
                if name not in tools_used:
                    tools_used.append(name)
                call_id = getattr(part, "tool_call_id", None)
                if call_id:
                    calls_by_id[call_id] = {
                        "tool": name,
                        "args": getattr(part, "args", None),
                        "result": None,
                    }
                    call_order.append(call_id)
            elif kind in ("tool-return", "builtin-tool-return"):
                call_id = getattr(part, "tool_call_id", None)
                if call_id in calls_by_id:
                    calls_by_id[call_id]["result"] = _short(getattr(part, "content", None))
            elif kind == "thinking":
                content = getattr(part, "content", None)
                if content:
                    thoughts.append(_short(content))
            elif kind == "text" and message is not messages[-1]:
                content = getattr(part, "content", None)
                if content:
                    thoughts.append(_short(content))

    tool_calls = [calls_by_id[cid] for cid in call_order]
    return tools_used, tool_calls, thoughts


def _record_audit(
    *,
    message: str,
    thoughts: list[str],
    tool_calls: list[dict[str, Any]],
    stop_reason: str,
) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    if AUDIT_PATH.exists():
        try:
            entries = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            entries = []
    entries.append(
        {
            "time": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "thoughts": thoughts,
            "tool_calls": tool_calls,
            "stop_reason": stop_reason,
        }
    )
    AUDIT_PATH.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")


def run_agent(message: str) -> dict:
    tools_used: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    thoughts: list[str] = []
    stop_reason = "completed"
    try:
        result = agent.run_sync(message)
        reply = result.output
        tools_used, tool_calls, thoughts = _inspect_run(result)
    except Exception as exc:  # noqa: BLE001 - surfaced to the chat UI, not swallowed
        stop_reason = f"error: {exc!r}"
        reply = "Sorry, I hit an error trying to answer that. Please try again."

    _record_audit(message=message, thoughts=thoughts, tool_calls=tool_calls, stop_reason=stop_reason)
    return {"reply": reply, "tools_used": tools_used}
