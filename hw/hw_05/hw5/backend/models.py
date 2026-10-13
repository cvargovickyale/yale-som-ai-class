"""Data shapes the agent team hands to each other, to the backend, and to the audit trail.

Agents return these structures, not prose, so code can act on them: the
dashboard reads pending IDs, the audit trail records who asked whom, and the
Boss reads every specialist's report in the same shape.
"""

from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]


class PendingIds(BaseModel):
    """IDs of records waiting for a human. Every ID comes from a tool result."""

    payment_request_ids: list[int] = Field(default_factory=list, description="From propose_payment")
    reprint_request_ids: list[int] = Field(default_factory=list, description="From request_reprint")
    hold_ids: list[int] = Field(default_factory=list, description="From reserve_stock")
    draft_ids: list[int] = Field(default_factory=list, description="From save_draft_message")
    decision_id: int | None = Field(default=None, description="From record_decision")


class SpecialistReport(BaseModel):
    """What Inventory, Accounting, Facilities, or Customer Service returns to whoever delegated to it."""

    agent: AgentName
    ticket_id: int
    findings: list[str] = Field(description="Facts found, each with its numbers, e.g. 'CC-HOOD-NAVY M: 8 on hand, need 20, short 12'")
    actions_taken: list[str] = Field(default_factory=list, description="Pending records created, e.g. 'payment request 1: invoice 501, $840'")
    pending: PendingIds = Field(default_factory=PendingIds)
    recommendation: str = Field(description="What this agent recommends, and why, in one to three sentences")
    blocked: list[str] = Field(default_factory=list, description="Anything a tool refused, and the reason")
    questions_for_caller: list[str] = Field(default_factory=list, description="What this agent needs from whoever asked, to continue")


class BossDecision(BaseModel):
    """The Boss's final call on a ticket. Waits for human approval."""

    ticket_id: int
    outcome: Literal["fulfil", "partial", "alternative", "waiting", "pay", "decline"] = Field(
        description="fulfil = as requested; partial = part now; alternative = something different offered; "
        "waiting = blocked until an approval or delivery; pay = a bill is being paid; decline = no")
    summary: str = Field(description="What the shop will do, in one or two sentences")
    reasoning: str = Field(description="Why, citing the numbers: stock, cost, margin, cash before and after, dates")
    agents_used: list[AgentName] = Field(default_factory=list)
    pending: PendingIds = Field(default_factory=PendingIds, description="Everything waiting for the human, by ID")
    risks: list[str] = Field(default_factory=list, description="Trade-offs or risks the human should know before approving")


# ---------------------------------------------------------------- audit trail

class ToolCallRecord(BaseModel):
    tool: str
    args: dict
    result: str = Field(description="Shortened tool result or error")
    status: Literal["ok", "error", "refused"]


class AgentRunRecord(BaseModel):
    """One agent loop: who ran, who asked, what it did, what it cost. Appended when the loop ends."""

    entry_type: Literal["agent_run"] = "agent_run"
    run_id: str
    parent_run_id: str | None
    agent: AgentName
    chain: list[AgentName] = Field(description="Hand-off path from the Boss to this agent")
    depth: int
    ticket_id: int
    task: str
    started_at: str
    duration_s: float
    models_reported: list[str] = Field(description="Model name on every response; must all be gpt-6-luna")
    model_requests: int
    input_tokens: int
    output_tokens: int
    tool_calls: list[ToolCallRecord]
    status: Literal["ok", "error", "usage_limit", "timeout", "wrong_model"]
    output: dict | None = None
    error: str | None = None


class TicketRun(BaseModel):
    """One full run of the team on one ticket. Appended after its agent entries, which it lists by run_id."""

    entry_type: Literal["ticket_run"] = "ticket_run"
    ticket_id: int
    started_at: str
    duration_s: float
    status: Literal["ok", "error", "usage_limit", "timeout", "wrong_model"]
    decision: BossDecision | None
    run_ids: list[str] = Field(description="The agent_run entries for this ticket run, in start order")
    runs: list[AgentRunRecord] = Field(default_factory=list, description="Returned to callers; not repeated in the audit file")
    totals: dict = Field(description="model_requests, input_tokens, output_tokens, tool_calls, delegations, refused_delegations")
    error: str | None = None
