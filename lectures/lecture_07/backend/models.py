"""Pydantic models shared by the agent, tools, and API layer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Course(BaseModel):
    """One row of data/yale_som_classes.json, typed for the agent's tools."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    course_id: str = Field(alias="Course ID", default="")
    course_number: str = Field(alias="Course Number", default="")
    course_title: str = Field(alias="Course Title", default="")
    course_category: str = Field(alias="Course Category", default="")
    course_type: str = Field(alias="Course Type", default="")
    course_description: str = Field(alias="Course Description", default="")
    faculty: str = Field(alias="Faculty 1", default="")
    faculty_email: str = Field(alias="Faculty 1 Email", default="")
    faculty_bio: str = Field(alias="faculty_bio", default="")
    daytimes: str = Field(alias="Daytimes", default="")
    timings_day: str = Field(alias="Timings Day", default="")
    timings_start: str = Field(alias="Timings StartTime", default="")
    timings_end: str = Field(alias="Timings EndTime", default="")
    room: str = Field(alias="Room", default="")
    units: str = Field(alias="Units", default="")
    section: str = Field(alias="Section", default="")
    bid_or_permission: str = Field(alias="Bid Or Permission", default="")


class AgentResult(BaseModel):
    """What run_agent() returns to main.py."""

    reply: str
    tools_used: list[str] = Field(default_factory=list)
