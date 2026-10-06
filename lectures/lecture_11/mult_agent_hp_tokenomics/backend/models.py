"""Shared API / agent result models.

- BOOK_CATALOG — roster metadata for books 1–7 (title, specialty, accent, …)
- ChatRequest, ChatResponse, Delegation — shapes used by FastAPI + the front end
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# One character per book, matched to where each matters most: Ron's chess game (1),
# Hermione solving the basilisk (2), Lupin's year teaching (3), the twins' Triwizard
# betting (4), Luna's debut (5), Snape as the Prince (6), Neville's stand (7).
# agent_key is also the key spend is booked under ("boss", "book-1" … "book-7").
BOOK_CATALOG: list[dict] = [
    {
        "book_number": 1,
        "agent_key": "book-1",
        "character": "Ron Weasley",
        "emoji": "♟️",
        "wand": "#6b4a2f",
        "persona": "casual, loyal, and funny; plain words, the odd 'bloody hell', and honest when he isn't sure",
        "title": "Harry Potter and the Sorcerer's Stone",
        "short": "Sorcerer's Stone",
        "specialty": "Harry's first year: Hagrid, Diagon Alley, the Mirror of Erised, Quirrell and the Stone.",
        "accent": "#d9792b",
        "house_hint": "Gryffindor",
    },
    {
        "book_number": 2,
        "agent_key": "book-2",
        "character": "Hermione Granger",
        "emoji": "📚",
        "wand": "#8a5a3b",
        "persona": "brisk, precise, and a little impatient; cites passages carefully and corrects sloppy questions",
        "title": "Harry Potter and the Chamber of Secrets",
        "short": "Chamber of Secrets",
        "specialty": "Dobby, the basilisk, Tom Riddle's diary, and the Heir of Slytherin.",
        "accent": "#b3262d",
        "house_hint": "Slytherin",
    },
    {
        "book_number": 3,
        "agent_key": "book-3",
        "character": "Remus Lupin",
        "emoji": "🐺",
        "wand": "#9c7b56",
        "persona": "kind, tired, and thoughtful, like a patient teacher; offers chocolate when the news is grim",
        "title": "Harry Potter and the Prisoner of Azkaban",
        "short": "Prisoner of Azkaban",
        "specialty": "Sirius Black, Lupin, dementors, the Marauder's Map, and the Time-Turner.",
        "accent": "#8a7f6b",
        "house_hint": "Ravenclaw",
    },
    {
        "book_number": 4,
        "agent_key": "book-4",
        "character": "Fred & George Weasley",
        "emoji": "🎆",
        "wand": "#7a4e2a",
        "persona": "two twins sharing one reply, finishing each other's sentences with mischievous jokes, while keeping the facts straight",
        "title": "Harry Potter and the Goblet of Fire",
        "short": "Goblet of Fire",
        "specialty": "The Triwizard Tournament, Barty Crouch Jr., the graveyard, and Voldemort's return.",
        "accent": "#e0562b",
        "house_hint": "Hufflepuff",
    },
    {
        "book_number": 5,
        "agent_key": "book-5",
        "character": "Luna Lovegood",
        "emoji": "🌙",
        "wand": "#c9b28a",
        "persona": "dreamy, serene, and candid; notices odd details and mentions creatures nobody else believes in, but never lets that replace the evidence",
        "title": "Harry Potter and the Order of the Phoenix",
        "short": "Order of the Phoenix",
        "specialty": "Umbridge, Dumbledore's Army, the prophecy, and the Department of Mysteries.",
        "accent": "#4a7fd4",
        "house_hint": "Gryffindor",
    },
    {
        "book_number": 6,
        "agent_key": "book-6",
        "character": "Severus Snape",
        "emoji": "🧪",
        "wand": "#2a2a2a",
        "persona": "cold, clipped, and sardonic, with disdain for obvious questions, yet exact about the text",
        "title": "Harry Potter and the Half-Blood Prince",
        "short": "Half-Blood Prince",
        "specialty": "Pensieve memories of Tom Riddle, Horcruxes, the Prince's book, and the Astronomy Tower.",
        "accent": "#2f5f4f",
        "house_hint": "Slytherin",
    },
    {
        "book_number": 7,
        "agent_key": "book-7",
        "character": "Neville Longbottom",
        "emoji": "🌱",
        "wand": "#a07850",
        "persona": "modest and earnest, a bit nervous at first but steady; fond of plant details",
        "title": "Harry Potter and the Deathly Hallows",
        "short": "Deathly Hallows",
        "specialty": "The Horcrux hunt, the Deathly Hallows, and the Battle of Hogwarts.",
        "accent": "#3f8f4a",
        "house_hint": "Gryffindor",
    },
]

BOOK_TITLES = {b["book_number"]: b["title"] for b in BOOK_CATALOG}
BOOKS = {b["book_number"]: b for b in BOOK_CATALOG}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    model: Literal["gpt-6-luna", "gpt-6-astra"] = "gpt-6-luna"
    budget_usd: float | None = Field(default=None, gt=0, description="Stop the job once spend reaches this; None = no cap")


class Delegation(BaseModel):
    agent: str
    book_number: int
    book_title: str
    question: str
    reply: str = ""
    status: Literal["pending", "running", "done", "error"] = "pending"


class ChatResponse(BaseModel):
    answer: str
    delegations: list[Delegation] = []
    trace: list[dict[str, Any]] | None = None
    boss_name: str
    usage: dict[str, Any] | None = None
    spend: dict[str, Any] | None = None
    budget_exceeded: bool = False
