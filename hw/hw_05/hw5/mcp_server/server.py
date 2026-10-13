"""Campus Customs MCP server: the shop's tools, shared by every agent.

Every tool reads data/campus_customs_new.db (the working copy) and returns
only values from the database, plus arithmetic on those values. "Today" is
desk.date_today, never the computer's clock. The original
data/campus_customs.db is never opened.

P3 tools (all read-only):
  check_stock      Inventory        inventory
  price_and_margin Accounting       pricing, cash_accounts
  get_ticket       Customer Service tickets, desk, invoices, vendors, leases
"""

import os
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = Path(os.environ.get("CAMPUS_CUSTOMS_DB", DATA_DIR / "campus_customs_new.db")).resolve()
ORIGINAL_DB = (DATA_DIR / "campus_customs.db").resolve()

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

mcp = FastMCP(
    name="campus-customs",
    instructions=(
        "Tools for the Campus Customs shop database. Every number comes from "
        "the database. Today is desk.date_today. If a tool says something "
        "was not found, do not guess a value."
    ),
)


def _connect(read_only: bool = True) -> sqlite3.Connection:
    """Open the working copy. Refuses the original so it can't be written by mistake."""
    if DB_PATH == ORIGINAL_DB:
        raise ToolError("Refusing to use the original campus_customs.db; point at campus_customs_new.db.")
    if not DB_PATH.exists():
        raise ToolError(f"Working database not found: {DB_PATH.name}. Copy campus_customs.db to it first.")
    uri = DB_PATH.as_uri() + ("?mode=ro" if read_only else "")
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _today(conn: sqlite3.Connection) -> date:
    return date.fromisoformat(conn.execute("SELECT date_today FROM desk").fetchone()["date_today"])


def _money(x: float) -> float:
    return round(float(x), 2)


@mcp.tool(annotations=READ_ONLY)
def check_stock(sku: str, size: str | None = None, qty_needed: int | None = None) -> dict:
    """Inventory: units on hand for a SKU, by size.

    Give a size to get that size's count; also give qty_needed to get the
    shortfall (how many more units the shop would need).
    Reads: inventory.
    """
    if qty_needed is not None and qty_needed < 1:
        raise ToolError("qty_needed must be at least 1.")
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT name, size, qty, location FROM inventory WHERE sku = ? ORDER BY rowid", (sku,)
        ).fetchall()
    if not rows:
        raise ToolError(f"SKU {sku!r} is not in inventory.")

    result = {
        "sku": sku,
        "name": rows[0]["name"],
        "location": rows[0]["location"],
        "sizes": [{"size": r["size"], "qty": r["qty"]} for r in rows],
        "total_on_hand": sum(r["qty"] for r in rows),
    }
    if size is not None:
        match = next((r for r in rows if r["size"] == size), None)
        if match is None:
            sizes = ", ".join(r["size"] for r in rows)
            raise ToolError(f"Size {size!r} does not exist for {sku}. Sizes: {sizes}.")
        requested = {"size": size, "qty_on_hand": match["qty"]}
        if qty_needed is not None:
            requested["qty_needed"] = qty_needed
            requested["shortfall"] = max(0, qty_needed - match["qty"])
            requested["can_fill_from_stock"] = match["qty"] >= qty_needed
        result["requested"] = requested
    return result


@mcp.tool(annotations=READ_ONLY)
def price_and_margin(sku: str, qty: int = 1, discount_pct: float = 0) -> dict:
    """Accounting: cost, price, and margin for an order of a SKU.

    Shows margin at list price and at an optional discount (percent off list),
    the order's revenue, cost, and profit, and the current cash balance.
    Reads: pricing, cash_accounts.
    """
    if qty < 1:
        raise ToolError("qty must be at least 1.")
    if not 0 <= discount_pct < 100:
        raise ToolError("discount_pct must be from 0 up to (not including) 100.")
    with closing(_connect()) as conn:
        p = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
        cash = conn.execute("SELECT name, balance, date FROM cash_accounts ORDER BY name").fetchall()
    if p is None:
        raise ToolError(f"SKU {sku!r} has no pricing row.")

    cost, price = p["unit_cost"], p["list_price"]
    unit_price = price * (1 - discount_pct / 100)
    return {
        "sku": sku,
        "unit_cost": _money(cost),
        "list_price": _money(price),
        "margin_pct_at_list": round((price - cost) / price * 100, 1),
        "discount_pct": discount_pct,
        "unit_price_after_discount": _money(unit_price),
        "margin_pct_after_discount": round((unit_price - cost) / unit_price * 100, 1),
        "qty": qty,
        "order_revenue": _money(unit_price * qty),
        "order_cost": _money(cost * qty),
        "order_profit": _money((unit_price - cost) * qty),
        "below_cost": unit_price < cost,
        "cash_accounts": [
            {"name": c["name"], "balance": _money(c["balance"]), "as_of": c["date"]} for c in cash
        ],
    }


@mcp.tool(annotations=READ_ONLY)
def get_ticket(ticket_id: int) -> dict:
    """Customer Service: one ticket with who asked, what they asked, and its linked records.

    Includes the linked invoice (vendor, amount, days overdue) or lease
    (landlord, rent, days until due), measured from desk.date_today.
    Reads: tickets, desk, invoices, vendors, leases.
    """
    with closing(_connect()) as conn:
        t = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            ids = [r["id"] for r in conn.execute("SELECT id FROM tickets ORDER BY id")]
            raise ToolError(f"Ticket {ticket_id} not found. Ticket ids: {ids}.")
        today = _today(conn)
        result = {"date_today": today.isoformat(), "ticket": dict(t)}

        if t["invoice_id"] is not None:
            inv = conn.execute(
                "SELECT i.id, i.amount, i.due_date, i.status, i.description, "
                "v.id AS vendor_id, v.name AS vendor_name, v.lead_days "
                "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (t["invoice_id"],),
            ).fetchone()
            if inv is not None:
                days_late = (today - date.fromisoformat(inv["due_date"])).days
                result["linked_invoice"] = {
                    **dict(inv),
                    "amount": _money(inv["amount"]),
                    "days_overdue": max(0, days_late),
                    "is_overdue": inv["status"] == "open" and days_late > 0,
                }

        if t["lease_id"] is not None:
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (t["lease_id"],)).fetchone()
            if lease is not None:
                days_left = (date.fromisoformat(lease["next_due"]) - today).days
                result["linked_lease"] = {
                    **dict(lease),
                    "monthly_rent": _money(lease["monthly_rent"]),
                    "days_until_due": days_left,
                    "is_overdue": days_left < 0,
                }
    return result


if __name__ == "__main__":
    mcp.run(show_banner=False)
