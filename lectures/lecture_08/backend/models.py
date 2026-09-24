"""Pydantic models shared by the agent, tools, and API layer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Course(BaseModel):
    """One row of the courses table in data/yale_som.db."""

    model_config = ConfigDict(extra="allow")

    id: int | None = None
    course_id: str = ""
    course_number: str = ""
    course_title: str = ""
    course_category: str = ""
    course_type: str = ""
    course_session: str = ""
    course_description: str = ""
    faculty_1: str = ""
    faculty_1_email: str = ""
    faculty_bio: str = ""
    daytimes: str = ""
    timings_day: str = ""
    timings_start: str = ""
    timings_end: str = ""
    room: str = ""
    section: str = ""
    units: str = ""
    term_code: str = ""
    syllabus: str = ""
    old_syllabus: str = ""


class AgentResult(BaseModel):
    """What run_agent() returns to main.py."""

    reply: str
    tools_used: list[str] = Field(default_factory=list)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class AuthResponse(BaseModel):
    token: str
    email: str


class MeResponse(BaseModel):
    email: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[str] = Field(default_factory=list)


class ChatMessageOut(BaseModel):
    role: str
    content: str
    tools_used: list[str] = Field(default_factory=list)
    created_at: str
