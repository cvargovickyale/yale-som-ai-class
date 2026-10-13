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

FastAPI (P7): the dashboard's routes, also in this file. Every shop fact
and every change goes through the MCP server: the backend never opens the
database. Start from backend/:
    ../.venv/bin/uvicorn main:app --reload --port 8000

Run one ticket from the command line (MCP server must be running):
    .venv/bin/python backend/main.py ticket 102
"""

import asyncio
import collections
import json
import os
import sys
import threading
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from openai import AsyncOpenAI
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Client
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, Tool, UsageLimits, capture_run_messages
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError, UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import (FunctionToolCallEvent, FunctionToolResultEvent, ModelResponse, RetryPromptPart,
                                  ToolCallPart, ToolReturnPart)
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


MODEL_RETRIES = 3            # extra tries for one model request on a temporary provider error


def _transient(e: Exception) -> bool:
    """Provider hiccups worth retrying: Azure's intermittent 401 "Jwt verification fails", 429, 5xx, no status."""
    if isinstance(e, ModelHTTPError):
        return e.status_code in (408, 429) or e.status_code >= 500 or (
            e.status_code == 401 and "jwt" in str(e.body).lower())
    return isinstance(e, ModelAPIError)


class RetryingResponsesModel(OpenAIResponsesModel):
    """Retries one model request on a temporary provider error, with backoff.

    Safe: a request has no side effects (tools run only after a reply comes
    back). Each retry is logged as a board event. Found in P8: about one in
    three calls to gpt-6-luna failed with Azure's 401 "Jwt verification
    fails" for a while, which ended whole team runs.
    """

    async def request(self, messages, model_settings, model_request_parameters):
        for attempt in range(MODEL_RETRIES + 1):
            try:
                return await super().request(messages, model_settings, model_request_parameters)
            except Exception as e:
                if attempt == MODEL_RETRIES or not _transient(e):
                    raise
                emit("model_retry", None, None, attempt=attempt + 1, error=_short(str(e), 160))
                await asyncio.sleep(1.5 * 2 ** attempt)

    @asynccontextmanager
    async def request_stream(self, messages, model_settings, model_request_parameters, run_context=None):
        # Runs with the live event hook stream their replies, so they come through here.
        # Retry only while opening the stream; once a reply is flowing, errors pass through.
        for attempt in range(MODEL_RETRIES + 1):
            opened = False
            try:
                async with super().request_stream(messages, model_settings, model_request_parameters, run_context) as stream:
                    opened = True
                    yield stream
                return
            except Exception as e:
                if opened or attempt == MODEL_RETRIES or not _transient(e):
                    raise
                emit("model_retry", None, None, attempt=attempt + 1, error=_short(str(e), 160))
                await asyncio.sleep(1.5 * 2 ** attempt)


def _model() -> OpenAIResponsesModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set (see .env.example)")
    # Responses API: gpt-6-luna rejects function tools on Chat Completions
    # unless reasoning is turned off (Portkey/Azure error, found in P5).
    # Force fresh responses: a Portkey cache hit returns tool-call IDs
    # ("portkey_cache_…") that Azure rejects when they're sent back, which
    # broke the first rerun of an identical request (found in P7).
    client = AsyncOpenAI(base_url=PORTKEY_BASE_URL, api_key=api_key,
                         default_headers={"x-portkey-cache-force-refresh": "true"})
    return RetryingResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


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


# ---------------------------------------------------------------- live events for the board

EVENTS: collections.deque[dict] = collections.deque(maxlen=500)
_event_seq = 0


def emit(kind: str, ticket_id: int | None = None, agent: str | None = None, **detail) -> dict:
    """Record a recent event for the board (in memory; the audit file is the permanent record)."""
    global _event_seq
    _event_seq += 1
    ev = {"seq": _event_seq, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
          "type": kind, "ticket_id": ticket_id, "agent": agent, **detail}
    EVENTS.append(ev)
    return ev


async def _stream_events(ctx: RunContext[Deps], stream) -> None:
    """PydanticAI event hook: one board event per tool call and per tool result, as they happen.

    Display only: an error here is swallowed so the board feed can never stop an agent's work.
    """
    d = ctx.deps
    async for event in stream:
        try:
            if isinstance(event, FunctionToolCallEvent):
                part = event.part
                args = part.args_as_dict()
                if part.tool_name == "delegate":
                    emit("delegation", d.ticket_id, d.agent, to_agent=args.get("to_agent"),
                         task=_short(args.get("task", ""), 200))
                else:
                    emit("tool_call", d.ticket_id, d.agent, tool=part.tool_name, args=_short(args, 200))
            elif isinstance(event, FunctionToolResultEvent):
                part = event.part
                if part.tool_name == "delegate":
                    continue  # the teammate's own agent_finished event covers it
                status = "error" if isinstance(part, RetryPromptPart) else "ok"
                emit("tool_result", d.ticket_id, d.agent, tool=part.tool_name, status=status,
                     result=_short(part.content, 200))
        except Exception as e:
            emit("event_error", d.ticket_id, d.agent, error=f"{type(e).__name__}: {e}")


async def run_agent(name: str, task: str, deps: Deps, usage: RunUsage):
    """One agent loop. Records itself (even on failure) before returning or raising."""
    agent, allowed = build_agent(name)
    toolset = deps.mcp.filtered(lambda ctx, tool_def, allowed=allowed: tool_def.name in allowed)
    started, t0 = datetime.now(timezone.utc).isoformat(timespec="seconds"), time.monotonic()
    emit("agent_started", deps.ticket_id, name, chain=list(deps.chain), task=_short(task, 200))
    with capture_run_messages() as messages:
        try:
            result = await agent.run(task, deps=deps, usage=usage, usage_limits=TICKET_LIMITS, toolsets=[toolset],
                                     event_stream_handler=_stream_events)
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
    emit("agent_finished", rec.ticket_id, rec.agent, status=rec.status, model_requests=rec.model_requests,
         tokens=rec.input_tokens + rec.output_tokens, tool_calls=len(rec.tool_calls),
         recommendation=(rec.output or {}).get("recommendation") or (rec.output or {}).get("summary"))


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


# ---------------------------------------------------------------- FastAPI routes (P7)

app = FastAPI(title="Campus Customs Multi-Agent Operations")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET", "POST"], allow_headers=["*"])

# Token-spend guard for the run route: one team run at a time, and at most
# RUNS_PER_WINDOW runs per RUN_WINDOW_S, checked before any agent starts.
RUNS_PER_WINDOW, RUN_WINDOW_S = 6, 600
RUNS: dict[int, dict] = {}           # ticket_id -> latest run status
_run_starts: collections.deque[float] = collections.deque()
_run_lock = asyncio.Lock()


async def mcp_call(tool: str, **args) -> dict:
    """Every read and write goes through the MCP server. A tool refusal becomes a 409 with its message."""
    try:
        async with Client(MCP_URL) as c:
            r = await c.call_tool(tool, args, raise_on_error=False)
    except Exception as e:
        raise HTTPException(503, f"MCP server not reachable at {MCP_URL}: {type(e).__name__}") from e
    if r.is_error:
        msg = r.content[0].text if r.content else f"{tool} failed"
        raise HTTPException(404 if "not found" in msg else 409, msg)
    data = r.structured_content or {}
    return data.get("result", data)


def _human_audit(action: str, by: str, result: dict) -> None:
    """Human approvals and resets go in the same append-only audit trail as agent runs."""
    _append_audit({"entry_type": "human_action", "action": action, "by": by,
                   "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "result": result})


class Approval(BaseModel):
    approved_by: str = Field(min_length=1, max_length=80, description="Name of the human approving")


class Rejection(BaseModel):
    rejected_by: str = Field(min_length=1, max_length=80)
    reason: str = Field(default="", max_length=500)


class ResetRequest(BaseModel):
    confirm: bool


@app.get("/api/health")
async def health() -> dict:
    board = await mcp_call("get_board")
    return {"ok": True, "model": MODEL_NAME, "mcp": MCP_URL, "date_today": board["date_today"]}


@app.get("/api/tickets")
async def tickets() -> dict:
    """All tickets with status (open/resolved), the team's records for each, and the latest run."""
    board = await mcp_call("get_board")
    for t in board["tickets"]:
        t["run"] = RUNS.get(t["id"])
    return board


@app.get("/api/tickets/{ticket_id}")
async def ticket(ticket_id: int) -> dict:
    data = await mcp_call("get_ticket", ticket_id=ticket_id)
    data["run"] = RUNS.get(ticket_id)
    return data


async def _run_in_background(ticket_id: int) -> None:
    async with _run_lock:
        RUNS[ticket_id] = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        emit("run_started", ticket_id, "boss")
        try:
            result = await run_ticket(ticket_id)
            RUNS[ticket_id] = {"status": result.status, "started_at": result.started_at, "duration_s": result.duration_s,
                               "totals": result.totals, "error": result.error,
                               "decision": result.decision.model_dump() if result.decision else None}
        except Exception as e:  # run_ticket records its own failures; this is a last resort
            RUNS[ticket_id] = {"status": "error", "error": f"{type(e).__name__}: {e}"}
        emit("run_finished", ticket_id, "boss", status=RUNS[ticket_id]["status"],
             totals=RUNS[ticket_id].get("totals"))


@app.get("/api/tickets/{ticket_id}/history")
async def history(ticket_id: int) -> dict:
    """What each agent did on the ticket's latest run since the last reset, from the audit trail (survives restarts).

    Reads output/audit_trail.json only (the run log, not shop data).
    """
    try:
        entries = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []
    except json.JSONDecodeError:
        entries = []
    # Only runs since the last database reset belong to the current board.
    last_reset = max((i for i, e in enumerate(entries)
                      if e.get("entry_type") == "human_action" and e.get("action") == "reset_database"), default=-1)
    entries = entries[last_reset + 1:]
    runs = [e for e in entries if e.get("entry_type") == "ticket_run" and e.get("ticket_id") == ticket_id]
    if not runs:
        return {"ticket_id": ticket_id, "run": None, "agents": []}
    last = runs[-1]
    by_id = {e["run_id"]: e for e in entries if e.get("entry_type") == "agent_run"}
    agents = []
    for rid in last.get("run_ids", []):
        e = by_id.get(rid)
        if not e:
            continue
        out = e.get("output") or {}
        agents.append({
            "run_id": rid, "agent": e["agent"], "chain": e["chain"], "status": e["status"],
            "task": e["task"], "duration_s": e["duration_s"],
            "tokens": e["input_tokens"] + e["output_tokens"], "model_requests": e["model_requests"],
            "tools": [{"tool": c["tool"], "status": c["status"]} for c in e["tool_calls"]],
            "findings": out.get("findings", []), "recommendation": out.get("recommendation") or out.get("summary"),
            "actions_taken": out.get("actions_taken", []), "blocked": out.get("blocked", []),
        })
    summary = {k: last.get(k) for k in ("started_at", "duration_s", "status", "totals", "decision", "error")}
    return {"ticket_id": ticket_id, "run": summary, "agents": agents}


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run(ticket_id: int, background: BackgroundTasks) -> dict:
    """Start the agent team on a ticket. Returns at once; watch /api/events and /api/runs."""
    t = (await mcp_call("get_ticket", ticket_id=ticket_id))["ticket"]
    if t["status"] != "open":
        raise HTTPException(409, f"Ticket {ticket_id} is {t['status']}, not open.")
    if _run_lock.locked() or any(r.get("status") == "running" for r in RUNS.values()):
        raise HTTPException(409, "The team is already working a ticket. One run at a time.")
    now = time.monotonic()
    while _run_starts and now - _run_starts[0] > RUN_WINDOW_S:
        _run_starts.popleft()
    if len(_run_starts) >= RUNS_PER_WINDOW:
        raise HTTPException(429, f"Run limit: {RUNS_PER_WINDOW} runs per {RUN_WINDOW_S // 60} minutes. Try again later.")
    _run_starts.append(now)
    RUNS[ticket_id] = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    background.add_task(_run_in_background, ticket_id)
    return {"ticket_id": ticket_id, "status": "running"}


@app.get("/api/runs")
async def runs() -> dict:
    return {"runs": RUNS}


@app.get("/api/events")
async def events(since: int = 0, limit: int = 100) -> dict:
    """Recent agent events (agent started/finished, tool calls and results, delegations, approvals), oldest first."""
    items = [e for e in EVENTS if e["seq"] > since][-max(1, min(limit, 500)):]
    return {"events": items, "last_seq": _event_seq}


@app.get("/api/cash")
async def cash() -> dict:
    """Checking balance from cash_accounts, plus what's waiting for approval."""
    data = await mcp_call("get_cash_and_bills")
    checking = next((a for a in data["cash_accounts"] if a["name"] == "checking"), None)
    return {"date_today": data["date_today"], "checking": checking, "open_invoices": data["open_invoices"],
            "leases": data["leases"], "pending_payment_requests": data["pending_payment_requests"]}


@app.post("/api/payments/{payment_request_id}/approve")
async def approve_payment(payment_request_id: int, body: Approval) -> dict:
    """Human clicks Approve: execute the payment (money moves, cash goes down)."""
    result = await mcp_call("approve_payment", payment_request_id=payment_request_id, approved_by=body.approved_by)
    _human_audit("approve_payment", body.approved_by, result)
    emit("payment_approved", None, None, by=body.approved_by, payment_request_id=payment_request_id,
         amount=result["amount"], payee=result["payee"], balance_after=result["balance_after"])
    return result


@app.post("/api/payments/{payment_request_id}/reject")
async def reject_payment(payment_request_id: int, body: Rejection) -> dict:
    result = await mcp_call("reject_payment", payment_request_id=payment_request_id,
                            rejected_by=body.rejected_by, reason=body.reason)
    _human_audit("reject_payment", body.rejected_by, result)
    emit("payment_rejected", None, None, by=body.rejected_by, payment_request_id=payment_request_id)
    return result


@app.post("/api/decisions/{decision_id}/approve")
async def approve_decision(decision_id: int, body: Approval) -> dict:
    """Human approves the Boss's decision: the ticket becomes resolved."""
    result = await mcp_call("approve_decision", decision_id=decision_id, approved_by=body.approved_by)
    _human_audit("approve_decision", body.approved_by, result)
    emit("ticket_resolved", result["ticket_id"], None, by=body.approved_by, decision_id=decision_id)
    return result


@app.post("/api/reset")
async def reset(body: ResetRequest) -> dict:
    """Reset the working database to the original for a fresh run. The audit trail is kept."""
    if any(r.get("status") == "running" for r in RUNS.values()):
        raise HTTPException(409, "A run is in progress. Reset after it finishes.")
    result = await mcp_call("reset_database", confirm=body.confirm)
    RUNS.clear()
    _human_audit("reset_database", "dashboard", result)
    emit("reset", None, None, checking_balance=result["checking_balance"])
    return result


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "ticket":
        result = asyncio.run(run_ticket(int(sys.argv[2])))
        print(json.dumps(result.model_dump(), indent=2))
    else:
        print(__doc__)
