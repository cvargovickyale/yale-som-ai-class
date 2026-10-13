"""FastAPI backend: each AI avatar in the building is a PydanticAI agent.

Run from the game folder:
    backend/.venv/bin/python -m uvicorn main:app --app-dir backend --port 8000
"""

import logging
import os
import uuid
from collections import OrderedDict
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv

# backend/.env first, then the game folder and up to three folders above it
# (e.g. the course workspace .env). Earlier files win; real env vars win over all.
BACKEND_DIR = Path(__file__).resolve().parent
for folder in [BACKEND_DIR, *list(BACKEND_DIR.parents)[:4]]:
    load_dotenv(folder / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart

from people import MODEL_NAME, PEOPLE, agent_for, course_title

log = logging.getLogger("uvicorn.error")

MAX_SESSIONS = 200
MAX_MESSAGES = 40

app = FastAPI(title="Yale SOM Virtual: AI avatars")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# (person_id, session_id) -> PydanticAI message history, least recently used first
SESSIONS: OrderedDict[tuple[str, str], list[ModelMessage]] = OrderedDict()


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None


class ChatOut(BaseModel):
    reply: str
    session_id: str


def _starts_user_turn(msg: ModelMessage) -> bool:
    return isinstance(msg, ModelRequest) and any(isinstance(p, UserPromptPart) for p in msg.parts)


def _trim(history: list[ModelMessage]) -> list[ModelMessage]:
    """Keep about the last MAX_MESSAGES, cut only where a user turn starts so tool calls stay paired."""
    if len(history) <= MAX_MESSAGES:
        return history
    for i in range(len(history) - MAX_MESSAGES, len(history)):
        if _starts_user_turn(history[i]):
            return history[i:]
    return []


@app.get("/api/health")
def health():
    return {"ok": True, "model": MODEL_NAME, "people": list(PEOPLE)}


@app.get("/api/people")
def people():
    return [
        {"id": p.id, "name": p.name, "title": p.title, "room": p.room, "course": f"{p.course_number} · {course_title(p.course_number)}"}
        for p in PEOPLE.values()
    ]


@app.post("/api/people/{person_id}/chat", response_model=ChatOut)
async def chat(person_id: str, body: ChatIn):
    if person_id not in PEOPLE:
        raise HTTPException(404, f"No one called {person_id!r} here.")
    session_id = body.session_id or uuid.uuid4().hex
    key = (person_id, session_id)
    history = _trim(SESSIONS.get(key, []))
    try:
        result = await agent_for(person_id).run(body.message, message_history=history)
    except Exception as e:  # model, network, or key problems
        log.exception("chat with %s failed", person_id)
        raise HTTPException(502, f"The avatar couldn't answer right now ({type(e).__name__}).") from e
    SESSIONS[key] = result.all_messages()
    SESSIONS.move_to_end(key)
    while len(SESSIONS) > MAX_SESSIONS:
        SESSIONS.popitem(last=False)
    return ChatOut(reply=result.output, session_id=session_id)
