"""Live event queue + step tracing shared by the boss and the specialists.

Every step of every agent loop goes onto one asyncio.Queue:
- step_started / step_done — one pair per model call, book search, or delegation,
  with input, output, start time, duration, and token counts
- boss_thinking, specialist_started, specialist_done, final, error — the
  higher-level events the dashboard uses for wands, edges, and sounds

The /api/chat/stream route drains the queue and forwards each event as SSE.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

PREVIEW_CHARS = 3000  # cap on input/output text per step sent to the browser


def clip(value: Any, limit: int = PREVIEW_CHARS) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + f"… [{len(text) - limit} more chars]"


@dataclass
class Tracer:
    queue: asyncio.Queue
    started_at: float = field(default_factory=time.perf_counter)
    steps: list[dict] = field(default_factory=list)
    _ids: itertools.count = field(default_factory=lambda: itertools.count(1))

    def now(self) -> float:
        return round(time.perf_counter() - self.started_at, 3)

    def emit(self, event_type: str, **data: Any) -> None:
        self.queue.put_nowait({"type": event_type, "data": {"t": self.now(), **data}})

    def start_step(self, *, agent_id: str, agent: str, kind: str, label: str, input: Any) -> dict:
        step = {
            "step_id": next(self._ids),
            "agent_id": agent_id,
            "agent": agent,
            "kind": kind,
            "label": label,
            "input": clip(input),
            "started": self.now(),
            "_t0": time.perf_counter(),
        }
        self.emit("step_started", **{k: v for k, v in step.items() if not k.startswith("_")})
        return step

    def end_step(self, step: dict, *, output: Any = "", status: str = "done", **extra: Any) -> None:
        done = {k: v for k, v in step.items() if not k.startswith("_")}
        done.update(
            output=clip(output),
            status=status,
            duration_ms=round((time.perf_counter() - step["_t0"]) * 1000),
            **extra,
        )
        self.steps.append(done)
        self.emit("step_done", **done)

    @asynccontextmanager
    async def step(self, *, agent_id: str, agent: str, kind: str, label: str, input: Any) -> AsyncIterator[dict]:
        """Time a block of work. Set result['output'] (and any extras) inside the block."""
        step = self.start_step(agent_id=agent_id, agent=agent, kind=kind, label=label, input=input)
        result: dict = {"output": ""}
        try:
            yield result
        except asyncio.CancelledError:
            self.end_step(step, output="cancelled", status="error")
            raise
        except Exception as exc:
            self.end_step(step, output=f"{type(exc).__name__}: {exc}", status="error")
            raise
        else:
            self.end_step(step, **result)


def _describe_request(parts: list) -> str:
    lines = []
    for part in parts:
        if isinstance(part, UserPromptPart):
            lines.append(f"USER: {part.content}")
        elif isinstance(part, ToolReturnPart):
            lines.append(f"TOOL RESULT {part.tool_name}: {clip(part.content, 600)}")
        elif isinstance(part, RetryPromptPart):
            lines.append(f"RETRY: {clip(part.content, 600)}")
    return "\n\n".join(lines) or "(continue)"


def _describe_response(parts: list) -> str:
    lines = []
    for part in parts:
        if isinstance(part, TextPart) and part.content.strip():
            lines.append(part.content)
        elif isinstance(part, ToolCallPart):
            lines.append(f"CALL {part.tool_name}({clip(part.args_as_dict(), 400)})")
    return "\n\n".join(lines) or "(no text)"


async def run_traced(
    agent: Agent,
    prompt: str,
    *,
    tracer: Tracer,
    agent_id: str,
    agent_name: str,
    **run_kwargs: Any,
):
    """Run an agent node by node, emitting a timed 'llm' step for every model call.

    Tool calls are traced by the tools themselves, so this only needs to time
    the gap between a ModelRequestNode and the CallToolsNode that follows it.
    """
    open_step: dict | None = None
    call_number = 0
    try:
        async with agent.iter(prompt, **run_kwargs) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    call_number += 1
                    open_step = tracer.start_step(
                        agent_id=agent_id,
                        agent=agent_name,
                        kind="llm",
                        label=f"model call {call_number}",
                        input=_describe_request(node.request.parts),
                    )
                elif Agent.is_call_tools_node(node) and open_step is not None:
                    response = node.model_response
                    usage = response.usage
                    tracer.end_step(
                        open_step,
                        output=_describe_response(response.parts),
                        input_tokens=usage.input_tokens,
                        output_tokens=usage.output_tokens,
                        model=response.model_name,
                    )
                    open_step = None
        return run.result
    except BaseException as exc:
        if open_step is not None:
            tracer.end_step(open_step, output=f"{type(exc).__name__}: {exc}", status="error")
        raise
