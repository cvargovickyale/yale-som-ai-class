"""Gateway 2000-style stock research chatbot with live tool calls.

Project conventions: see ../../AGENTS.md, especially the Dash run and process
cleanup rules.
"""

import json
import os
from datetime import datetime, timezone

import dash
from dash import Input, Output, State, dcc, html
import requests
import yfinance as yf
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env")))
API_KEY = os.getenv("PORTKEY_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
client = OpenAI(
    api_key=API_KEY,
    base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
    default_headers={"x-portkey-api-key": API_KEY},
)


def get_stock_price(ticker: str, tstart: str, tstop: str) -> dict:
    """Return a Yahoo Finance closing-price series for an explicit date range."""
    symbol = ticker.upper().strip()
    history = yf.download(symbol, start=tstart, end=tstop, auto_adjust=False, progress=False)
    if history.empty:
        raise ValueError(f"Yahoo Finance returned no data for {symbol}.")
    close = history["Close"]
    if hasattr(close, "columns"):
        close = close[symbol]
    series = [{"date": index.strftime("%Y-%m-%d"), "close": round(float(value), 4)} for index, value in close.dropna().items()]
    return {"ticker": symbol, "tstart": tstart, "tstop": tstop, "price_series": series, "source": "Yahoo Finance"}


def stock_returns(price_series: list[dict]) -> dict:
    """Calculate returns and risk metrics from a price series."""
    if len(price_series) < 2:
        raise ValueError("At least two prices are required to calculate returns.")
    prices = [float(item["close"]) for item in price_series]
    returns = [(prices[index] / prices[index - 1]) - 1 for index in range(1, len(prices))]
    momentum = float((prices[-1] / prices[0] - 1) * 100)
    risk_free = 0.04
    import numpy as np
    return_array = np.array(returns)
    volatility_raw = return_array.std(ddof=1) if len(returns) > 1 else 0
    volatility = float(volatility_raw * (252 ** 0.5) * 100) if len(returns) > 1 else None
    sharpe = float((return_array.mean() * 252 - risk_free) / (volatility_raw * (252 ** 0.5))) if volatility_raw else None
    return {
        "latest_price_usd": prices[-1],
        "as_of": price_series[-1]["date"],
        "observations": len(price_series),
        "returns": [{"from": price_series[index - 1]["date"], "to": price_series[index]["date"], "return_percent": round(value * 100, 4)} for index, value in enumerate(returns, 1)],
        "momentum_percent": round(momentum, 2) if momentum is not None else None,
        "annualized_volatility_percent": round(volatility, 2) if volatility is not None else None,
        "sharpe_ratio": round(sharpe, 3) if sharpe is not None else None,
        "risk_free_rate_assumption": risk_free,
    }


def news_search(query: str, days: int = 14) -> dict:
    """Search recent news through DuckDuckGo's HTML endpoint."""
    response = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": f"{query} stock financial news past {days} days"},
        headers={"User-Agent": "Mozilla/5.0"}, timeout=15,
    )
    response.raise_for_status()
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for result in soup.select(".result")[:6]:
        link = result.select_one(".result__a")
        snippet = result.select_one(".result__snippet")
        if link:
            results.append({"title": link.get_text(" ", strip=True), "url": link.get("href"), "snippet": snippet.get_text(" ", strip=True) if snippet else ""})
    return {"query": query, "results": results, "source": "DuckDuckGo web search"}


TOOLS = [
    {"type": "function", "function": {"name": "get_stock_price", "description": "Get a live Yahoo Finance closing-price series. Use before calculating stock returns or risk metrics; never invent prices.", "parameters": {"type": "object", "properties": {"ticker": {"type": "string"}, "tstart": {"type": "string", "description": "Start date YYYY-MM-DD"}, "tstop": {"type": "string", "description": "End date YYYY-MM-DD"}}, "required": ["ticker", "tstart", "tstop"]}}},
    {"type": "function", "function": {"name": "stock_returns", "description": "Calculate returns, momentum, annualized volatility, and Sharpe ratio from a get_stock_price price series.", "parameters": {"type": "object", "properties": {"price_series": {"type": "array", "items": {"type": "object", "properties": {"date": {"type": "string"}, "close": {"type": "number"}}, "required": ["date", "close"], "additionalProperties": False}}}, "required": ["price_series"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "news_search", "description": "Search the web for recent financial news.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "days": {"type": "integer"}}, "required": ["query"]}}},
]
TOOL_FUNCTIONS = {"get_stock_price": get_stock_price, "stock_returns": stock_returns, "news_search": news_search}


def answer(messages: list[dict]) -> tuple[str, list[str]]:
    tool_status = []
    system = {"role": "system", "content": "You are a careful stock research assistant. Use tools for current prices, metrics, and recent news. Never invent market data. Cite tool sources and dates in answers. Explain when a tool fails or data is stale."}
    working = [system, *messages]
    for _ in range(4):
        response = client.chat.completions.create(model=MODEL, messages=working, tools=TOOLS)
        message = response.choices[0].message
        if not message.tool_calls:
            return message.content or "I could not produce an answer.", tool_status
        working.append(message.model_dump(exclude_none=True))
        for call in message.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            tool_status.append(f"Ran {name}({', '.join(f'{k}={v}' for k, v in args.items())})")
            try:
                result = TOOL_FUNCTIONS[name](**args)
            except Exception as exc:
                result = {"error": str(exc), "source": name}
            working.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
    return "The tool workflow exceeded its safe call limit.", tool_status


def bubble(message: dict) -> html.Div:
    role = message["role"]
    return html.Div(message["content"], className=f"bubble {role}")


app = dash.Dash(__name__)
app.layout = html.Div([
    html.Div([html.Span("STOCK RESEARCH TERMINAL", className="title"), html.Span("LECTURE 03", className="title-right")], className="titlebar"),
    html.Div([html.Div("Live market data + web search", className="status"), dcc.Loading(html.Div(id="chat", className="chat"), type="default")], className="window"),
    dcc.Store(id="history", data=[]),
    html.Div([dcc.Input(id="prompt", type="text", placeholder="Ask about a ticker, volatility, Sharpe, momentum, or recent news...", className="input"), html.Button("SEND", id="send", className="button")], className="composer"),
    html.Div("Press Enter or click SEND · Tool activity appears in the conversation", className="hint"),
], className="desktop")


@app.callback(Output("chat", "children"), Output("history", "data"), Output("prompt", "value"), Input("send", "n_clicks"), Input("prompt", "n_submit"), State("prompt", "value"), State("history", "data"), prevent_initial_call=True)
def chat(_clicks, _submit, value, history):
    if not value or not value.strip():
        return [bubble(m) for m in history], history, value
    history = history or []
    history.append({"role": "user", "content": value.strip()})
    reply, statuses = answer(history)
    if statuses:
        history.append({"role": "tool", "content": "TOOL ACTIVITY\n" + "\n".join(statuses)})
    history.append({"role": "assistant", "content": reply})
    return [bubble(m) for m in history], history, ""


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
