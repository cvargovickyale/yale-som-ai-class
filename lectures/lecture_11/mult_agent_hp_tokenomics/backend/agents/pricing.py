"""Token → dollar pricing, per-agent spend tracking, and the budget kill-switch.

Prices are OpenAI Standard short-context rates in USD per 1M tokens.
input_tokens already INCLUDES cache_read_tokens and cache_write_tokens, so the
uncached remainder is billed at the plain input rate:

    uncached = input − cache_read − cache_write
    cost = uncached·input + cache_read·cached + cache_write·cache_write + output·output
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

PRICING_SOURCE = "https://developers.openai.com/api/docs/pricing"

MODEL_PRICES: dict[str, dict[str, float]] = {
    "gpt-6-luna": {"input": 0.10, "cached": 0.01, "cache_write": 0.125, "output": 0.50},
    "gpt-6-astra": {"input": 10.00, "cached": 1.00, "cache_write": 12.50, "output": 50.00},
}
DEFAULT_MODEL = "gpt-6-luna"

TOKEN_KEYS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")


class BudgetExceeded(Exception):
    """Raised when total spend for a job reaches its USD budget."""

    def __init__(self, spent: float, budget: float):
        super().__init__(f"Budget of ${budget:.4f} reached (spent ${spent:.4f}); run stopped.")
        self.spent = spent
        self.budget = budget


def prices_for(model: str) -> dict[str, float]:
    """Price row for a model; tolerates dated or regional suffixes like 'gpt-6-luna-global'."""
    for name, row in MODEL_PRICES.items():
        if model == name or model.startswith(name + "-"):
            return row
    raise KeyError(f"No price for model {model!r}")


def cost_usd(model: str, usage: dict) -> float:
    p = prices_for(model)
    inp = usage.get("input_tokens", 0) or 0
    read = usage.get("cache_read_tokens", 0) or 0
    write = usage.get("cache_write_tokens", 0) or 0
    out = usage.get("output_tokens", 0) or 0
    uncached = max(inp - read - write, 0)
    dollars = (uncached * p["input"] + read * p["cached"] + write * p["cache_write"] + out * p["output"]) / 1_000_000
    return round(dollars, 8)


def enrich_usage(model: str, usage: dict) -> dict:
    """Copy of a usage dict with cost_usd added."""
    return {**usage, "cost_usd": cost_usd(model, usage)}


@dataclass
class SpendTracker:
    """Running per-agent totals for one job. emit() publishes a `spend` SSE event."""

    model: str
    emit: Callable[..., None]
    budget_usd: float | None = None
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    exceeded: bool = False

    @property
    def total(self) -> dict[str, Any]:
        tot: dict[str, Any] = {k: sum(a.get(k, 0) for a in self.agents.values()) for k in (*TOKEN_KEYS, "requests")}
        tot["cost_usd"] = round(sum(a["cost_usd"] for a in self.agents.values()), 8)
        return tot

    def snapshot(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "budget_usd": self.budget_usd,
            "total_usd": self.total["cost_usd"],
            "budget_exceeded": self.exceeded,
            "agents": self.agents,
            "total": self.total,
        }

    def check(self) -> None:
        """Call before a model request: refuse to start new calls once over budget."""
        if self.exceeded:
            raise BudgetExceeded(self.total["cost_usd"], self.budget_usd or 0)

    def add(self, agent_key: str, usage: dict) -> float:
        """Record one model response's usage. Returns its cost; raises if the budget is hit."""
        cost = cost_usd(self.model, usage)
        row = self.agents.setdefault(agent_key, {**{k: 0 for k in TOKEN_KEYS}, "requests": 0, "cost_usd": 0.0})
        for k in TOKEN_KEYS:
            row[k] += usage.get(k, 0) or 0
        row["requests"] += 1
        row["cost_usd"] = round(row["cost_usd"] + cost, 8)

        spent = self.total["cost_usd"]
        if self.budget_usd is not None and spent >= self.budget_usd:
            self.exceeded = True
        self.emit("spend", **self.snapshot())
        if self.exceeded:
            raise BudgetExceeded(spent, self.budget_usd or 0)
        return cost
