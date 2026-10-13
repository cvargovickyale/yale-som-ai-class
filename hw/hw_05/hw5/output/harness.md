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
values. A missing SKU, size, ticket, invoice, or lease returns an error,
never a guess. "Today" is `desk.date_today`.

The server runs two ways from the same file: over stdio for Claude Code
(`.mcp.json`), and over HTTP (`--http`, port 8765) for the backend. Each
agent sees only its own tools; the backend filters the list per agent.

### Tools and the tickets they serve

| Tool | Agent | Reads / writes | Helps with | Agent–ticket fit |
|---|---|---|---|---|
| `list_open_tickets` | Boss | reads `tickets`, `decisions` | 101, 102, 103 | The Boss's queue: all three open tickets, oldest first, with any decision already waiting for approval. |
| `get_ticket` | Boss, Facilities, CS | reads `tickets`, `desk`, `invoices`, `vendors`, `leases`, pending records | 101, 102, 103 | One ticket with its linked records and everything already pending. 101 → invoice 501 to Bulldog Print Co, $840, 3 days overdue. 102 → Elm City Properties, $2,400 due 2026-09-02. 103 → Yale AI Club, 20 × M. |
| `record_decision` | Boss | writes `decisions` (pending) | 101, 102, 103 | The Boss's final call goes in front of the human. The ticket stays open until the human approves. |
| `check_stock` | Inventory | reads `inventory`, `stock_holds` | 101, 103 | Tee S = 0 (101 can't ship from stock). Hoodie M = 8 of 20 (103 is short 12), with S 4 / L 14 / XL 6 as alternatives. Subtracts units already held. |
| `find_vendor` | Inventory | reads `inventory`, `vendors`, `invoices` | 101, 103 | Both reprints are apparel, so Bulldog Print Co (5-day lead time), which is **blocked** by invoice 501. Evidence: its specialty, plus invoice 501 itself names CC-TEE-WHITE S. |
| `reserve_stock` | Inventory | writes `stock_holds` (pending) | 103 | Sets the 8 hoodies in M aside for the Yale AI Club so no other ticket promises them. |
| `request_reprint` | Inventory | writes `reprint_requests` (pending) | 101, 103 | Refused while invoice 501 is unpaid. Once paid: tee S or hoodie M reprint, cost = qty × $8 or $22, earliest arrival 2026-09-05. |
| `price_and_margin` | Accounting | reads `pricing`, `cash_accounts` | 103 | Margin on the bulk discount: 62.1% at list ($22 cost, $58 list). Each discount level shows margin and profit, checked against the 40% floor. |
| `get_cash_and_bills` | Accounting | reads `cash_accounts`, `invoices`, `leases`, `payment_requests` | 101, 102 | Cash $3,400. Invoice 501 ($840, 3 days overdue) + rent ($2,400, due in 2 days) = $3,240, leaving $160. Shows payments already waiting so nothing is counted twice. |
| `propose_payment` | Accounting | writes `payment_requests` (pending) | 101 (invoice 501), 102 (rent) | Creates a payment request for a human to approve. Amount from the database; only the ticket's own bill; refused if cash would go below $0. |
| `get_lease` | Facilities | reads `leases`, `payments`, `payment_requests` | 102 | Lease 1: Chapel Street shop, Elm City Properties, $2,400 due 2026-09-02 (2 days), no past rent payments. |
| `save_draft_message` | Customer Service | writes `message_drafts` (draft) | 101, 102, 103 | Drafts to Tauhid Zaman, Elm City Properties, and the Yale AI Club, only to the ticket's requester. Never sent. |

### Rules the tools enforce (not just the prompts)

| Rule | Enforced by |
|---|---|
| A human approves every payment | No agent has a pay tool. `propose_payment` only creates a pending request. |
| Cash never goes below $0 | `propose_payment` refuses if balance − already-pending − amount < 0, and names the shortfall. |
| A vendor with an open unpaid invoice won't ship | `request_reprint` refuses and names the invoice to pay first. |
| `desk.date_today` is today | Every date calculation reads it; nothing uses the computer's clock for business dates. |
| No real emails | `save_draft_message` only saves drafts, to the ticket's requester. There is no send tool. |
| No duplicate actions | A second payment request for the same bill, a second hold, or a second reprint for the same ticket/SKU/size is refused. |
| Stay on the ticket | `propose_payment` only pays the bill linked to the ticket. |
| Original data untouched | The server refuses to open `campus_customs.db`. Pending work lives in five new tables in the working copy only (`stock_holds`, `reprint_requests`, `payment_requests`, `message_drafts`, `decisions`). A reset removes them. |

**Tested.** P4: the three original tools were called over MCP through
`.mcp.json` and compared with SQL (`output/mcp_smoke.json`): 7 of 7 match,
4 of 4 bad inputs return errors. P5: every new tool and rule was tested on a
throwaway copy of the database (23 of 23 checks, including the cash floor
with the balance lowered to $3,000: rent refused at −$240). The P4 checks
still pass, and the working copy is unchanged.

## 3. Agent team

Five PydanticAI agents, all on `gpt-6-luna` through Portkey, in
`backend/main.py`. Each has its own prompt in `backend/prompts/` (re-read on
every run) and returns a fixed shape from `backend/models.py`.

| Agent | Role (from Christopher's answers in P5) | Tools | Returns |
|---|---|---|---|
| Boss | Reads each ticket first, decides who works on it, interprets the results, and balances business health against customer happiness | `get_ticket`, `list_open_tickets`, `record_decision`, `delegate` | `BossDecision` |
| Inventory | Knows the stock: by size, shortfall vs. the request, which vendor could reprint, lead time | `check_stock`, `find_vendor`, `reserve_stock`, `request_reprint`, `delegate` | `SpecialistReport` |
| Accounting | Sets the lowest acceptable margin, understands the financials, flags bad business decisions, keeps cash to restock, pays overdue bills first | `price_and_margin`, `get_cash_and_bills`, `propose_payment`, `delegate` | `SpecialistReport` |
| Facilities | Handles rent; asks Accounting to note the payment and recommend it to the Boss | `get_lease`, `get_ticket`, `delegate` | `SpecialistReport` |
| Customer Service | Writes to whoever is named in the ticket; friendly and honest; only facts from the database; never overpromises a date | `get_ticket`, `save_draft_message`, `delegate` | `SpecialistReport` |

### Agent loop and delegation

One **agent loop** = one PydanticAI run: the model reads its prompt and the
task, then either calls a tool and gets the result back, or returns its final
answer in its `models.py` shape. `delegate(to_agent, ticket_id, task)` starts
the teammate's loop and returns its report as the tool result, so any agent
can ask any other agent (full connectivity), within these code-enforced
limits:

| Guardrail | Setting | Why |
|---|---|---|
| Delegation depth | 4 hand-offs from the Boss | Christopher's choice. With 5 agents and no repeats, a chain can't be longer anyway, so the two rules back each other up. |
| No ping-pong or loops | Can't delegate to any agent already in the chain | A specialist that needs something from its caller lists it in `questions_for_caller`. The caller answers by delegating again with the answer, so you still get one controlled back-and-forth. |
| Stay on the ticket | Delegation only for the ticket being worked | Keeps one ticket's run from acting on another. |
| One tool call at a time | `parallel_tool_calls = False` | In the first test, parallel hand-offs made two agents do the same work. |
| Shared budget per ticket | 40 model requests, 80 tool calls, 400k tokens | One budget for the whole team on a ticket, so a runaway chain stops. |
| Time limits | 300 s per ticket, 90 s per model call, 60 s per tool | One stuck call fails fast instead of hanging the ticket. |
| Model | `gpt-6-luna`, fixed in code | The assignment allows no other model. Every response's reported model is checked (`gpt-6-luna-global`); anything else fails the run. |

`gpt-6-luna` rejects function tools on the Chat Completions endpoint while
its reasoning is on, so the agents use the Responses API (found in the first
P5 test run).

### First measured run (P5, ticket 102, throwaway database copy)

| Measure | Value |
|---|---|
| Status | ok, 156 s |
| Agent runs | 5: Boss → Facilities → Accounting, Boss → Accounting, Boss → Customer Service |
| Model requests | 18 |
| Tokens | 38,332 in + 4,485 out |
| Tool calls | 13 (4 delegations, 0 refused) |
| Reported model | `gpt-6-luna-global` on every response |
| Result | Rent payment request ($2,400, leaves $1,000) pending approval; draft to Elm City Properties; Boss decision `pay`, pending approval. It flagged that invoice 501 ($840, overdue) belongs to ticket 101 and needs its own request; both together leave $160. |

Seen in that run, to address when planning the tickets (P6): the Boss asked
Accounting a second time after Facilities had already brought Accounting in
(about 4,600 extra tokens), and one Customer Service model call took most of
its 97 seconds.
