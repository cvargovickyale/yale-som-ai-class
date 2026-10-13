"""Campus Customs MCP server: the shop's tools, shared by every agent.

Every tool works on data/campus_customs_new.db (the working copy) and returns
only values from the database, plus arithmetic on those values. "Today" is
desk.date_today, never the computer's clock. The original
data/campus_customs.db is never opened.

Agent tools never move money, stock, or messages. The write tools only create
*pending* records (a hold, a reprint request, a payment request, a draft, a
decision) that a human approves later on the dashboard. The shop's rules are
enforced here in code, not left to the agents' prompts:

  - A vendor with an open unpaid invoice can't take a reprint order.
  - A payment can't be proposed if it would take cash below $0 (counting
    payments already waiting for approval).
  - The same invoice or rent can't be proposed twice; the same stock can't
    be held twice.
  - Messages are drafts only, addressed to the ticket's requester. Nothing
    is ever sent.

Tools                  Agent(s)            Tables
  list_open_tickets    Boss                tickets, decisions
  get_ticket           Boss, Facilities,   tickets, desk, invoices, vendors,
                       Customer Service    leases, + pending records
  record_decision      Boss                decisions (writes, pending)
  check_stock          Inventory           inventory, stock_holds
  find_vendor          Inventory           inventory, vendors, invoices
  reserve_stock        Inventory           stock_holds (writes, pending)
  request_reprint      Inventory           reprint_requests (writes, pending)
  price_and_margin     Accounting          pricing, cash_accounts
  get_cash_and_bills   Accounting          cash_accounts, invoices, leases,
                                           payment_requests
  propose_payment      Accounting          payment_requests (writes, pending)
  get_lease            Facilities          leases, payments
  save_draft_message   Customer Service    message_drafts (writes, draft only)

Run:  python mcp_server/server.py          (stdio, used by Claude Code via .mcp.json)
      python mcp_server/server.py --http   (HTTP on 127.0.0.1:$MCP_PORT, default 8765, used by the backend)
"""

import os
import sqlite3
import sys
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = Path(os.environ.get("CAMPUS_CUSTOMS_DB", DATA_DIR / "campus_customs_new.db")).resolve()
ORIGINAL_DB = (DATA_DIR / "campus_customs.db").resolve()

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
PENDING_WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)

mcp = FastMCP(
    name="campus-customs",
    instructions=(
        "Tools for the Campus Customs shop database. Every number comes from "
        "the database. Today is desk.date_today. If a tool says something "
        "was not found or refuses an action, do not guess or work around it. "
        "Write tools only create pending records for a human to approve."
    ),
)

# Work tables the agent team adds to the working copy. The original data has
# nowhere to record pending approvals, holds, reprint orders, or drafts.
# Created on the first write; a reset (copying the original over the working
# copy) removes them again.
WORK_TABLES = """
CREATE TABLE IF NOT EXISTS stock_holds (
    id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL, sku TEXT NOT NULL,
    size TEXT NOT NULL, qty INTEGER NOT NULL, status TEXT NOT NULL,
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reprint_requests (
    id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL, vendor_id INTEGER NOT NULL,
    sku TEXT NOT NULL, size TEXT NOT NULL, qty INTEGER NOT NULL,
    unit_cost REAL NOT NULL, est_cost REAL NOT NULL, expected_arrival TEXT NOT NULL,
    status TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS payment_requests (
    id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL, kind TEXT NOT NULL,
    ref_id INTEGER NOT NULL, payee TEXT NOT NULL, amount REAL NOT NULL,
    account TEXT NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL,
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS message_drafts (
    id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL, to_name TEXT NOT NULL,
    subject TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL,
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL, summary TEXT NOT NULL,
    reasoning TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
"""


# ---------------------------------------------------------------- helpers

def _connect(read_only: bool = True) -> sqlite3.Connection:
    """Open the working copy. Refuses the original so it can't be written by mistake."""
    if DB_PATH == ORIGINAL_DB:
        raise ToolError("Refusing to use the original campus_customs.db; point at campus_customs_new.db.")
    if not DB_PATH.exists():
        raise ToolError(f"Working database not found: {DB_PATH.name}. Copy campus_customs.db to it first.")
    uri = DB_PATH.as_uri() + ("?mode=ro" if read_only else "")
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    if not read_only:
        conn.executescript(WORK_TABLES)
    return conn


def _today(conn: sqlite3.Connection) -> date:
    return date.fromisoformat(conn.execute("SELECT date_today FROM desk").fetchone()["date_today"])


def _now() -> str:
    """Real timestamp for when a record was created (business dates use desk.date_today)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _money(x: float) -> float:
    return round(float(x), 2)


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _rows(conn: sqlite3.Connection, table: str, where: str, args: tuple) -> list[dict]:
    """Rows from a work table, or [] if no agent has written one yet."""
    if not _has_table(conn, table):
        return []
    return [dict(r) for r in conn.execute(f"SELECT * FROM {table} WHERE {where} ORDER BY id", args)]


def _ticket_or_error(conn: sqlite3.Connection, ticket_id: int) -> sqlite3.Row:
    t = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if t is None:
        ids = [r["id"] for r in conn.execute("SELECT id FROM tickets ORDER BY id")]
        raise ToolError(f"Ticket {ticket_id} not found. Ticket ids: {ids}.")
    return t


def _pending_for_ticket(conn: sqlite3.Connection, ticket_id: int) -> dict:
    """Everything the team has already put in motion for a ticket, so no one repeats it."""
    return {
        "stock_holds": _rows(conn, "stock_holds", "ticket_id = ? AND status = 'held'", (ticket_id,)),
        "reprint_requests": _rows(conn, "reprint_requests", "ticket_id = ? AND status = 'pending_approval'", (ticket_id,)),
        "payment_requests": _rows(conn, "payment_requests", "ticket_id = ? AND status = 'pending_approval'", (ticket_id,)),
        "message_drafts": _rows(conn, "message_drafts", "ticket_id = ? AND status = 'draft'", (ticket_id,)),
        "decision": next(iter(_rows(conn, "decisions", "ticket_id = ? AND status = 'pending_approval'", (ticket_id,))), None),
    }


def _held_qty(conn: sqlite3.Connection, sku: str, size: str) -> int:
    if not _has_table(conn, "stock_holds"):
        return 0
    return conn.execute(
        "SELECT COALESCE(SUM(qty), 0) FROM stock_holds WHERE sku = ? AND size = ? AND status = 'held'", (sku, size)
    ).fetchone()[0]


def _pending_payments_total(conn: sqlite3.Connection, account: str) -> float:
    if not _has_table(conn, "payment_requests"):
        return 0.0
    return conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payment_requests WHERE account = ? AND status = 'pending_approval'",
        (account,),
    ).fetchone()[0]


def _open_invoices(conn: sqlite3.Connection, today: date, vendor_id: int | None = None) -> list[dict]:
    sql = ("SELECT i.id, i.vendor_id, v.name AS vendor_name, i.amount, i.due_date, i.status, i.description "
           "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.status = 'open'")
    args: tuple = ()
    if vendor_id is not None:
        sql += " AND i.vendor_id = ?"
        args = (vendor_id,)
    out = []
    for r in conn.execute(sql + " ORDER BY i.due_date", args):
        days = (today - date.fromisoformat(r["due_date"])).days
        out.append({**dict(r), "amount": _money(r["amount"]), "days_overdue": max(0, days),
                    "days_until_due": max(0, -days), "is_overdue": days > 0})
    return out


def _lease_view(conn: sqlite3.Connection, lease: sqlite3.Row, today: date) -> dict:
    days_left = (date.fromisoformat(lease["next_due"]) - today).days
    return {**dict(lease), "monthly_rent": _money(lease["monthly_rent"]),
            "days_until_due": days_left, "is_overdue": days_left < 0}


# ---------------------------------------------------------------- Boss

@mcp.tool(annotations=READ_ONLY)
def list_open_tickets() -> dict:
    """Boss: every open ticket on the board, oldest first, with any decision already waiting for approval.

    Reads: tickets, decisions.
    """
    with closing(_connect()) as conn:
        today = _today(conn)
        tickets = [dict(r) for r in conn.execute("SELECT * FROM tickets WHERE status = 'open' ORDER BY created_at")]
        for t in tickets:
            d = _rows(conn, "decisions", "ticket_id = ? AND status = 'pending_approval'", (t["id"],))
            t["pending_decision"] = d[0] if d else None
    return {"date_today": today.isoformat(), "open_count": len(tickets), "tickets": tickets}


@mcp.tool(annotations=READ_ONLY)
def get_ticket(ticket_id: int) -> dict:
    """One ticket with who asked, what they asked, its linked records, and what's already pending for it.

    Linked invoice: vendor, amount, days overdue. Linked lease: landlord, rent,
    days until due. Both measured from desk.date_today. "pending" lists holds,
    reprint requests, payment requests, drafts, and a decision the team has
    already created for this ticket, so no one repeats them.
    Reads: tickets, desk, invoices, vendors, leases, and the team's pending records.
    """
    with closing(_connect()) as conn:
        t = _ticket_or_error(conn, ticket_id)
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
                result["linked_lease"] = _lease_view(conn, lease, today)

        result["pending"] = _pending_for_ticket(conn, ticket_id)
    return result


@mcp.tool(annotations=PENDING_WRITE)
def record_decision(ticket_id: int, summary: str, reasoning: str) -> dict:
    """Boss: record the final call on a ticket. It waits for human approval; it does not close the ticket.

    summary: the decision in one or two sentences (what the shop will do).
    reasoning: why, using the numbers the team found (stock, cost, margin, cash, dates).
    One pending decision per ticket: recording again replaces the earlier pending one.
    Writes: decisions (status pending_approval). Returns the decision and every pending record for the ticket.
    """
    if not summary.strip() or not reasoning.strip():
        raise ToolError("summary and reasoning must both be filled in.")
    with closing(_connect(read_only=False)) as conn, conn:
        t = _ticket_or_error(conn, ticket_id)
        if t["status"] != "open":
            raise ToolError(f"Ticket {ticket_id} is {t['status']!r}, not open.")
        existing = conn.execute(
            "SELECT id FROM decisions WHERE ticket_id = ? AND status = 'pending_approval'", (ticket_id,)
        ).fetchone()
        if existing:
            conn.execute("UPDATE decisions SET summary = ?, reasoning = ?, created_at = ? WHERE id = ?",
                         (summary.strip(), reasoning.strip(), _now(), existing["id"]))
            decision_id, action = existing["id"], "replaced"
        else:
            cur = conn.execute(
                "INSERT INTO decisions (ticket_id, summary, reasoning, status, created_at) VALUES (?, ?, ?, 'pending_approval', ?)",
                (ticket_id, summary.strip(), reasoning.strip(), _now()))
            decision_id, action = cur.lastrowid, "created"
        pending = _pending_for_ticket(conn, ticket_id)
    return {"decision_id": decision_id, "action": action, "status": "pending_approval",
            "note": "A human must approve this decision before the ticket is closed.", "pending": pending}


# ---------------------------------------------------------------- Inventory

@mcp.tool(annotations=READ_ONLY)
def check_stock(sku: str, size: str | None = None, qty_needed: int | None = None) -> dict:
    """Inventory: units on hand for a SKU, by size, and how many are already held for other tickets.

    Give a size to get that size's count; also give qty_needed to get the
    shortfall (how many more units the shop would need). "available" is on
    hand minus units already held.
    Reads: inventory, stock_holds.
    """
    if qty_needed is not None and qty_needed < 1:
        raise ToolError("qty_needed must be at least 1.")
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT name, size, qty, location FROM inventory WHERE sku = ? ORDER BY rowid", (sku,)
        ).fetchall()
        if not rows:
            raise ToolError(f"SKU {sku!r} is not in inventory.")
        held = {r["size"]: _held_qty(conn, sku, r["size"]) for r in rows}

    result = {
        "sku": sku,
        "name": rows[0]["name"],
        "location": rows[0]["location"],
        "sizes": [{"size": r["size"], "qty": r["qty"]} for r in rows],
        "total_on_hand": sum(r["qty"] for r in rows),
    }
    if any(held.values()):
        result["held"] = [{"size": s, "held": h, "available": next(r["qty"] for r in rows if r["size"] == s) - h}
                          for s, h in held.items() if h]
    if size is not None:
        match = next((r for r in rows if r["size"] == size), None)
        if match is None:
            sizes = ", ".join(r["size"] for r in rows)
            raise ToolError(f"Size {size!r} does not exist for {sku}. Sizes: {sizes}.")
        available = match["qty"] - held[size]
        requested = {"size": size, "qty_on_hand": match["qty"]}
        if held[size]:
            requested.update(held=held[size], available=available)
        if qty_needed is not None:
            requested["qty_needed"] = qty_needed
            requested["shortfall"] = max(0, qty_needed - available)
            requested["can_fill_from_stock"] = available >= qty_needed
        result["requested"] = requested
    return result


@mcp.tool(annotations=READ_ONLY)
def find_vendor(sku: str) -> dict:
    """Inventory: which vendors could restock a SKU, their lead time, and whether each is blocked.

    The data has no SKU-to-vendor link, so this returns every vendor with its
    specialty for you to match against the product name, plus evidence from
    past invoices that name this SKU. A vendor with any open unpaid invoice is
    blocked: it will not ship new product until that invoice is paid.
    earliest_arrival = desk.date_today + lead_days (only if not blocked).
    Reads: inventory, vendors, invoices.
    """
    with closing(_connect()) as conn:
        item = conn.execute("SELECT name FROM inventory WHERE sku = ? LIMIT 1", (sku,)).fetchone()
        if item is None:
            raise ToolError(f"SKU {sku!r} is not in inventory.")
        today = _today(conn)
        vendors = []
        for v in conn.execute("SELECT * FROM vendors ORDER BY id"):
            open_inv = _open_invoices(conn, today, v["id"])
            past = [dict(r) for r in conn.execute(
                "SELECT id, amount, due_date, status, description FROM invoices WHERE vendor_id = ? AND description LIKE ?",
                (v["id"], f"%{sku}%"))]
            blocked = bool(open_inv)
            vendors.append({
                "vendor_id": v["id"], "name": v["name"], "specialty": v["specialty"], "lead_days": v["lead_days"],
                "blocked": blocked, "blocking_invoices": open_inv,
                "earliest_arrival": None if blocked else (today + timedelta(days=v["lead_days"])).isoformat(),
                "earliest_arrival_if_unblocked_today": (today + timedelta(days=v["lead_days"])).isoformat(),
                "past_invoices_for_this_sku": past,
            })
    return {"date_today": today.isoformat(), "sku": sku, "product_name": item["name"], "vendors": vendors}


@mcp.tool(annotations=PENDING_WRITE)
def reserve_stock(ticket_id: int, sku: str, size: str, qty: int) -> dict:
    """Inventory: hold units on the shelf for a ticket so no other ticket promises them.

    Does not change inventory.qty; stock leaves the shelf only when a human
    approves the ticket. Refuses more than is available (on hand minus other
    holds) and refuses a second hold for the same ticket, SKU, and size.
    Writes: stock_holds (status held).
    """
    if qty < 1:
        raise ToolError("qty must be at least 1.")
    with closing(_connect(read_only=False)) as conn, conn:
        _ticket_or_error(conn, ticket_id)
        row = conn.execute("SELECT qty FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone()
        if row is None:
            raise ToolError(f"{sku} size {size!r} is not in inventory.")
        dup = conn.execute(
            "SELECT id, qty FROM stock_holds WHERE ticket_id = ? AND sku = ? AND size = ? AND status = 'held'",
            (ticket_id, sku, size)).fetchone()
        if dup:
            raise ToolError(f"Ticket {ticket_id} already holds {dup['qty']} of {sku} {size} (hold {dup['id']}). Nothing changed.")
        available = row["qty"] - _held_qty(conn, sku, size)
        if qty > available:
            raise ToolError(f"Only {available} of {sku} {size} available (on hand {row['qty']}). Hold at most {available}.")
        cur = conn.execute(
            "INSERT INTO stock_holds (ticket_id, sku, size, qty, status, created_at) VALUES (?, ?, ?, ?, 'held', ?)",
            (ticket_id, sku, size, qty, _now()))
    return {"hold_id": cur.lastrowid, "ticket_id": ticket_id, "sku": sku, "size": size, "qty": qty,
            "status": "held", "available_after_hold": available - qty}


@mcp.tool(annotations=PENDING_WRITE)
def request_reprint(ticket_id: int, sku: str, size: str, qty: int, vendor_id: int) -> dict:
    """Inventory: ask a vendor to reprint a SKU/size. Creates a request for human approval; nothing is ordered yet.

    Refuses if the vendor has any open unpaid invoice (it won't ship) and
    names the invoice to pay first. Refuses a duplicate request for the same
    ticket, SKU, and size. Cost = qty x pricing.unit_cost; expected arrival =
    desk.date_today + vendor lead_days.
    Writes: reprint_requests (status pending_approval).
    """
    if qty < 1:
        raise ToolError("qty must be at least 1.")
    with closing(_connect(read_only=False)) as conn, conn:
        _ticket_or_error(conn, ticket_id)
        today = _today(conn)
        v = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if v is None:
            raise ToolError(f"Vendor {vendor_id} not found.")
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            raise ToolError(f"{sku} size {size!r} is not in inventory.")
        blocking = _open_invoices(conn, today, vendor_id)
        if blocking:
            inv = blocking[0]
            raise ToolError(
                f"{v['name']} is blocked: invoice {inv['id']} (${inv['amount']:,.2f}, due {inv['due_date']}, "
                f"{inv['days_overdue']} days overdue) is unpaid. The vendor won't ship until it's paid, "
                f"which needs human approval. No reprint was requested.")
        dup = conn.execute(
            "SELECT id FROM reprint_requests WHERE ticket_id = ? AND sku = ? AND size = ? AND status = 'pending_approval'",
            (ticket_id, sku, size)).fetchone()
        if dup:
            raise ToolError(f"Reprint request {dup['id']} for ticket {ticket_id} {sku} {size} is already pending. Nothing changed.")
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            raise ToolError(f"SKU {sku!r} has no pricing row, so the reprint cost is unknown.")
        arrival = (today + timedelta(days=v["lead_days"])).isoformat()
        est = _money(price["unit_cost"] * qty)
        cur = conn.execute(
            "INSERT INTO reprint_requests (ticket_id, vendor_id, sku, size, qty, unit_cost, est_cost, expected_arrival, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending_approval', ?)",
            (ticket_id, vendor_id, sku, size, qty, price["unit_cost"], est, arrival, _now()))
    return {"reprint_request_id": cur.lastrowid, "vendor": v["name"], "sku": sku, "size": size, "qty": qty,
            "unit_cost": _money(price["unit_cost"]), "est_cost": est, "expected_arrival": arrival,
            "status": "pending_approval", "note": "A human must approve this order."}


# ---------------------------------------------------------------- Accounting

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
def get_cash_and_bills() -> dict:
    """Accounting: cash on hand, every open invoice and upcoming rent, and payments already waiting for approval.

    cash_after_pending = balance minus payment requests already waiting for
    approval; that's what any new payment has to fit inside. Days overdue /
    until due are measured from desk.date_today.
    Reads: desk, cash_accounts, invoices, vendors, leases, payment_requests.
    """
    with closing(_connect()) as conn:
        today = _today(conn)
        accounts = []
        for c in conn.execute("SELECT name, balance, date FROM cash_accounts ORDER BY name"):
            pending = _pending_payments_total(conn, c["name"])
            accounts.append({"name": c["name"], "balance": _money(c["balance"]), "as_of": c["date"],
                             "pending_payments": _money(pending), "cash_after_pending": _money(c["balance"] - pending)})
        invoices = _open_invoices(conn, today)
        leases = [_lease_view(conn, l, today) for l in conn.execute("SELECT * FROM leases ORDER BY next_due")]
        pending_reqs = _rows(conn, "payment_requests", "status = 'pending_approval'", ())
    bills_total = sum(i["amount"] for i in invoices) + sum(l["monthly_rent"] for l in leases)
    return {
        "date_today": today.isoformat(),
        "cash_accounts": accounts,
        "open_invoices": invoices,
        "leases": leases,
        "pending_payment_requests": pending_reqs,
        "all_open_bills_total": _money(bills_total),
        "cash_left_if_all_bills_paid": _money(sum(a["balance"] for a in accounts) - bills_total),
    }


@mcp.tool(annotations=PENDING_WRITE)
def propose_payment(ticket_id: int, kind: Literal["invoice", "rent"], ref_id: int, reason: str, account: str = "checking") -> dict:
    """Accounting: propose paying an invoice or a lease's rent. A human must approve it; no money moves now.

    kind="invoice": ref_id is invoices.id (amount = the invoice amount).
    kind="rent": ref_id is leases.id (amount = monthly_rent).
    The bill must be the one linked to the ticket (tickets.invoice_id or
    tickets.lease_id). The amount always comes from the database. Refuses if the bill is already
    paid or already proposed, or if the payment would take the account below
    $0 after payments already waiting for approval.
    Writes: payment_requests (status pending_approval).
    """
    if not reason.strip():
        raise ToolError("reason must be filled in.")
    with closing(_connect(read_only=False)) as conn, conn:
        t = _ticket_or_error(conn, ticket_id)
        today = _today(conn)
        linked = t["invoice_id"] if kind == "invoice" else t["lease_id"]
        if linked != ref_id:
            raise ToolError(
                f"Ticket {ticket_id} is not linked to {kind} {ref_id} (its linked {kind}: {linked}). "
                f"Propose a payment only under the ticket that bill belongs to.")
        if kind == "invoice":
            inv = conn.execute("SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id "
                               "WHERE i.id = ?", (ref_id,)).fetchone()
            if inv is None:
                raise ToolError(f"Invoice {ref_id} not found.")
            if inv["status"] != "open":
                raise ToolError(f"Invoice {ref_id} is {inv['status']!r}, not open. Nothing to pay.")
            amount, payee = inv["amount"], inv["vendor_name"]
            detail = {"due_date": inv["due_date"], "days_overdue": max(0, (today - date.fromisoformat(inv["due_date"])).days)}
        else:
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if lease is None:
                raise ToolError(f"Lease {ref_id} not found.")
            amount, payee = lease["monthly_rent"], lease["landlord"]
            detail = {"next_due": lease["next_due"], "days_until_due": (date.fromisoformat(lease["next_due"]) - today).days}

        dup = conn.execute("SELECT id FROM payment_requests WHERE kind = ? AND ref_id = ? AND status = 'pending_approval'",
                           (kind, ref_id)).fetchone()
        if dup:
            raise ToolError(f"Payment request {dup['id']} for {kind} {ref_id} is already waiting for approval. Nothing changed.")
        acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if acct is None:
            raise ToolError(f"Cash account {account!r} not found.")
        pending = _pending_payments_total(conn, account)
        after = acct["balance"] - pending - amount
        if after < 0:
            raise ToolError(
                f"Refused: paying ${amount:,.2f} to {payee} would leave {account} at ${after:,.2f} "
                f"(balance ${acct['balance']:,.2f}, already pending ${pending:,.2f}). Cash can't go below $0. "
                f"Recommend an alternative instead.")
        cur = conn.execute(
            "INSERT INTO payment_requests (ticket_id, kind, ref_id, payee, amount, account, reason, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending_approval', ?)",
            (ticket_id, kind, ref_id, payee, amount, account, reason.strip(), _now()))
    return {"payment_request_id": cur.lastrowid, "kind": kind, "ref_id": ref_id, "payee": payee,
            "amount": _money(amount), **detail, "account": account,
            "cash_after_if_approved": _money(after), "status": "pending_approval",
            "note": "A human must approve this payment. No money has moved."}


# ---------------------------------------------------------------- Facilities

@mcp.tool(annotations=READ_ONLY)
def get_lease(lease_id: int) -> dict:
    """Facilities: one lease: the space, landlord, monthly rent, next due date, days until due, and past rent payments.

    Reads: leases, payments.
    """
    with closing(_connect()) as conn:
        lease = conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone()
        if lease is None:
            ids = [r["id"] for r in conn.execute("SELECT id FROM leases ORDER BY id")]
            raise ToolError(f"Lease {lease_id} not found. Lease ids: {ids}.")
        today = _today(conn)
        paid = [dict(r) for r in conn.execute(
            "SELECT * FROM payments WHERE kind = 'rent' AND ref_id = ? ORDER BY paid_at", (lease_id,))]
        pending = _rows(conn, "payment_requests", "kind = 'rent' AND ref_id = ? AND status = 'pending_approval'", (lease_id,))
    return {"date_today": today.isoformat(), "lease": _lease_view(conn, lease, today),
            "rent_payments": paid, "pending_rent_requests": pending}


# ---------------------------------------------------------------- Customer Service

@mcp.tool(annotations=PENDING_WRITE)
def save_draft_message(ticket_id: int, to_name: str, subject: str, body: str) -> dict:
    """Customer Service: save a draft reply to the ticket's requester. Drafts are never sent.

    to_name must be the ticket's requester. One draft per ticket: saving again
    replaces the earlier draft. Use only facts the team got from tools.
    Writes: message_drafts (status draft).
    """
    if not subject.strip() or not body.strip():
        raise ToolError("subject and body must both be filled in.")
    with closing(_connect(read_only=False)) as conn, conn:
        t = _ticket_or_error(conn, ticket_id)
        if to_name.strip().lower() != t["requester"].strip().lower():
            raise ToolError(f"Ticket {ticket_id}'s requester is {t['requester']!r}. Drafts can only go to the requester.")
        existing = conn.execute("SELECT id FROM message_drafts WHERE ticket_id = ? AND status = 'draft'", (ticket_id,)).fetchone()
        if existing:
            conn.execute("UPDATE message_drafts SET subject = ?, body = ?, created_at = ? WHERE id = ?",
                         (subject.strip(), body.strip(), _now(), existing["id"]))
            draft_id, action = existing["id"], "replaced"
        else:
            cur = conn.execute(
                "INSERT INTO message_drafts (ticket_id, to_name, subject, body, status, created_at) VALUES (?, ?, ?, ?, 'draft', ?)",
                (ticket_id, t["requester"], subject.strip(), body.strip(), _now()))
            draft_id, action = cur.lastrowid, "created"
    return {"draft_id": draft_id, "action": action, "to": t["requester"], "subject": subject.strip(),
            "status": "draft", "note": "Saved as a draft. Nothing was sent."}


if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="http", host="127.0.0.1", port=int(os.environ.get("MCP_PORT", "8765")), show_banner=False)
    else:
        mcp.run(show_banner=False)
