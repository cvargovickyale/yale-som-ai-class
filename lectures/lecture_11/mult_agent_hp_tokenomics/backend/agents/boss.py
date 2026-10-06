"""Boss agent — owns the chat and delegates to book specialists.

Every action lands on one asyncio.Queue through BossDeps.emit():
  boss_thinking      the run starts
  agent_step         one PydanticAI loop node (boss or specialist), or a retrieval
  specialist_started the boss delegated to a book (dashboard edge lights up)
  specialist_done    that book reported back
  spend              running dollar totals per agent (after every model response)
  final / error      last event; data matches ChatResponse (error includes a budget stop)
run_boss_chat_stream() drains the queue for SSE; run_boss_chat() returns the final dict.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import CachePoint

from agents.config import BOSS_NAME, CACHE_SETTINGS, MODEL_NAME, build_model
from agents.events import clip, run_traced
from agents.pricing import BudgetExceeded, SpendTracker
from agents.specialists import agent_key, run_specialist, specialist_name
from models import BOOK_TITLES, Delegation
from retrieval import series_chapter_titles

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "boss.md").read_text(encoding="utf-8")
BOSS_KEY = "boss"
MAX_DELEGATIONS = 12  # guard rail on Portkey spend per question


@dataclass
class BossDeps:
    queue: asyncio.Queue
    delegations: list[dict] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    specialist_usage: list[dict] = field(default_factory=list)
    model_name: str = MODEL_NAME
    spend: SpendTracker | None = None
    started: float = field(default_factory=time.perf_counter)
    seq: int = 0

    def emit(self, event_type: str, **data: Any) -> None:
        self.seq += 1
        data = {
            "seq": self.seq,
            "t_ms": round((time.perf_counter() - self.started) * 1000),
            "ts": time.time(),
            **data,
        }
        event = {"type": event_type, "data": data}
        if event_type not in ("final", "error"):
            self.trace.append(event)
        self.queue.put_nowait(event)


boss_agent = Agent(deps_type=BossDeps, output_type=str, name="boss")


@boss_agent.instructions
def _instructions() -> str:
    # Static prompt + the series chapter map: identical on every call, so it is
    # the boss's cached prefix (long enough to clear OpenAI's ~1,024-token minimum).
    return f"{PROMPT}\n{series_chapter_titles()}"


@boss_agent.tool
async def ask_book_specialist(ctx: RunContext[BossDeps], book_number: int, question: str) -> dict:
    """Delegate a question to the specialist for one Harry Potter book.

    Args:
        book_number: 1 Sorcerer's Stone, 2 Chamber of Secrets, 3 Prisoner of Azkaban,
            4 Goblet of Fire, 5 Order of the Phoenix, 6 Half-Blood Prince, 7 Deathly Hallows.
        question: A specific question for that book, with concrete names/objects/places
            so the specialist's keyword search finds the right passages.
    """
    d = ctx.deps
    if book_number not in BOOK_TITLES:
        return {"status": "error", "reply": "book_number must be between 1 and 7."}
    if len(d.delegations) >= MAX_DELEGATIONS:
        return {"status": "error", "reply": "Delegation limit reached; answer from the reports you have."}

    index = len(d.delegations)
    delegation = Delegation(
        agent=specialist_name(book_number),
        book_number=book_number,
        book_title=BOOK_TITLES[book_number],
        question=question,
        status="running",
    ).model_dump()
    d.delegations.append(delegation)
    d.emit(
        "specialist_started",
        index=index,
        agent_key=agent_key(book_number),
        from_agent=BOSS_NAME,
        tool_call_id=ctx.tool_call_id,
        **{k: delegation[k] for k in ("agent", "book_number", "book_title", "question")},
    )

    try:
        result = await run_specialist(book_number, question, emit=d.emit, model_name=d.model_name, spend=d.spend)
    except BudgetExceeded:
        delegation.update(reply="Stopped: the spending budget was reached.", status="error")
        d.emit(
            "specialist_done",
            index=index,
            question=question,
            to_agent=BOSS_NAME,
            **{k: delegation[k] for k in ("agent", "book_number", "book_title", "reply", "status")},
            agent_key=agent_key(book_number),
        )
        raise

    delegation.update(reply=result["reply"], status=result["status"])
    if result.get("usage"):
        d.specialist_usage.append(result["usage"])
    d.emit("specialist_done", index=index, to_agent=BOSS_NAME, question=question, **result)
    return {k: result.get(k) for k in ("agent", "book_number", "book_title", "status", "passages_used", "reply")}


def _total_usage(boss: dict | None, specialists: list[dict], spend: SpendTracker | None = None) -> dict:
    parts = ([boss] if boss else []) + specialists
    keys = ("requests", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")
    total = {k: sum(p.get(k, 0) for p in parts) for k in keys}
    if spend:  # the tracker saw every model response, including ones from runs cut short
        total = {**{k: spend.total.get(k, 0) for k in keys}, "cost_usd": spend.total["cost_usd"]}
    return {"boss": boss, "specialists": {k: sum(p.get(k, 0) for p in specialists) for k in keys}, "total": total}


async def run_boss_chat_stream(
    message: str, model: str = MODEL_NAME, budget_usd: float | None = None
) -> AsyncIterator[dict]:
    """Yield every queued event as it happens, ending with `final` or `error`."""
    queue: asyncio.Queue = asyncio.Queue()
    deps = BossDeps(queue=queue, model_name=model)
    deps.spend = SpendTracker(model=model, emit=deps.emit, budget_usd=budget_usd)

    def closing(event_type: str, answer: str, boss_usage: dict | None, **extra) -> None:
        for d in deps.delegations:  # anything still running was cut off
            if d["status"] == "running":
                d.update(status="error", reply=d["reply"] or "Stopped before reporting back.")
        deps.emit(
            event_type,
            answer=answer,
            delegations=deps.delegations,
            trace=list(deps.trace),
            boss_name=BOSS_NAME,
            usage=_total_usage(boss_usage, deps.specialist_usage, deps.spend),
            spend=deps.spend.snapshot(),
            budget_exceeded=deps.spend.exceeded,
            **extra,
        )

    async def work() -> None:
        boss_usage = None
        try:
            deps.emit("boss_thinking", agent=BOSS_NAME, agent_key=BOSS_KEY, message=message, model=model, budget_usd=budget_usd)
            prompt = [
                "A visitor to the Headmaster's office asks:",  # fixed text the breakpoint attaches to
                CachePoint(),  # instructions + tools + the line above are the cached prefix
                message,
            ]
            answer, boss_usage = await run_traced(
                boss_agent,
                prompt,
                emit=deps.emit,
                agent_name=BOSS_NAME,
                agent_key=BOSS_KEY,
                deps=deps,
                model=build_model(model),
                model_settings=CACHE_SETTINGS,
                spend=deps.spend,
            )
            closing("final", answer, boss_usage)
        except BudgetExceeded as exc:
            reports = sum(1 for d in deps.delegations if d["status"] == "done")
            closing(
                "error",
                f"**Budget reached.** {exc} The Headmaster stopped his staff before finishing; "
                f"{reports} specialist report(s) had come back and are listed below.",
                boss_usage,
                error=str(exc),
            )
        except Exception as exc:
            closing("error", f"The Headmaster's spell fizzled: {clip(exc, 400)}", boss_usage, error=clip(exc, 1000))
        finally:
            queue.put_nowait(None)

    task = asyncio.create_task(work())
    try:
        while (event := await queue.get()) is not None:
            yield event
    finally:
        if not task.done():  # client hung up mid-run: stop spending tokens
            task.cancel()


async def run_boss_chat(message: str, model: str = MODEL_NAME, budget_usd: float | None = None) -> dict:
    final: dict = {"answer": "No answer produced.", "delegations": [], "boss_name": BOSS_NAME}
    async for event in run_boss_chat_stream(message, model=model, budget_usd=budget_usd):
        if event["type"] in ("final", "error"):
            final = event["data"]
    return final
