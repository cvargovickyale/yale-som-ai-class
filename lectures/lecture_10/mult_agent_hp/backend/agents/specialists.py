"""Book specialist workers — one character per novel (1–7).

- run_specialist(book_number, question, tracer)
- Retrieves chunks via retrieval.py up front, then may call search_book for
  follow-up searches; total evidence stays under EVIDENCE_BUDGET_CHARS
- Answers only from that evidence, in character
- Returns agent name, book title, reply, status, passages_used
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits

from agents.config import build_model
from agents.tracing import Tracer, run_traced
from models import BOOK_CATALOG
from retrieval import format_evidence, get_book_meta, retrieve_chunks

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "specialist.md"

EVIDENCE_BUDGET_CHARS = 40_000  # total evidence one specialist may read per question
FIRST_SEARCH_CHARS = 16_000  # retrieved before the model's first call
FOLLOW_UP_SEARCH_CHARS = 8_000  # per search_book call
MAX_MODEL_CALLS = 6

CHARACTERS = {b["book_number"]: b for b in BOOK_CATALOG}


def specialist_name(book_number: int) -> str:
    return CHARACTERS[book_number]["character"]


@dataclass
class SpecialistDeps:
    book_number: int
    agent_id: str
    name: str
    tracer: Tracer
    seen: set[int] = field(default_factory=set)
    passages: int = 0
    chars_used: int = 0

    def search(self, query: str, max_chars: int) -> tuple[str, int]:
        """Retrieve new chunks within the remaining budget; return (evidence, count)."""
        budget = min(max_chars, EVIDENCE_BUDGET_CHARS - self.chars_used)
        if budget <= 1000:
            return "Evidence budget used up. Answer with the passages you already have.", 0
        chunks = retrieve_chunks(self.book_number, query, max_chars=budget, exclude=self.seen)
        evidence = format_evidence(chunks, start=self.passages + 1)
        self.seen.update(c["chunk_index"] for c in chunks)
        self.passages += len(chunks)
        self.chars_used += sum(len(c["text"]) for c in chunks)
        return evidence, len(chunks)


async def search_book(ctx: RunContext[SpecialistDeps], query: str) -> str:
    """Search your book again for passages you have not seen yet.

    Args:
        query: Keywords likely to appear in the text, e.g. "basilisk fang diary ink".
    """
    deps = ctx.deps
    async with deps.tracer.step(
        agent_id=deps.agent_id, agent=deps.name, kind="search", label="search_book", input=query
    ) as step:
        # Keyword scoring is CPU work; keep it off the event loop so other agents keep streaming.
        evidence, count = await asyncio.to_thread(deps.search, query, FOLLOW_UP_SEARCH_CHARS)
        step["output"] = f"{count} new passages · {deps.chars_used:,} chars read so far\n\n{evidence}"
        step["passages"] = count
    return evidence


@cache
def _specialist_agent() -> Agent[SpecialistDeps, str]:
    # One agent definition serves all seven characters; persona, book, and
    # evidence arrive as per-run instructions. Built lazily so the API starts without a key.
    return Agent(
        build_model(),
        deps_type=SpecialistDeps,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        tools=[search_book],
        name="book_specialist",
    )


async def run_specialist(book_number: int, question: str, tracer: Tracer) -> dict:
    meta = get_book_meta(book_number)
    character = CHARACTERS.get(book_number)
    if meta is None or character is None:
        return {
            "agent": f"Book {book_number}",
            "book_number": book_number,
            "book_title": f"Book {book_number}",
            "reply": f"There is no book {book_number} in the library.",
            "status": "error",
            "passages_used": 0,
        }

    title = meta["title"]
    deps = SpecialistDeps(
        book_number=book_number,
        agent_id=character["agent_id"],
        name=character["character"],
        tracer=tracer,
    )

    async with tracer.step(
        agent_id=deps.agent_id, agent=deps.name, kind="search", label="initial retrieval", input=question
    ) as step:
        evidence, count = await asyncio.to_thread(deps.search, question, FIRST_SEARCH_CHARS)
        step["output"] = f"{count} passages · {deps.chars_used:,} chars\n\n{evidence}"
        step["passages"] = count

    run_instructions = (
        f"You are {character['character']}. Personality: {character['persona']}.\n"
        f"Your book: {title} (Book {book_number}).\n\n"
        f"EVIDENCE (passages retrieved from your book):\n{evidence}"
    )
    try:
        result = await run_traced(
            _specialist_agent(),
            f"QUESTION FROM DUMBLEDORE: {question}",
            tracer=tracer,
            agent_id=deps.agent_id,
            agent_name=deps.name,
            deps=deps,
            instructions=run_instructions,
            usage_limits=UsageLimits(request_limit=MAX_MODEL_CALLS),
        )
        reply, status = result.output.strip(), "done"
    except Exception as exc:  # report the failure to the boss instead of crashing the run
        reply, status = f"Specialist error: {exc}", "error"

    return {
        "agent": deps.name,
        "book_number": book_number,
        "book_title": title,
        "reply": reply,
        "status": status,
        "passages_used": deps.passages,
    }
