"""Read-only access to the Yale SOM course catalog in data/yale_som.db.

Only the public fields below ever leave this module (no faculty emails), and PhD
courses are skipped.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "yale_som.db"

FIELDS = [
    "course_number",
    "course_title",
    "course_category",
    "course_session",
    "course_description",
    "faculty_1",
    "faculty_bio",
    "daytimes",
    "room",
    "section",
    "units",
]
COLS = ", ".join(FIELDS)
NOT_PHD = "COALESCE(course_category, '') != 'PhD'"


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _norm(number: str) -> str:
    """'mgt409', 'MGT 409', ' Mgt  409 ' -> 'MGT409' for comparison."""
    return "".join(number.split()).upper()


def course_sections(number: str) -> list[dict]:
    """Every section of one course, ordered by section."""
    with _connect() as con:
        rows = con.execute(
            f"SELECT {COLS} FROM courses WHERE REPLACE(UPPER(course_number), ' ', '') = ? AND {NOT_PHD} ORDER BY section",
            (_norm(number),),
        ).fetchall()
    return [dict(r) for r in rows]


def search_courses(keyword: str, limit: int = 8) -> list[dict]:
    """Courses whose number, title, description, or instructor matches, one row per course."""
    kw = keyword.strip()
    if not kw:
        return []
    like = f"%{kw}%"
    with _connect() as con:
        rows = con.execute(
            f"""SELECT {COLS} FROM courses
                WHERE {NOT_PHD} AND (
                    course_number LIKE ? OR REPLACE(UPPER(course_number), ' ', '') LIKE ?
                    OR course_title LIKE ? OR course_description LIKE ? OR faculty_1 LIKE ?)
                ORDER BY course_number, section""",
            (like, f"%{_norm(kw)}%", like, like, like),
        ).fetchall()
    out: dict[str, dict] = {}
    for r in rows:
        if r["course_number"] in out:
            continue
        d = {k: r[k] for k in FIELDS if k != "faculty_bio"}
        desc = d["course_description"] or ""
        d["course_description"] = desc[:400] + ("…" if len(desc) > 400 else "")
        out[r["course_number"]] = d
        if len(out) >= limit:
            break
    return list(out.values())


def course_brief(number: str) -> str:
    """Plain-text summary of a course for an agent's instructions."""
    rows = course_sections(number)
    if not rows:
        return f"No catalog entry found for {number}."
    first = rows[0]
    desc = next((r["course_description"] for r in rows if r["course_description"]), "")
    bio = next((r["faculty_bio"] for r in rows if r["faculty_bio"]), "")
    lines = [
        f"{first['course_number']}: {first['course_title']}",
        f"Category: {first['course_category']} · Units: {first['units']}",
        f"Instructor: {first['faculty_1']}",
        "",
        f"Description: {desc}" if desc else "Description: (none in the catalog)",
        "",
        "Sections:",
    ]
    for r in rows:
        when = (r["daytimes"] or "").strip() or "time not listed"
        where = r["room"] or "room not listed"
        lines.append(f"- Section {r['section']} ({r['course_session']}): {when}, {where}, taught by {r['faculty_1']}")
    if bio:
        lines += ["", f"Instructor bio (public catalog): {bio}"]
    return "\n".join(lines)
