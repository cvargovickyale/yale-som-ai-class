"""The Campus Customs shopping agent (PydanticAI, routed through Portkey).

How it's assembled:
  1. Load PORTKEY_API_KEY from .env.
  2. Build an OpenAI-compatible model client pointed at Portkey's gateway.
  3. Create the Agent with prompts/prompt.md as its instructions, AgentReply
     as its required output shape, AgentDeps as its per-request context,
     and the functions in tools.TOOLS as its tools.

main.py calls `await run_agent(message, deps)` and gets back an AgentReply.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from models import AgentDeps, AgentReply
from tools import TOOLS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# hw4/.env first. Parent folders are a fallback so a shared workspace .env
# works without copying the key. load_dotenv never overrides a value that's
# already set, so the closest .env wins.
for folder in [ROOT, *ROOT.parents][:4]:
    load_dotenv(folder / ".env")

MODEL_NAME = os.getenv("AGENT_MODEL", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
PROMPT_PATH = HERE / "prompts" / "prompt.md"

# Guardrails on cost and runaway loops for a single chat message.
RUN_LIMITS = UsageLimits(request_limit=6, tool_calls_limit=8)
RUN_TIMEOUT_SECONDS = 45


class AgentUnavailable(RuntimeError):
    """Raised when the agent can't run (e.g. no API key configured)."""


def build_agent() -> Agent[AgentDeps, AgentReply] | None:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        return None  # site still works for browsing; chat reports it's unavailable
    provider = OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=api_key)
    model = OpenAIChatModel(MODEL_NAME, provider=provider)
    built = Agent(
        model,
        output_type=AgentReply,
        deps_type=AgentDeps,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        tools=TOOLS,
        retries=2,
    )

    @built.instructions
    def shopper_context(ctx: RunContext[AgentDeps]) -> str:
        # Added to the prompt on every run. First name only, never email or ID.
        if ctx.deps.first_name:
            return f"The shopper is logged in. Their first name is {ctx.deps.first_name}."
        return "The shopper is not logged in."

    return built


agent = build_agent()


async def run_agent(message: str, deps: AgentDeps) -> AgentReply:
    if agent is None:
        raise AgentUnavailable("PORTKEY_API_KEY is not set (see .env.example)")
    result = await asyncio.wait_for(
        agent.run(message, deps=deps, usage_limits=RUN_LIMITS),
        timeout=RUN_TIMEOUT_SECONDS,
    )
    return result.output
