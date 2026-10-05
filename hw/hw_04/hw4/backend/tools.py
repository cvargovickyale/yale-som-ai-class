"""Tools the Campus Customs agent can call.

Every fact the agent states about products (price, stock, sizes, colors)
must come from a tool here, which reads the database. The model never
answers those from memory (see prompts/prompt.md, "Honesty rules").

P5: the plumbing only (database access through the agent's deps).
P6 adds the product-info and stock tools to TOOLS.
"""

from __future__ import annotations

import sqlite3

from pydantic_ai import RunContext

from models import AgentDeps


def open_db(ctx: RunContext[AgentDeps]) -> sqlite3.Connection:
    """Read-only connection for tools; the agent can never write to the database."""
    conn = sqlite3.connect(f"{ctx.deps.db_path.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# Functions the agent may call. Empty until P6.
TOOLS: list = []
