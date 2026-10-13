# Campus Customs MCP server

## What it's for

The shop's agent team (Boss, Inventory, Accounting, Facilities, Customer
Service) never touches the database directly. Every agent uses the tools in
`server.py`, a [FastMCP](https://gofastmcp.com) server. That gives three
guarantees:

- **One source of facts.** Stock, prices, cash, invoices, and leases come
  from the database, never from a model's memory. If a record doesn't exist,
  the tool returns an error instead of a guess.
- **One place for the shop's rules.** "Today" is `desk.date_today`
  (2026-08-31), so "overdue" and "due in N days" mean the same thing to
  every agent. Later rules (human approval for payments, no negative cash
  balance) will be enforced here, in code.
- **One record of what was asked.** Every tool call goes through the MCP
  protocol, so it can be logged and audited.

## Database

| File | Used by this server? |
|---|---|
| `../data/campus_customs_new.db` | **Yes.** The working copy. Later tools will write to it as tickets get resolved. |
| `../data/campus_customs.db` | **Never.** The original, kept clean for resets. The server refuses to open it. |

To reset, copy the original over the working copy (see the main README). To
point at a different working file, set `CAMPUS_CUSTOMS_DB`.

## Tools (P3: three read-only tools)

All three open the database read-only, so they can't change anything.

| Tool | For | Inputs | Reads | Returns |
|---|---|---|---|---|
| `check_stock` | Inventory | `sku`, optional `size`, optional `qty_needed` | `inventory` | Units on hand per size, total on hand, shelf location; with a size and quantity, the shortfall and whether stock can fill it |
| `price_and_margin` | Accounting | `sku`, `qty` (default 1), `discount_pct` (default 0) | `pricing`, `cash_accounts` | Unit cost, list price, margin at list and after the discount, the order's revenue/cost/profit, whether the price is below cost, and the cash balance |
| `get_ticket` | Customer Service | `ticket_id` | `tickets`, `desk`, `invoices`, `vendors`, `leases` | The ticket (requester, subject, notes, status), plus its linked invoice (vendor, amount, days overdue) or lease (landlord, rent, days until due) |

More tools (writing to the database, payments with human approval,
delegation support) are added in later problems.

## Running

Install once from the `hw5/` folder:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Connecting the server to Claude Code and to the backend is set up in later
problems (`.mcp.json`, P4).
