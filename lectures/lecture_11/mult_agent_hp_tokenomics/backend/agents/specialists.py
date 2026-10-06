"""Book specialist workers — one focused answer path per novel (1–7).

run_specialist() pulls the best-matching chunks for its book and lets the agent
do at most one follow-up search_book() call before answering. Every step goes
out through `emit`.

Prompt caching: the instructions (rules + persona + the book's chapter map) are
identical for every question to the same book, so they form a stable prefix.
The user message puts a short fixed header first, then a CachePoint, then the
per-question EVIDENCE and QUESTION, so only the stable part is cached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import CachePoint

from agents.config import CACHE_SETTINGS, MODEL_NAME, build_model
from agents.events import Emit, clip, run_traced
from agents.pricing import BudgetExceeded, SpendTracker
from models import BOOK_TITLES, BOOKS
from retrieval import Chunk, chapter_guide, format_evidence, retrieve_chunks

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "specialist.md").read_text(encoding="utf-8")
FOLLOW_UP_SEARCHES = 1
FOLLOW_UP_CHARS = 5000
FOLLOW_UP_CHUNKS = 4


def specialist_name(book_number: int) -> str:
    return BOOKS[book_number]["character"] if book_number in BOOKS else f"Book {book_number}"


def agent_key(book_number: int) -> str:
    return f"book-{book_number}"


def _noop(*_args, **_kwargs) -> None:
    pass


@dataclass
class SpecialistDeps:
    book_number: int
    book_title: str
    emit: Emit
    chunks: list[Chunk] = field(default_factory=list)
    searches_left: int = FOLLOW_UP_SEARCHES


specialist_agent = Agent(deps_type=SpecialistDeps, output_type=str, name="book_specialist")


@lru_cache(maxsize=7)
def stable_instructions(book_number: int) -> str:
    """Byte-identical for every question to this book, so OpenAI can cache it."""
    book = BOOKS[book_number]
    return (
        PROMPT.replace("{character}", book["character"])
        .replace("{persona}", book["persona"])
        .replace("{book_title}", book["title"])
        .replace("{book_number}", str(book_number))
        .replace("{chapter_guide}", chapter_guide(book_number))
    )


@specialist_agent.instructions
def _instructions(ctx: RunContext[SpecialistDeps]) -> str:
    return stable_instructions(ctx.deps.book_number)


@specialist_agent.tool
async def search_book(ctx: RunContext[SpecialistDeps], keywords: str) -> str:
    """Search your book again with different keywords (character names, places, objects, spells).

    Only use this when the EVIDENCE you already have does not answer the question.
    """
    d = ctx.deps
    if d.searches_left <= 0:
        return "No searches left. Answer from the passages you already have."
    d.searches_left -= 1
    seen = {c.chunk_id for c in d.chunks}
    found = retrieve_chunks(
        d.book_number, keywords, max_chars=FOLLOW_UP_CHARS, max_chunks=FOLLOW_UP_CHUNKS, exclude=seen
    )
    start = len(d.chunks) + 1
    d.chunks.extend(found)
    d.emit(
        "agent_step",
        agent=specialist_name(d.book_number),
        agent_key=agent_key(d.book_number),
        book_number=d.book_number,
        kind="retrieval",
        query=keywords,
        follow_up=True,
        chunks=[c.as_dict() for c in found],
        evidence_chars=sum(len(c.text) for c in found),
    )
    if not found:
        return "No new passages matched those keywords."
    return format_evidence(found, start=start)


async def run_specialist(
    book_number: int,
    question: str,
    emit: Emit | None = None,
    *,
    model_name: str = MODEL_NAME,
    spend: SpendTracker | None = None,
) -> dict:
    """Answer `question` from book `book_number`'s retrieved passages only.

    BudgetExceeded is re-raised (not reported as a specialist error) so the
    whole job stops when the spend cap is hit.
    """
    emit = emit or _noop
    name = specialist_name(book_number)
    title = BOOK_TITLES.get(book_number, f"Book {book_number}")
    key = agent_key(book_number)
    base = {"agent": name, "agent_key": key, "book_number": book_number, "book_title": title}
    try:
        chunks = retrieve_chunks(book_number, question)
        emit(
            "agent_step",
            **base,
            kind="retrieval",
            query=question,
            follow_up=False,
            chunks=[c.as_dict() for c in chunks],
            evidence_chars=sum(len(c.text) for c in chunks),
        )
        deps = SpecialistDeps(book_number, title, emit, chunks=chunks)
        prompt = [
            f"Dumbledore has a question for you about {title}.",  # fixed text the breakpoint attaches to
            CachePoint(),  # everything above (instructions + tools + this line) is the cached prefix
            f"QUESTION: {question}\n\nEVIDENCE:\n{format_evidence(chunks)}",
        ]
        reply, usage = await run_traced(
            specialist_agent,
            prompt,
            emit=emit,
            agent_name=name,
            agent_key=key,
            deps=deps,
            model=build_model(model_name),
            model_settings=CACHE_SETTINGS,
            spend=spend,
            book_number=book_number,
        )
        return {
            **base,
            "reply": reply.strip(),
            "status": "done",
            "passages_used": len(deps.chunks),
            "evidence_chars": sum(len(c.text) for c in deps.chunks),
            "chapters": list(dict.fromkeys(c.chapter for c in deps.chunks)),
            "usage": usage,
        }
    except BudgetExceeded:
        raise
    except Exception as exc:  # report the failure to the boss rather than crash the run
        return {
            **base,
            "reply": f"Specialist error: {clip(exc, 300)}",
            "status": "error",
            "passages_used": 0,
            "usage": None,
        }
