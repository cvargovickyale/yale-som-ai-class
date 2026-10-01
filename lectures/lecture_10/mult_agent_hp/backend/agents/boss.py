"""Boss agent (Dumbledore) — owns the chat and delegates to book specialists.

- PydanticAI Agent with async tool ask_book_specialist(book_number, question)
- BossDeps holds the Tracer (asyncio.Queue) + delegations list; emit() pushes events
- run_boss_chat_stream(message) and run_boss_chat(message)
- High-level events: boss_thinking, specialist_started, specialist_done, final, error
- Step events: step_started / step_done for every model call, search, and delegation

main.py imports run_boss_chat and run_boss_chat_stream from here.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits

from agents.config import BOSS_NAME, build_model
from agents.specialists import CHARACTERS, run_specialist, specialist_name
from agents.tracing import Tracer, run_traced
from models import BOSS
from retrieval import get_book_meta

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "boss.md"
BOSS_ID = BOSS["agent_id"]
MAX_BOSS_MODEL_CALLS = 12

_DONE = object()  # sentinel: tells the stream reader the run is over


@dataclass
class BossDeps:
    """Per-request state the boss's tools can reach through ctx.deps."""

    tracer: Tracer
    delegations: list[dict] = field(default_factory=list)

    def emit(self, event_type: str, **data: Any) -> None:
        self.tracer.emit(event_type, **data)


async def ask_book_specialist(ctx: RunContext[BossDeps], book_number: int, question: str) -> dict:
    """Ask the specialist for one Harry Potter book a focused question.

    Args:
        book_number: Which novel to consult, 1 (Sorcerer's Stone) through 7 (Deathly Hallows).
        question: A self-contained question about events in that one book.
    """
    deps = ctx.deps
    if book_number not in CHARACTERS:
        return {"book_number": book_number, "status": "error", "reply": "Invalid book_number: use 1 through 7."}

    character = CHARACTERS[book_number]
    meta = get_book_meta(book_number) or {}
    index = len(deps.delegations)
    deps.delegations.append(
        {
            "agent": specialist_name(book_number),
            "book_number": book_number,
            "book_title": meta.get("title", f"Book {book_number}"),
            "question": question,
            "reply": "",
            "status": "running",
        }
    )
    deps.emit("specialist_started", index=index, agent_id=character["agent_id"], **deps.delegations[index])

    async with deps.tracer.step(
        agent_id=BOSS_ID,
        agent=BOSS_NAME,
        kind="delegate",
        label=f"ask {character['character']}",
        input=question,
    ) as step:
        result = await run_specialist(book_number, question, deps.tracer)
        step["output"] = result["reply"]
        step["status"] = result["status"]
        step["passages"] = result["passages_used"]

    deps.delegations[index].update(reply=result["reply"], status=result["status"])
    deps.emit(
        "specialist_done",
        index=index,
        agent_id=character["agent_id"],
        passages_used=result["passages_used"],
        **deps.delegations[index],
    )
    return {k: result[k] for k in ("agent", "book_number", "book_title", "reply", "status", "passages_used")}


@cache
def _boss_agent() -> Agent[BossDeps, str]:
    return Agent(
        build_model(),
        deps_type=BossDeps,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        tools=[ask_book_specialist],
        name="boss",
    )


async def _run(message: str, deps: BossDeps) -> None:
    """Run the boss to completion, then emit final (or error) and the sentinel."""
    try:
        result = await run_traced(
            _boss_agent(),
            message,
            tracer=deps.tracer,
            agent_id=BOSS_ID,
            agent_name=BOSS_NAME,
            deps=deps,
            usage_limits=UsageLimits(request_limit=MAX_BOSS_MODEL_CALLS),
        )
        deps.emit(
            "final",
            answer=result.output,
            delegations=deps.delegations,
            boss_name=BOSS_NAME,
            trace=deps.tracer.steps,
        )
    except Exception as exc:
        deps.emit(
            "error",
            answer=f"{BOSS_NAME} ran into a problem: {exc}",
            delegations=deps.delegations,
            boss_name=BOSS_NAME,
            trace=deps.tracer.steps,
        )
    finally:
        deps.tracer.queue.put_nowait(_DONE)


async def run_boss_chat_stream(message: str) -> AsyncIterator[dict]:
    """Yield every queued event as it happens while the boss works in a background task."""
    deps = BossDeps(tracer=Tracer(queue=asyncio.Queue()))
    deps.emit("boss_thinking", agent_id=BOSS_ID, boss_name=BOSS_NAME, message=message)
    task = asyncio.create_task(_run(message, deps))
    try:
        while True:
            event = await deps.tracer.queue.get()
            if event is _DONE:
                break
            yield event
    finally:
        # If the browser disconnects mid-run, stop paying for model calls.
        if not task.done():
            task.cancel()


async def run_boss_chat(message: str) -> dict:
    """Non-streaming version: drain the stream and return the last final/error payload."""
    outcome: dict = {"answer": "No answer produced.", "delegations": [], "boss_name": BOSS_NAME}
    async for event in run_boss_chat_stream(message):
        if event["type"] in ("final", "error"):
            outcome = {k: v for k, v in event["data"].items() if k != "t"}
    return outcome
