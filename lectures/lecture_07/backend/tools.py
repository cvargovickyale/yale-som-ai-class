"""Tools the agent can call. web_search is OpenAI's native tool (wired in
agent.py via pydantic_ai.native_tools.WebSearchTool) — this file only holds
search_courses, the one function tool the agent calls locally."""

from __future__ import annotations

import json
from pathlib import Path

from models import Course

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_PATH = ROOT / "data" / "yale_som_classes.json"

_SEARCH_FIELDS = (
    "Course Number",
    "Course Title",
    "Faculty 1",
    "Course Category",
    "Course Type",
    "Daytimes",
    "Timings Day",
)

_courses_cache: list[dict] | None = None


def _load_courses() -> list[dict]:
    global _courses_cache
    if _courses_cache is None:
        _courses_cache = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return _courses_cache


def search_courses(query: str, limit: int = 15) -> list[Course]:
    """Search the Yale SOM course catalog (data/yale_som_classes.json).

    Matches rows where `query` appears, case-insensitively, in the course
    number, title, faculty name, category, course type, or scheduled
    day/time. Returns at most `limit` matching courses.
    """
    needle = query.strip().lower()
    if not needle:
        return []

    matches: list[Course] = []
    for row in _load_courses():
        haystack = " ".join(str(row.get(field, "")) for field in _SEARCH_FIELDS).lower()
        if needle in haystack:
            matches.append(Course.model_validate(row))
            if len(matches) >= limit:
                break
    return matches
