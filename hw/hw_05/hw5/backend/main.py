"""Campus Customs multi-agent backend: the five agents, their loops, and delegation.

Agent loop: each agent is a PydanticAI Agent on gpt-6-luna. A run sends the
agent's prompt plus a task to the model; the model either calls a tool (an
MCP tool, or `delegate`) and gets the result back, or returns its final
answer in the shape models.py requires. That repeats until it answers.

Delegation: `delegate(to_agent, ticket_id, task)` is a tool every agent has.
It starts the other agent's loop and returns that agent's report as the
tool result. The guardrails live here in code, not in the prompts:
  - at most MAX_DEPTH hand-offs from the Boss
  - no hand-off to any agent already in the chain (no ping-pong, no loops)
  - stay on the ticket being worked
  - one shared usage budget per ticket (UsageLimits) and a time limit
Every agent loop is recorded (who asked whom, tool calls, tokens, the model
name each response reports) in output/audit_trail.json.

Tools come from the MCP server (mcp_server/server.py, started with --http).
Each agent sees only its own tools.

Run one ticket from the command line (MCP server must be running):
    .venv/bin/python backend/main.py ticket 102
"""

import asyncio
import json
import os
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext, Tool, UsageLimits, capture_run_messages
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import RunUsage

from models import AgentName, AgentRunRecord, BossDecision, SpecialistReport, TicketRun, ToolCallRecord

HW5_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
AUDIT_PATH = Path(os.getenv("AUDIT_PATH", HW5_DIR / "output" / "audit_trail.json"))

# hw5/.env first, then parent folders (the workspace .env) as a fallback.
load_dotenv(HW5_DIR / ".env")
for parent in HW5_DIR.parents:
    if (parent / ".env").exists():
        load_dotenv(parent / ".env")
        break

# The assignment allows only gpt-6-luna, for every agent. Fixed on purpose:
# no environment variable can change it.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
MCP_URL = os.getenv("MCP_URL", f"http://127.0.0.1:{os.getenv('MCP_PORT', '8765')}/mcp")

MAX_DEPTH = 4                      # hand-offs from the Boss (Christopher's choice in P5)
TICKET_TIMEOUT_S = 300             # whole team, one ticket
MODEL_CALL_TIMEOUT_S = 90          # one model request
TOOL_TIMEOUT_S = 60                # one tool call (a delegate call is a whole sub-run, so it is exempt below)
TICKET_LIMITS = UsageLimits(       # shared by every agent working one ticket
    request_limit=40,
    tool_calls_limit=80,
    total_tokens_limit=400_000,
)

# Which MCP tools each agent can see (Christopher's picks in P5). `delegate`
# is added to every agent separately.
AGENT_TOOLS: dict[str, set[str]] = {
    "boss": {"get_ticket", "list_open_tickets", "record_decision"},
    "inventory": {"check_stock", "find_vendor", "reserve_stock", "request_reprint"},
    "accounting": {"price_and_margin", "get_cash_and_bills", "propose_payment"},
    "facilities": {"get_lease", "get_ticket"},
    "customer_service": {"get_ticket", "save_draft_message"},
}
OUTPUT_TYPES = {"boss": BossDecision}  # everyone else returns SpecialistReport


@dataclass
class Deps:
    """Per-agent-run context. The chain and records travel down through delegation."""

    ticket_id: int
    chain: list[str]
    run_id: str
    parent_run_id: str | None
    mcp: MCPToolset
    records: list[AgentRunRecord] = field(default_factory=list)

    @property
    def agent(self) -> str:
        return self.chain[-1]

    @property
    def depth(self) -> int:
        return len(self.chain) - 1


def _model() -> OpenAIResponsesModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set (see .env.example)")
    # Responses API: gpt-6-luna rejects function tools on Chat Completions
    # unless reasoning is turned off (Portkey/Azure error, found in P5).
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=api_key))


def _dynamic_context(ctx: RunContext[Deps]) -> str:
    d = ctx.deps
    path = " → ".join(d.chain)
    return (
        f"You are working ticket {d.ticket_id}. Hand-off chain so far: {path} "
        f"(depth {d.depth} of {MAX_DEPTH}). Agents already in the chain can't be delegated to."
    )


async def delegate(ctx: RunContext[Deps], to_agent: AgentName, ticket_id: int, task: str) -> dict:
    """Hand a specific task to a teammate and get their report back.

    to_agent: boss, inventory, accounting, facilities, or customer_service.
    ticket_id: the ticket being worked.
    task: exactly what you need from them, with the facts they need (SKU, size,
    quantity, invoice or lease ID, amounts).
    """
    d = ctx.deps
    if ticket_id != d.ticket_id:
        return {"refused": f"Stay on ticket {d.ticket_id}. Delegation for ticket {ticket_id} is not allowed in this run."}
    if to_agent == d.agent:
        return {"refused": "You can't delegate to yourself."}
    if to_agent in d.chain:
        return {"refused": f"{to_agent} is already in the chain ({' → '.join(d.chain)}). No ping-pong: "
                           "put what you need in questions_for_caller instead."}
    if d.depth >= MAX_DEPTH:
        return {"refused": f"Delegation limit reached ({MAX_DEPTH} hand-offs). Finish with what you have and report back."}
    child = Deps(ticket_id=d.ticket_id, chain=[*d.chain, to_agent], run_id=uuid.uuid4().hex[:12],
                 parent_run_id=d.run_id, mcp=d.mcp, records=d.records)
    report = await run_agent(to_agent, task, child, usage=ctx.usage)
    return report.model_dump()


def build_agent(name: str) -> tuple[Agent, set[str]]:
    """Built per run so prompt edits apply without restarting anything."""
    prompt = (PROMPTS_DIR / f"{name}.md").read_text()
    allowed = AGENT_TOOLS[name]
    return Agent(
        _model(),
        name=name,
        deps_type=Deps,
        output_type=OUTPUT_TYPES.get(name, SpecialistReport),
        instructions=[prompt, _dynamic_context],
        toolsets=[],  # MCP toolset is passed per run (shared connection)
        tools=[Tool(delegate, timeout=TICKET_TIMEOUT_S)],  # a hand-off is a whole sub-run
        retries=2,
        # One tool call at a time (parallel hand-offs made two agents do the
        # same work in P5), and no single model call or tool call can hang
        # the whole ticket.
        model_settings={"parallel_tool_calls": False, "timeout": MODEL_CALL_TIMEOUT_S},
        tool_timeout=TOOL_TIMEOUT_S,
    ), allowed


def _short(value, limit: int = 600) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + f"… ({len(text)} chars)"


def _record(name: str, task: str, deps: Deps, started: str, t0: float, messages: list, status: str,
            output=None, error: str | None = None) -> AgentRunRecord:
    calls: dict[str, ToolCallRecord] = {}
    models, requests, tin, tout = [], 0, 0, 0
    for m in messages:
        if isinstance(m, ModelResponse):
            requests += 1
            models.append(m.model_name or "unknown")
            tin += m.usage.input_tokens or 0
            tout += m.usage.output_tokens or 0
            for p in m.parts:
                if isinstance(p, ToolCallPart) and p.tool_name != "final_result":
                    calls[p.tool_call_id] = ToolCallRecord(tool=p.tool_name, args=p.args_as_dict(), result="", status="ok")
        else:
            for p in getattr(m, "parts", []):
                if isinstance(p, ToolReturnPart) and p.tool_call_id in calls:
                    c = calls[p.tool_call_id]
                    c.result = _short(p.content)
                    if isinstance(p.content, dict) and "refused" in p.content:
                        c.status = "refused"
                elif isinstance(p, RetryPromptPart) and p.tool_call_id in calls:
                    calls[p.tool_call_id].result = _short(p.content)
                    calls[p.tool_call_id].status = "error"
    if status == "ok" and any(not m.startswith(MODEL_NAME) for m in models):
        status, error = "wrong_model", f"Responses reported models {sorted(set(models))}; only {MODEL_NAME} is allowed."
    return AgentRunRecord(
        run_id=deps.run_id, parent_run_id=deps.parent_run_id, agent=name, chain=list(deps.chain), depth=deps.depth,
        ticket_id=deps.ticket_id, task=task, started_at=started, duration_s=round(time.monotonic() - t0, 2),
        models_reported=models, model_requests=requests, input_tokens=tin, output_tokens=tout,
        tool_calls=list(calls.values()), status=status,
        output=output.model_dump() if output is not None else None, error=error)


async def run_agent(name: str, task: str, deps: Deps, usage: RunUsage):
    """One agent loop. Records itself (even on failure) before returning or raising."""
    agent, allowed = build_agent(name)
    toolset = deps.mcp.filtered(lambda ctx, tool_def, allowed=allowed: tool_def.name in allowed)
    started, t0 = datetime.now(timezone.utc).isoformat(timespec="seconds"), time.monotonic()
    with capture_run_messages() as messages:
        try:
            result = await agent.run(task, deps=deps, usage=usage, usage_limits=TICKET_LIMITS, toolsets=[toolset])
        except UsageLimitExceeded as e:
            _save(deps, _record(name, task, deps, started, t0, messages, "usage_limit", error=str(e)))
            raise
        except asyncio.CancelledError:
            _save(deps, _record(name, task, deps, started, t0, messages, "timeout",
                                error=f"Cancelled when the ticket passed {TICKET_TIMEOUT_S}s."))
            raise
        except Exception as e:
            _save(deps, _record(name, task, deps, started, t0, messages, "error", error=f"{type(e).__name__}: {e}"))
            raise
    rec = _record(name, task, deps, started, t0, result.new_messages(), "ok", output=result.output)
    _save(deps, rec)
    if rec.status == "wrong_model":
        raise RuntimeError(rec.error)
    return result.output


_AUDIT_LOCK = threading.Lock()


def _save(deps: Deps, rec: AgentRunRecord) -> None:
    """Every agent appends its own audit entry the moment its loop ends (ok or not)."""
    deps.records.append(rec)
    _append_audit(rec.model_dump())


def _append_audit(entry: dict) -> None:
    """Append-only; never wiped. Atomic write; an unreadable file is moved aside, never overwritten."""
    with _AUDIT_LOCK:
        _append_audit_locked(entry)


def _append_audit_locked(entry: dict) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if AUDIT_PATH.exists():
        try:
            entries = json.loads(AUDIT_PATH.read_text())
        except json.JSONDecodeError:
            AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f".unreadable-{int(time.time())}.json"))
    entries.append(entry)
    tmp = AUDIT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2) + "\n")
    tmp.replace(AUDIT_PATH)


async def run_ticket(ticket_id: int, task: str | None = None) -> TicketRun:
    """The whole team on one ticket, starting with the Boss."""
    task = task or (f"Work ticket {ticket_id}: read it, get what you need from the team, decide, "
                    f"have Customer Service draft the reply, and record your decision for human approval.")
    mcp = MCPToolset(MCP_URL)
    deps = Deps(ticket_id=ticket_id, chain=["boss"], run_id=uuid.uuid4().hex[:12], parent_run_id=None, mcp=mcp)
    usage = RunUsage()
    started, t0 = datetime.now(timezone.utc).isoformat(timespec="seconds"), time.monotonic()
    decision, status, error = None, "ok", None
    try:
        async with mcp:
            decision = await asyncio.wait_for(run_agent("boss", task, deps, usage), TICKET_TIMEOUT_S)
    except UsageLimitExceeded as e:
        status, error = "usage_limit", str(e)
    except (asyncio.TimeoutError, TimeoutError):
        status, error = "timeout", f"Ticket run passed {TICKET_TIMEOUT_S}s."
    except Exception as e:
        status = "wrong_model" if any(r.status == "wrong_model" for r in deps.records) else "error"
        error = f"{type(e).__name__}: {e}"
    runs = sorted(deps.records, key=lambda r: r.started_at)
    calls = [c for r in runs for c in r.tool_calls]
    entry = TicketRun(
        ticket_id=ticket_id, started_at=started, duration_s=round(time.monotonic() - t0, 2), status=status,
        decision=decision, run_ids=[r.run_id for r in runs], runs=runs, error=error,
        totals={
            "agent_runs": len(runs),
            "model_requests": sum(r.model_requests for r in runs),
            "input_tokens": sum(r.input_tokens for r in runs),
            "output_tokens": sum(r.output_tokens for r in runs),
            "tool_calls": len(calls),
            "delegations": sum(c.tool == "delegate" and c.status == "ok" for c in calls),
            "refused_delegations": sum(c.tool == "delegate" and c.status == "refused" for c in calls),
        })
    # The ticket summary points at the agent entries already appended, by run_id.
    _append_audit(entry.model_dump(exclude={"runs"}))
    t = entry.totals
    print(f"[cost] ticket {ticket_id} {status}: {t['agent_runs']} agent runs, {t['model_requests']} model requests, "
          f"{t['input_tokens']}+{t['output_tokens']} tokens, {t['tool_calls']} tool calls, "
          f"{t['delegations']} delegations ({t['refused_delegations']} refused), {entry.duration_s}s", file=sys.stderr)
    return entry


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "ticket":
        result = asyncio.run(run_ticket(int(sys.argv[2])))
        print(json.dumps(result.model_dump(), indent=2))
    else:
        print(__doc__)
