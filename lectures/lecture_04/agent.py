"""PydanticAI financial analyst agent for Lecture 4."""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import yfinance as yf
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import NativeTool
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.native_tools import WebSearchTool
from pydantic_ai.providers.openai import OpenAIProvider


load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env")))
UNIVERSE = {"AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "BAC", "GS"}
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
provider = OpenAIProvider(
    base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
    api_key=os.getenv("PORTKEY_API_KEY"),
)
model = OpenAIResponsesModel(MODEL_NAME, provider=provider)


@dataclass
class AnalystDeps:
    portfolio: dict[str, Any] = field(default_factory=dict)
    audit_log: list[dict[str, Any]] = field(default_factory=list)

    def audit(self, event: str, **details: Any) -> None:
        self.audit_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **details,
        })


SYSTEM_PROMPT = """You are a careful financial analyst agent.

Approved stock universe: AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA, JPM, BAC, GS.
Use get_stock_price for all current or historical prices and stock_returns for
returns and risk metrics. Use the native web search tool for recent news.
Never invent, estimate, or silently substitute prices. Distinguish retrieved
facts, deterministic calculations, and your interpretation. State the source
and date range. Do not promise returns, claim certainty, or give personalized
buy/sell instructions. Refuse unsafe requests. Ask for missing ticker or date
range information. Keep answers concise and useful.
"""

analyst = Agent(
    model,
    deps_type=AnalystDeps,
    output_type=str,
    instructions=SYSTEM_PROMPT,
    capabilities=[NativeTool(WebSearchTool(search_context_size="medium", external_web_access=True))],
    retries=1,
)


@analyst.tool
def get_stock_price(ctx: RunContext[AnalystDeps], ticker: str, start: str, stop: str) -> dict[str, Any]:
    """Retrieve an actual daily closing-price series from Yahoo Finance."""
    symbol = ticker.upper().strip()
    if symbol not in UNIVERSE:
        raise ValueError(f"{symbol} is outside the approved stock universe.")
    ctx.deps.audit("tool_call", tool="get_stock_price", arguments={"ticker": symbol, "start": start, "stop": stop})
    prices = yf.download(symbol, start=start, end=stop, auto_adjust=False, progress=False)
    if prices.empty:
        raise ValueError(f"Yahoo Finance returned no prices for {symbol}.")
    close = prices["Close"]
    if hasattr(close, "columns"):
        close = close[symbol]
    series = [{"date": index.strftime("%Y-%m-%d"), "close": round(float(value), 6)} for index, value in close.dropna().items()]
    result = {"ticker": symbol, "start": start, "stop": stop, "price_series": series, "source": "Yahoo Finance"}
    ctx.deps.audit("observation", tool="get_stock_price", result_summary=f"{len(series)} daily prices returned", source="Yahoo Finance")
    return result


@analyst.tool
def stock_returns(ctx: RunContext[AnalystDeps], price_series: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate returns, CAGR, volatility, Sharpe ratio, and max drawdown."""
    if len(price_series) < 2:
        raise ValueError("At least two price observations are required.")
    closes = np.array([float(point["close"]) for point in price_series])
    returns = closes[1:] / closes[:-1] - 1
    years = max((len(price_series) - 1) / 252, 1 / 252)
    cumulative = closes[-1] / closes[0]
    cagr = cumulative ** (1 / years) - 1
    annual_vol = returns.std(ddof=1) * np.sqrt(252) if len(returns) > 1 else 0
    sharpe = (returns.mean() * 252 - 0.04) / annual_vol if annual_vol else None
    running_max = np.maximum.accumulate(closes)
    max_drawdown = np.min(closes / running_max - 1)
    result = {"observations": len(closes), "cumulative_return_percent": round((cumulative - 1) * 100, 2), "cagr_percent": round(cagr * 100, 2), "annualized_volatility_percent": round(annual_vol * 100, 2), "sharpe_ratio": round(float(sharpe), 3) if sharpe is not None else None, "max_drawdown_percent": round(float(max_drawdown) * 100, 2), "risk_free_rate_assumption": 0.04}
    ctx.deps.audit("observation", tool="stock_returns", result_summary=result)
    return result


def run_agent(prompt: str, history: list[dict[str, Any]] | None = None, portfolio: dict[str, Any] | None = None) -> tuple[str, list[dict[str, Any]]]:
    deps = AnalystDeps(portfolio=portfolio or {})
    deps.audit("user_request", request=prompt)
    prior = "\n".join(f"{message['role']}: {message['content']}" for message in (history or [])[:-1])
    context_prompt = f"Conversation so far:\n{prior}\n\nCurrent user request:\n{prompt}" if prior else prompt
    result = analyst.run_sync(context_prompt, deps=deps)
    deps.audit("assistant_response", result_summary="response generated")
    return result.output, deps.audit_log
