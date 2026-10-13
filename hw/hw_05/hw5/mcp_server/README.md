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

## Tools

Read tools open the database read-only. Write tools only create **pending**
records for a human to approve on the dashboard. No tool moves money, takes
stock off the shelf, or sends a message.

| Tool | For | Inputs | Reads / writes | Returns |
|---|---|---|---|---|
| `list_open_tickets` | Boss | none | reads `tickets`, `decisions` | Open tickets, oldest first, with any pending decision |
| `get_ticket` | Boss, Facilities, CS | `ticket_id` | reads `tickets`, `desk`, `invoices`, `vendors`, `leases`, pending tables | The ticket, its linked invoice (days overdue) or lease (days until due), and everything already pending for it |
| `record_decision` | Boss | `ticket_id`, `summary`, `reasoning` | writes `decisions` | The decision (pending approval) and every pending record for the ticket |
| `check_stock` | Inventory | `sku`, optional `size`, `qty_needed` | reads `inventory`, `stock_holds` | On hand per size, units held, available, shortfall |
| `find_vendor` | Inventory | `sku` | reads `inventory`, `vendors`, `invoices` | Every vendor's specialty, lead time, blocked status and blocking invoices, earliest arrival, past invoices naming this SKU |
| `reserve_stock` | Inventory | `ticket_id`, `sku`, `size`, `qty` | writes `stock_holds` | A hold, or an error if more than available or already held |
| `request_reprint` | Inventory | `ticket_id`, `sku`, `size`, `qty`, `vendor_id` | writes `reprint_requests` | A pending reprint (cost, expected arrival), or an error if the vendor is blocked |
| `price_and_margin` | Accounting | `sku`, `qty`, `discount_pct` | reads `pricing`, `cash_accounts` | Cost, price, margin at list and after discount, revenue/cost/profit, cash |
| `get_cash_and_bills` | Accounting | none | reads `cash_accounts`, `invoices`, `leases`, `payment_requests` | Cash, cash after pending payments, open invoices, rent due, totals |
| `propose_payment` | Accounting | `ticket_id`, `kind` (`invoice`/`rent`), `ref_id`, `reason` | writes `payment_requests` | A pending payment request, or an error (not this ticket's bill, already pending, or cash would go below $0) |
| `get_lease` | Facilities | `lease_id` | reads `leases`, `payments`, `payment_requests` | Lease, days until due, past and pending rent payments |
| `save_draft_message` | Customer Service | `ticket_id`, `to_name`, `subject`, `body` | writes `message_drafts` | A draft to the ticket's requester (never sent) |

### Rules enforced in code

- A vendor with any open unpaid invoice can't take a reprint order.
- A payment can't be proposed if cash would go below $0 after payments
  already waiting for approval.
- A payment can only be proposed for the bill linked to its ticket.
- No duplicates: the same bill, hold, or reprint can't be requested twice.
- Drafts go only to the ticket's requester and are never sent.

### Work tables

The original data has nowhere to record pending work, so the first write
creates five tables in the **working copy only**: `stock_holds`,
`reprint_requests`, `payment_requests`, `message_drafts`, `decisions`.
Resetting (copying the original over the working copy) removes them.

## Running

Install once from the `hw5/` folder:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Two ways to run it:

```bash
.venv/bin/python mcp_server/server.py          # stdio: Claude Code starts it from .mcp.json
.venv/bin/python mcp_server/server.py --http   # HTTP on 127.0.0.1:8765/mcp, for the backend
```

Set `MCP_PORT` to use a different port.
