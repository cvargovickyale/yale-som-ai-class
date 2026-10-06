"""Turn every PydanticAI agent-loop node into a queue event.

run_traced() drives agent.iter() node by node and emits an `agent_step` event
for each one, so the dashboard sees the whole loop: prompt in, model request,
model response (text + tool calls + tokens + dollars), tool results, end.

With a SpendTracker it also records each model response's cost under the
agent's key, emits a `spend` event, and stops the run once the budget is hit.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from pydantic_ai import Agent
from pydantic_ai.messages import (
    CachePoint,
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)

from agents.pricing import SpendTracker, cost_usd

Emit = Callable[..., None]


def clip(value: Any, limit: int = 800) -> str:
    if isinstance(value, (list, tuple)):  # a prompt split around a CachePoint
        value = " ⟨cache breakpoint⟩ ".join("" if isinstance(v, CachePoint) else str(v) for v in value)
    text = value if isinstance(value, str) else str(value)
    return text if len(text) <= limit else text[:limit] + f"… (+{len(text) - limit} chars)"


def usage_dict(usage: Any) -> dict:
    return {
        "requests": getattr(usage, "requests", 0),
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        # Responses API prompt-cache counters; both are already inside input_tokens.
        "cache_read_tokens": getattr(usage, "cache_read_tokens", 0) or 0,
        "cache_write_tokens": getattr(usage, "cache_write_tokens", 0) or 0,
        "tool_calls": getattr(usage, "tool_calls", 0) or 0,
    }


def describe_node(node: Any) -> tuple[str, dict] | None:
    if Agent.is_user_prompt_node(node):
        return "user_prompt", {"prompt": clip(node.user_prompt)}

    if Agent.is_model_request_node(node):
        parts = node.request.parts
        returns = [
            {"tool": p.tool_name, "tool_call_id": p.tool_call_id, "content": clip(p.model_response_str(), 500)}
            for p in parts
            if isinstance(p, ToolReturnPart)
        ]
        retries = [clip(p.model_response(), 300) for p in parts if isinstance(p, RetryPromptPart)]
        return "model_request", {
            "parts": [type(p).__name__ for p in parts],
            "tool_returns": returns,
            "retries": retries,
        }

    if Agent.is_call_tools_node(node):
        resp = node.model_response
        text = "".join(p.content for p in resp.parts if isinstance(p, TextPart))
        thinking = "".join(p.content for p in resp.parts if isinstance(p, ThinkingPart))
        calls = [
            {"tool": p.tool_name, "tool_call_id": p.tool_call_id, "args": p.args_as_dict()}
            for p in resp.parts
            if isinstance(p, ToolCallPart)
        ]
        return "model_response", {
            "model": resp.model_name,
            "text": clip(text),
            "thinking": clip(thinking, 400) if thinking else "",
            "tool_calls": calls,
            "usage": usage_dict(resp.usage),
            "finish_reason": getattr(resp, "finish_reason", None),
        }

    if Agent.is_end_node(node):
        return "end", {"output": clip(node.data.output)}

    return None


async def run_traced(
    agent: Agent,
    prompt: Any,
    *,
    emit: Emit,
    agent_name: str,
    agent_key: str,
    deps: Any = None,
    model: Any = None,
    model_settings: dict | None = None,
    spend: SpendTracker | None = None,
    **extra: Any,
) -> tuple[Any, dict]:
    """Run an agent, emitting one agent_step per loop node. Returns (output, usage).

    agent_key ("boss", "book-1" … "book-7") is where spend is booked and is
    attached to every event so the dashboard can light the right character.
    """
    started = time.perf_counter()
    request_started: float | None = None
    async with agent.iter(prompt, deps=deps, model=model, model_settings=model_settings) as run:
        step = 0
        async for node in run:
            described = describe_node(node)
            if described is None:
                continue
            step += 1
            kind, data = described
            cost: float | None = None
            if kind == "model_request":
                if spend:
                    spend.check()  # budget already blown by another agent: don't start a new call
                request_started = time.perf_counter()
            elif kind == "model_response":
                if request_started is not None:
                    data["duration_ms"] = round((time.perf_counter() - request_started) * 1000)
                if spend:
                    data["usage"]["cost_usd"] = cost = cost_usd(spend.model, data["usage"])
            emit("agent_step", agent=agent_name, agent_key=agent_key, step=step, kind=kind, **extra, **data)
            if cost is not None and spend:
                spend.add(agent_key, data["usage"])  # emits `spend`; raises BudgetExceeded at the cap
        run_usage = run.usage() if callable(run.usage) else run.usage
        usage = usage_dict(run_usage)
        if spend:
            usage["cost_usd"] = cost_usd(spend.model, usage)
        usage["seconds"] = round(time.perf_counter() - started, 2)
        return run.result.output, usage
