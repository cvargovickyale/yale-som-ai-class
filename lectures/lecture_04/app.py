"""Dash UI for the Lecture 4 PydanticAI financial analyst."""

import json

import dash
from dash import Input, Output, State, dcc, html

from agent import run_agent


app = dash.Dash(__name__)
app.layout = html.Div([
    html.Div([html.Span("FINANCIAL ANALYST", className="title"), html.Span("LECTURE 04", className="title-right")], className="titlebar"),
    html.Div([
        html.Div("Yahoo Finance + OpenAI native web search", className="status"),
        dcc.Loading(html.Div(id="chat", className="chat"), type="default"),
    ], className="window"),
    dcc.Store(id="history", data=[]),
    dcc.Store(id="audit", data=[]),
    html.Div([dcc.Input(id="prompt", type="text", placeholder="Ask about an approved stock, metrics, or recent news...", className="input"), html.Button("SEND", id="send", className="button")], className="composer"),
    html.Div("Press Enter or click SEND · Tool activity is recorded in the audit panel", className="hint"),
    html.Pre(id="audit-panel", className="audit"),
], className="desktop")


def bubble(message: dict) -> html.Div:
    return html.Div(message["content"], className=f"bubble {message['role']}")


@app.callback(
    Output("chat", "children"), Output("history", "data"), Output("audit-panel", "children"), Output("prompt", "value"),
    Input("send", "n_clicks"), Input("prompt", "n_submit"), State("prompt", "value"), State("history", "data"), State("audit", "data"),
    prevent_initial_call=True,
)
def chat(_clicks, _submit, value, history, audit):
    if not value or not value.strip():
        return [bubble(message) for message in history or []], history or [], json.dumps(audit or [], indent=2), value or ""
    history = history or []
    history.append({"role": "user", "content": value.strip()})
    try:
        reply, events = run_agent(value.strip(), history=history)
        history.append({"role": "assistant", "content": reply})
        audit = (audit or []) + events
    except Exception as exc:
        history.append({"role": "assistant", "content": f"Tool or agent error: {exc}"})
    return [bubble(message) for message in history], history, json.dumps(audit or [], indent=2), ""


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
