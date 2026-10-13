"""The AI avatars you can talk to. Each one is a PydanticAI agent.

To add an avatar: write prompts/<id>.md, add a Person to PEOPLE, add an entry to
PEOPLE_INFO in src/talk.js, and put a preset in a classroom (src/Faculty.jsx).
"""

import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

import courses

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-6-luna")


@dataclass(frozen=True)
class Person:
    id: str
    name: str
    title: str
    room: str
    course_number: str
    prompt_file: str


PEOPLE: dict[str, Person] = {
    "zaman": Person(
        id="zaman",
        name="Tauhid Zaman",
        title="Professor",
        room="2200",
        course_number="MGT 409",
        prompt_file="zaman.md",
    ),
}


def course_title(number: str) -> str:
    rows = courses.course_sections(number)
    return rows[0]["course_title"] if rows else ""


def _model() -> OpenAIResponsesModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set (put it in backend/.env)")
    # gpt-6-luna on Portkey only takes function tools through the Responses API.
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=api_key))


def search_courses(keyword: str) -> list[dict]:
    """Search Yale SOM MBA courses by course number, title, description words, or instructor name.

    keyword: e.g. "MGT 409", "negotiation", "Zaman". Returns up to 8 courses.
    """
    return courses.search_courses(keyword)


def course_info(course_number: str) -> list[dict]:
    """Every section of one course: description, instructor, days/times, room, units.

    course_number: e.g. "MGT 409".
    """
    rows = courses.course_sections(course_number)
    return rows or [{"error": f"No course {course_number} in the catalog."}]


@cache
def agent_for(person_id: str) -> Agent:
    p = PEOPLE[person_id]
    persona = (PROMPTS_DIR / p.prompt_file).read_text(encoding="utf-8")
    instructions = f"{persona}\n\n## Course facts (from the Yale SOM catalog)\n\n{courses.course_brief(p.course_number)}"
    return Agent(_model(), instructions=instructions, tools=[search_courses, course_info], name=person_id)
