"""Tools the agent can call. web_search is OpenAI's native tool (wired in
agent.py via pydantic_ai.native_tools.WebSearchTool) — this file only holds
search_courses, which now queries the courses table in data/yale_som.db
instead of the Lecture 07 JSON file."""

from __future__ import annotations

from db import get_connection
from models import Course

_SEARCH_COLUMNS = (
    "course_number",
    "course_title",
    "faculty_1",
    "course_category",
    "course_type",
    "daytimes",
    "timings_day",
)


def search_courses(query: str, limit: int = 15) -> list[Course]:
    """Search the Yale SOM course catalog (data/yale_som.db, courses table).

    Matches rows where `query` appears, case-insensitively, in the course
    number, title, faculty name, category, course type, or scheduled
    day/time. Returns at most `limit` matching courses.
    """
    needle = query.strip()
    if not needle:
        return []

    like = f"%{needle}%"
    where = " OR ".join(f"{col} LIKE ? COLLATE NOCASE" for col in _SEARCH_COLUMNS)
    sql = f"SELECT * FROM courses WHERE {where} LIMIT ?"  # noqa: S608 - columns are a fixed allowlist, not user input
    params = [like] * len(_SEARCH_COLUMNS) + [limit]

    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    return [Course.model_validate(dict(row)) for row in rows]
