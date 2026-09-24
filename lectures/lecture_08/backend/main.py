"""Yale SOM course explorer API — Lecture 08.

Same React + FastAPI + PydanticAI shape as Lecture 07, now backed by SQLite
(data/yale_som.db) instead of a JSON file, with email/password auth (JWT
bearer tokens) gating the whole app and per-user chat history.

Supabase + Render are next steps, not today's build (see AI_prompts.md /
lecture notes) — this still targets the local SQLite file.

Run from backend/:  uvicorn main:app --reload --port 8000
Open API docs:      http://127.0.0.1:8000/docs
Frontend (Vite):    http://127.0.0.1:5173
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from agent import run_agent
from auth import create_token, get_current_user, hash_password, verify_password
from db import get_connection, init_db
from models import (
    AuthResponse,
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
    LoginRequest,
    MeResponse,
    SignupRequest,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT.parent.parent / ".env")

init_db()

app = FastAPI(title="Yale SOM Courses (Lecture 08)", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(body: SignupRequest):
    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (body.email,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="An account with that email already exists")
        cur = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (body.email, hash_password(body.password)),
        )
        conn.commit()
        user_id = cur.lastrowid
    finally:
        conn.close()
    return AuthResponse(token=create_token(user_id, body.email), email=body.email)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(body: LoginRequest):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?", (body.email,)
        ).fetchone()
    finally:
        conn.close()
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return AuthResponse(token=create_token(row["id"], row["email"]), email=row["email"])


@app.get("/api/auth/me", response_model=MeResponse)
def me(user: dict = Depends(get_current_user)):
    return MeResponse(email=user["email"])


@app.get("/api/courses")
def list_courses(q: str | None = Query(default=None), user: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        if q:
            like = f"%{q.strip()}%"
            rows = conn.execute(
                """SELECT * FROM courses WHERE
                    course_number LIKE ? COLLATE NOCASE OR
                    course_title LIKE ? COLLATE NOCASE OR
                    faculty_1 LIKE ? COLLATE NOCASE OR
                    course_category LIKE ? COLLATE NOCASE""",
                (like, like, like, like),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM courses").fetchall()
    finally:
        conn.close()
    courses = [dict(r) for r in rows]
    return {"count": len(courses), "courses": courses}


@app.get("/api/chat/history", response_model=list[ChatMessageOut])
def chat_history(user: dict = Depends(get_current_user)):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT role, content, tools_used, created_at FROM chats WHERE user_id = ? ORDER BY id ASC",
            (user["id"],),
        ).fetchall()
    finally:
        conn.close()
    return [
        ChatMessageOut(
            role=row["role"],
            content=row["content"],
            tools_used=json.loads(row["tools_used"]) if row["tools_used"] else [],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest, user: dict = Depends(get_current_user)):
    result = run_agent(body.message)
    _save_message(user["id"], "user", body.message, [])
    _save_message(user["id"], "assistant", result["reply"], result["tools_used"])
    return ChatResponse(reply=result["reply"], tools_used=result["tools_used"])


def _save_message(user_id: int, role: str, content: str, tools_used: list[str]) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO chats (user_id, role, content, tools_used) VALUES (?, ?, ?, ?)",
            (user_id, role, content, json.dumps(tools_used) if tools_used else None),
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
