# Campus Customs Multi-Agent Operations — Harness

How the agent team, MCP server, backend, and dashboard fit together.
Working notes are added per problem and consolidated at the end.

## 1. Data

Two copies of the same SQLite database live in `data/`:

| File | Role |
|---|---|
| `campus_customs.db` | Original. Never written to. Copy it over the working copy to reset. |
| `campus_customs_new.db` | Working copy. The MCP server reads and writes only this file. |

"Today" for the shop is `desk.date_today` (**2026-08-31**), never the
computer's clock. All overdue and due-soon checks use it.

Agents: **Boss**, **Inventory**, **Accounting**, **Facilities**,
**Customer Service** (CS).

### desk — 1 row

| Field | Type | Notes |
|---|---|---|
| `date_today` | TEXT | Shop's "today": 2026-08-31 |
| `notes` | TEXT | Empty |

- **All agents:** the one date every overdue / due-soon judgment is measured against.

### tickets — 3 rows (all `open`)

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | 101, 102, 103 |
| `type` | TEXT | `customer_order`, `rent_notice`, `price_override` |
| `requester` | TEXT | Person or org who raised it |
| `subject` | TEXT | Short title |
| `sku`, `size`, `qty` | TEXT, TEXT, INTEGER | Filled for product tickets (101, 103) |
| `lease_id` | INTEGER → `leases.id` | Filled for the rent ticket (102) |
| `invoice_id` | INTEGER → `invoices.id` | Filled for 101 (links the order to invoice 501) |
| `status` | TEXT | `open` → resolved by the team |
| `notes` | TEXT | The request in plain words |
| `created_at` | TEXT | ISO timestamp with time zone |

- **Boss:** the work queue. Reads each ticket, routes it, and makes the final call.
- **Inventory:** the `sku`/`size`/`qty` fields on order and discount tickets.
- **Accounting:** `invoice_id` and the `price_override` request.
- **Facilities:** `lease_id` on the rent ticket.
- **CS:** `requester` and `notes`, to know who gets a reply and what they asked.

### inventory — 10 rows (4 SKUs × sizes)

| Field | Type | Notes |
|---|---|---|
| `sku` | TEXT (PK with size) | `CC-HOOD-NAVY`, `CC-TEE-WHITE`, `CC-HAT-BLUE`, `CC-MUG-CREST` |
| `name` | TEXT | Product name |
| `size` | TEXT (PK with sku) | S/M/L/XL, or `OS` (one size) |
| `qty` | INTEGER | Units on hand; 82 total |
| `location` | TEXT | Aisle A–D |

- **Inventory:** its main table. Stock by SKU and size, and shortfalls (tee S = 0, hoodie M = 8 of 20 asked).
- **Accounting:** quantities feed the cost of any reprint.
- **CS:** what can actually be promised to a customer.

### pricing — 4 rows

| Field | Type | Notes |
|---|---|---|
| `sku` | TEXT PK | One row per SKU (no per-size pricing) |
| `unit_cost` | REAL | What the shop pays |
| `list_price` | REAL | What the customer pays |

- **Accounting:** margin math for discount requests (hoodie $22 cost, $58 list = 62% margin).
- **Inventory:** what a reprint will cost.
- **Boss:** the margin is what a discount decision rests on.

### vendors — 3 rows

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | 1–3 |
| `name` | TEXT | Bulldog Print Co, Elm City Gifts, QuickShip CT |
| `specialty` | TEXT | Free text; the only link between a vendor and what it makes |
| `lead_days` | INTEGER | 5, 3, 1. The rule for when a restock can arrive |

- **Inventory:** who can restock what, and how long it takes (Bulldog Print Co: apparel, 5 days).
- **Accounting:** whether a vendor is blocked by an unpaid invoice.

### invoices — 1 row

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | 501 |
| `vendor_id` | INTEGER → `vendors.id` | 1 (Bulldog Print Co) |
| `amount` | REAL | $840.00 |
| `due_date` | TEXT | 2026-08-28 → **3 days overdue** |
| `status` | TEXT | `open` |
| `description` | TEXT | "Rush reprint CC-TEE-WHITE S" |

- **Accounting:** bills to pay. Invoice 501 is overdue and blocks Bulldog Print Co from shipping.
- **Inventory:** an open overdue invoice means that vendor can't restock.

### leases — 1 row

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | 1 |
| `space_name` | TEXT | Chapel Street shop |
| `landlord` | TEXT | Elm City Properties |
| `monthly_rent` | REAL | $2,400.00 |
| `next_due` | TEXT | 2026-09-02 → due in **2 days** |
| `notes` | TEXT | Empty |

- **Facilities:** its main table. Rent amount, due date, and landlord.
- **Accounting:** rent is the biggest cash commitment.

### cash_accounts — 1 row

| Field | Type | Notes |
|---|---|---|
| `name` | TEXT PK | `checking` |
| `balance` | REAL | $3,400.00 |
| `date` | TEXT | 2026-08-31 |

- **Accounting:** the hard limit. A payment that would go below $0 must be refused.
- **Boss:** the budget every payment decision competes for.

### payments — 0 rows

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `kind` | TEXT | What was paid (e.g. invoice, rent). No fixed list in the data |
| `ref_id` | INTEGER | Points to an invoice or lease depending on `kind`; not a real foreign key |
| `amount` | REAL | |
| `account` | TEXT | Which cash account it came from |
| `paid_at` | TEXT | |
| `approved_by` | TEXT | **Required.** The human who approved it |

- **Accounting:** where an approved payment is recorded.
- **Boss:** proof that a payment happened, and who approved it.

### Data findings that shape later problems

- **The three tickets are linked through cash.** Invoice 501 ($840) + rent
  ($2,400) = $3,240 of the $3,400, leaving **$160**. Twelve hoodies at cost
  would be $264.
- **Both reprints come from one blocked vendor.** Tee S and hoodie M are
  apparel, so both come from Bulldog Print Co, and its invoice 501 is
  overdue. Earliest delivery after paying is 2026-09-05 (5-day lead).
- **There's no SKU → vendor link.** The vendor's `specialty` text is the
  only clue, so the Inventory agent has to match on it.
- **The data has nowhere to record approvals or reprint orders.** No
  approvals table, no purchase-order table. `payments.approved_by` is filled
  only at payment time. Any pending-approval or order record will need a
  new tool or table (P5 "grow the MCP tools").
- **No customer contact fields.** CS drafts messages to the `requester`
  name only, and nothing is sent.
- **The links are clean:** every ticket's SKU/size, invoice, and lease
  exists, and every inventory SKU has a price.

## 2. MCP tools

All agents get their tools from one FastMCP server, `mcp_server/server.py`.
It reads only `data/campus_customs_new.db` and refuses to open the original.
Every value a tool returns is a database value or arithmetic on database
values. A missing SKU, size, or ticket returns an error, never a guess.
"Today" is `desk.date_today`.

P3 adds three tools, all read-only. Write tools (stock changes, payments
with human approval) come in later problems.

| Tool | Agent | Reads | Helps with | Agent–ticket fit |
|---|---|---|---|---|
| `check_stock(sku, size?, qty_needed?)` | Inventory | `inventory` | **101** (tee S), **103** (hoodie M ×20) | Inventory owns the "can we fill it from the shelf?" question. For 101 that's tee S = 0 (shortfall 1), and for 103 it's hoodie M = 8 of 20 (shortfall 12), with S 4 / L 14 / XL 6 as the mixed-size fallback. |
| `price_and_margin(sku, qty, discount_pct)` | Accounting | `pricing`, `cash_accounts` | **103** (bulk discount), plus the cost of a reprint for **101**/**103** | Accounting turns the Yale AI Club's discount request into numbers the Boss can decide on. At list price the hoodie margin is 62.1% ($22 cost, $58 list), so 20 hoodies = $1,160 revenue and $720 profit. Each discount level shows what's left, and 12 replacement hoodies cost $264 at cost against $3,400 cash. |
| `get_ticket(ticket_id)` | Customer Service | `tickets`, `desk`, `invoices`, `vendors`, `leases` | **101**, **102**, **103** (every reply) | CS can only write an honest reply if it sees the same linked facts the team acts on. 101 → invoice 501 to Bulldog Print Co, $840, 3 days overdue (why the tee can't be reprinted yet). 102 → Elm City Properties, $2,400 due 2026-09-02, in 2 days. 103 → the Yale AI Club's 20 × M request. |

Why these three: each one answers the first question its agent has to
settle before the team can act on a ticket. Is it on the shelf (Inventory)?
What does it cost and earn (Accounting)? Who asked for what, and what's
blocking it (CS)?

Gaps left on purpose for later problems:

- **Facilities has no tool yet.** `get_ticket(102)` already shows the lease;
  a rent-payment tool comes with human approval.
- **No tool writes anything yet.** No tool can mark a ticket resolved,
  change stock, or pay, so nothing can go wrong before the plan (P6) and
  approval rules exist.
- **No SKU → vendor tool.** Vendor restock (lead time, blocked by an unpaid
  invoice) needs one; the data has no SKU → vendor link, only
  `vendors.specialty`.

Expected values above come from SQL on the working copy. P4 calls each tool
directly to confirm them.
