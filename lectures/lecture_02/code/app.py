import json
from pathlib import Path

import dash
from dash import dcc, html
import plotly.graph_objects as go


ROOT = Path(__file__).parents[1]
DATA_FILE = ROOT / "leases.json"


def load_leases() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text()).get("leases", [])


def make_map(leases: list[dict]) -> go.Figure:
    located = [lease for lease in leases if lease.get("latitude") and lease.get("longitude")]
    figure = go.Figure(go.Scattergeo(
        lat=[lease["latitude"] for lease in located],
        lon=[lease["longitude"] for lease in located],
        text=[lease.get("property_name", "Lease") for lease in located],
        hovertemplate="%{text}<extra></extra>",
        mode="markers",
        marker={"size": 10, "color": "#174a5b"},
    ))
    figure.update_geos(
        scope="usa",
        center={"lat": 41.31, "lon": -72.92},
        projection_scale=30,
        showland=True,
        landcolor="#eeeeee",
        showlakes=True,
        lakecolor="#d8e9ef",
    )
    figure.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0}, height=500)
    return figure


def make_cash_flow_chart(leases: list[dict]) -> go.Figure:
    totals = {}
    for lease in leases:
        for item in lease.get("cash_flows", []):
            totals[item["year"]] = totals.get(item["year"], 0) + item["amount"]
    years = sorted(totals)
    figure = go.Figure(go.Bar(x=years, y=[totals[year] for year in years], marker_color="#d97732"))
    figure.update_layout(
        title="Annual base rent",
        xaxis_title="Year",
        yaxis_title="Dollars",
        margin={"l": 45, "r": 15, "t": 55, "b": 45},
    )
    return figure


leases = load_leases()
app = dash.Dash(__name__)
app.layout = html.Main([
    html.H1("New Haven leases"),
    html.P(f"{len(leases)} leases loaded"),
    dcc.Graph(figure=make_map(leases)),
    dcc.Graph(figure=make_cash_flow_chart(leases)),
], style={"maxWidth": "1000px", "margin": "20px auto", "fontFamily": "Georgia, serif"})


if __name__ == "__main__":
    app.run(debug=False)
