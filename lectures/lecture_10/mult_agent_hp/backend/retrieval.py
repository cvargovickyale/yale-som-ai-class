"""Helpers to pull text chunks from harrypotter.db.

- list_books(), get_book_meta(book_number)
- retrieve_chunks(book_number, question) — keyword-scored chunks; cap evidence size
- format_evidence(chunks) — join chunks for the specialist prompt

Never load an entire novel into a model prompt.
"""

from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "harrypotter.db"

CHUNK_WORDS = 220  # words per chunk
CHUNK_STRIDE = 170  # step between chunk starts (50-word overlap)
DEFAULT_TOP_K = 30
MAX_EVIDENCE_CHARS = 40000

STOPWORDS = frozenset(
    """a about after again all also an and any are as at be because been before
    being but by can could did do does doing during each few for from had has
    have having he her here hers him his how i if in into is it its just me
    more most my no nor not of off on once only or other our out over own
    same she should so some such than that the their them then there these
    they this those through to too under until up very was we were what when
    where which while who whom why will with would you your book books happen
    happens happened tell describe explain identify report find check
    detail details include including specific exactly actual immediate
    circumstance circumstances keyword keywords passage passages chapter
    question answer evidence""".split()
)

WORD_RE = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?")


@dataclass(frozen=True)
class Chunk:
    book_number: int
    index: int
    text: str
    terms: Counter


def _connect() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _stem(word: str) -> str:
    """Crude, consistent normalizer so 'Horcruxes' matches 'Horcrux'."""
    word = re.sub(r"['’]s$", "", word)
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    if len(word) > 3 and word.endswith("e"):
        word = word[:-1]
    return word


def _terms(text: str) -> list[str]:
    return [_stem(w) for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS]


def list_books() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT book_number, title, page_count, token_count FROM books ORDER BY book_number"
        ).fetchall()
    return [dict(r) for r in rows]


def get_book_meta(book_number: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT book_number, title, page_count, token_count FROM books WHERE book_number = ?",
            (book_number,),
        ).fetchone()
    return dict(row) if row else None


@lru_cache(maxsize=7)
def _book_index(book_number: int) -> tuple[list[Chunk], dict[str, int]]:
    """Split one book into overlapping word windows and count document frequency."""
    with _connect() as conn:
        row = conn.execute("SELECT text FROM books WHERE book_number = ?", (book_number,)).fetchone()
    if row is None:
        raise ValueError(f"No book {book_number} in database")

    # The source text is hard-wrapped PDF output; collapse it to single spaces.
    words = row["text"].split()
    chunks: list[Chunk] = []
    for i, start in enumerate(range(0, max(len(words) - CHUNK_WORDS // 2, 1), CHUNK_STRIDE)):
        text = " ".join(words[start : start + CHUNK_WORDS])
        chunks.append(Chunk(book_number, i, text, Counter(_terms(text))))

    doc_freq: Counter = Counter()
    for chunk in chunks:
        doc_freq.update(chunk.terms.keys())
    return chunks, dict(doc_freq)


def retrieve_chunks(
    book_number: int,
    question: str,
    top_k: int = DEFAULT_TOP_K,
    max_chars: int = MAX_EVIDENCE_CHARS,
    exclude: set[int] | None = None,
) -> list[dict]:
    """Return the best-matching chunks for a question, capped at max_chars total.

    exclude: chunk indices already shown to the caller, so follow-up searches
    surface new passages instead of repeating old ones.
    """
    exclude = exclude or set()
    chunks, doc_freq = _book_index(book_number)
    query = set(_terms(question))
    if not query:
        return []

    n = len(chunks)
    idf = {t: math.log((n + 1) / (doc_freq.get(t, 0) + 1)) + 1 for t in query if t in doc_freq}
    if not idf:
        return []

    scored = []
    for chunk in chunks:
        if chunk.index in exclude:
            continue
        matched = [t for t in idf if chunk.terms.get(t)]
        if not matched:
            continue
        # Sublinear term frequency, weighted by rarity; reward covering more query terms.
        score = sum((1 + math.log(chunk.terms[t])) * idf[t] for t in matched)
        score *= 1 + len(matched) / len(idf)
        scored.append((score, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    picked: list[dict] = []
    used_chars = 0
    for score, chunk in scored:
        # Skip a chunk that overlaps one we already took.
        if any(abs(chunk.index - p["chunk_index"]) <= 1 for p in picked):
            continue
        if used_chars + len(chunk.text) > max_chars and picked:
            break
        picked.append(
            {
                "book_number": book_number,
                "chunk_index": chunk.index,
                "score": round(score, 2),
                "text": chunk.text,
            }
        )
        used_chars += len(chunk.text)
        if len(picked) >= top_k:
            break

    # Present in story order so the specialist reads events chronologically.
    picked.sort(key=lambda p: p["chunk_index"])
    return picked


def format_evidence(chunks: list[dict], start: int = 1) -> str:
    if not chunks:
        return "(no matching passages found)"
    total = len(_book_index(chunks[0]["book_number"])[0])
    parts = []
    for i, c in enumerate(chunks, start=start):
        position = round(100 * c["chunk_index"] / max(total - 1, 1))
        parts.append(f"[Passage {i} — about {position}% through the book]\n{c['text']}")
    return "\n\n".join(parts)
