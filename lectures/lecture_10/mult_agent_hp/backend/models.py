"""Shared API / agent result models.

- BOOK_CATALOG — roster metadata for books 1–7 (title, specialty, accent, …)
- ChatRequest, ChatResponse, Delegation — shapes used by FastAPI + the front end
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# One worker per book, matched to the book where each character matters most:
# Ron's chess game (1), Hermione solving the basilisk (2), Lupin's year teaching (3),
# the twins' Triwizard betting (4), Luna's debut (5), Snape as the Prince (6),
# Neville's stand against Nagini (7). Swap the character fields to reassign.
BOOK_CATALOG: list[dict[str, Any]] = [
    {
        "book_number": 1,
        "agent_id": "book1",
        "character": "Ron Weasley",
        "emoji": "♟️",
        "title": "Harry Potter and the Sorcerer's Stone",
        "short": "Sorcerer's Stone",
        "specialty": "Harry's arrival at Hogwarts, the Mirror of Erised, the Stone",
        "accent": "#d9792b",
        "house_hint": "Gryffindor",
        "wand": "#6b4a2f",
        "persona": "casual, loyal, and funny; plain words, the odd 'bloody hell', and honest when he isn't sure",
    },
    {
        "book_number": 2,
        "agent_id": "book2",
        "character": "Hermione Granger",
        "emoji": "📚",
        "title": "Harry Potter and the Chamber of Secrets",
        "short": "Chamber of Secrets",
        "specialty": "The Chamber, the basilisk, Tom Riddle's diary",
        "accent": "#b3262d",
        "house_hint": "Gryffindor",
        "wand": "#8a5a3b",
        "persona": "brisk, precise, and a little impatient; cites passages carefully and corrects sloppy questions",
    },
    {
        "book_number": 3,
        "agent_id": "book3",
        "character": "Remus Lupin",
        "emoji": "🐺",
        "title": "Harry Potter and the Prisoner of Azkaban",
        "short": "Prisoner of Azkaban",
        "specialty": "Sirius Black, dementors, the Marauders, time travel",
        "accent": "#8a7f6b",
        "house_hint": "Gryffindor",
        "wand": "#9c7b56",
        "persona": "kind, tired, and thoughtful, like a patient teacher; offers chocolate when the news is grim",
    },
    {
        "book_number": 4,
        "agent_id": "book4",
        "character": "Fred & George Weasley",
        "emoji": "🎆",
        "title": "Harry Potter and the Goblet of Fire",
        "short": "Goblet of Fire",
        "specialty": "The Triwizard Tournament and Voldemort's return",
        "accent": "#e0562b",
        "house_hint": "Gryffindor",
        "wand": "#7a4e2a",
        "persona": "two twins sharing one reply, finishing each other's sentences with mischievous jokes, while keeping the facts straight",
    },
    {
        "book_number": 5,
        "agent_id": "book5",
        "character": "Luna Lovegood",
        "emoji": "🌙",
        "title": "Harry Potter and the Order of the Phoenix",
        "short": "Order of the Phoenix",
        "specialty": "Umbridge, Dumbledore's Army, the prophecy, the Ministry",
        "accent": "#4a7fd4",
        "house_hint": "Ravenclaw",
        "wand": "#c9b28a",
        "persona": "dreamy, serene, and candid; notices odd details and mentions creatures nobody else believes in, but never lets that replace the evidence",
    },
    {
        "book_number": 6,
        "agent_id": "book6",
        "character": "Severus Snape",
        "emoji": "🧪",
        "title": "Harry Potter and the Half-Blood Prince",
        "short": "Half-Blood Prince",
        "specialty": "Riddle's past, Horcruxes, the Prince's potions book",
        "accent": "#2f5f4f",
        "house_hint": "Slytherin",
        "wand": "#2a2a2a",
        "persona": "cold, clipped, and sardonic, with long pauses and disdain for obvious questions, yet exact about the text",
    },
    {
        "book_number": 7,
        "agent_id": "book7",
        "character": "Neville Longbottom",
        "emoji": "🌱",
        "title": "Harry Potter and the Deathly Hallows",
        "short": "Deathly Hallows",
        "specialty": "The Horcrux hunt, the Hallows, the Battle of Hogwarts",
        "accent": "#3f8f4a",
        "house_hint": "Gryffindor",
        "wand": "#a07850",
        "persona": "modest and earnest, a bit nervous at first but steady; fond of plant details",
    },
]

BOSS = {
    "agent_id": "boss",
    "character": "Albus Dumbledore",
    "emoji": "🧙‍♂️",
    "accent": "#6b4fbf",
    "wand": "#d8cfb8",
}

DelegationStatus = Literal["pending", "running", "done", "error"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class Delegation(BaseModel):
    agent: str
    book_number: int
    book_title: str
    question: str
    reply: str = ""
    status: DelegationStatus = "pending"


class ChatResponse(BaseModel):
    answer: str
    delegations: list[Delegation] = Field(default_factory=list)
    trace: list[Any] = Field(default_factory=list)
    boss_name: str
