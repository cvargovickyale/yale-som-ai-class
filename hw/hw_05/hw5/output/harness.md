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

## 4. Safety: who can do what

The rule behind every row: **agents propose, a human approves, and code
enforces it.** No agent can move money, take stock off the shelf, place a
vendor order, or send a message. Each of those exists only as a pending
record until a human approves it on the dashboard.

Approval is done by four **human tools** on the MCP server
(`approve_payment`, `reject_payment`, `approve_decision`,
`reset_database`). No agent is given them. They are registered only when
the server runs over HTTP for the backend, so Claude Code's stdio
connection (`.mcp.json`) can't call them either. The backend calls them
only from the dashboard's approve/reset routes (section 6), and each call
records the human's name.

All shop facts go through the MCP server. The backend never opens the
database, so there is no side door around these rules.

### Messages (customers, landlord, vendors)

| Action | Who can propose | Who approves | Enforced by |
|---|---|---|---|
| Reply to a customer (101 Tauhid Zaman, 103 Yale AI Club) | Customer Service only (`save_draft_message`) | Human, on the dashboard | No send tool exists. Drafts can only be addressed to the ticket's `requester`. One draft per ticket (a new one replaces the old). |
| Reply to the landlord (102 Elm City Properties) | Customer Service only, same tool | Human | Same: draft only, to the requester. Facilities' prompt forbids contacting the landlord. |
| Contact a vendor | **Nobody.** There is no vendor messaging tool. | n/a | The only vendor-facing actions are a reprint request and an invoice payment, both pending approval (below). |
| What a message may say | CS prompt: facts from tools only, no firm date while an order is pending, no internal details (cash, margins, invoices) | Human reviews every draft | Prompt-level. The human review is the hard stop. |

### Money: business spend

| Action | Who can propose | Who approves | Enforced by |
|---|---|---|---|
| Pay an invoice or rent | Accounting only (`propose_payment`) | Human only: `POST /api/payments/{id}/approve` → `approve_payment` writes `payments.approved_by`, lowers cash, marks the invoice paid or moves rent's next due date. | No agent has a pay tool. The amount comes from the database, not the agent. It must be the ticket's own bill. One pending request per bill. Refused if cash after already-pending payments would go below $0 (tested: $3,000 balance → rent refused at −$240). |
| Order a reprint (vendor spend) | Inventory only (`request_reprint`) | Human | Refused while the vendor has any open unpaid invoice (tested: Bulldog Print Co blocked by invoice 501). Cost = qty × `unit_cost` from the database. One pending request per ticket/SKU/size. |
| Discount (revenue given up) | Accounting recommends; Boss decides | Human approves the Boss's decision | 40% margin floor after discount, in Accounting's prompt (prompt-level). `price_and_margin` reports `below_cost` and the margin so the human sees the numbers. |
| Set stock aside | Inventory only (`reserve_stock`) | Stock leaves the shelf only on human approval | Can't hold more than available (on hand minus other holds). One hold per ticket/SKU/size. `inventory.qty` never changes from an agent. |
| Close a ticket | Boss records a decision (`record_decision`) | Human: `POST /api/decisions/{id}/approve` | The decision is stored as pending and the ticket stays `open` until approved. Approval is refused while the ticket still has payment requests waiting. |
| Execute a payment at approval time | n/a | Human | `approve_payment` re-checks at payment time: the request is still pending, the bill is still open, and cash won't go below $0. Approving twice is refused. |

### Money: token spend (the AI bill)

| Limit | Setting | Enforced by |
|---|---|---|
| Model | `gpt-6-luna` only, fixed in code | No setting can change it. Every response's reported model is checked (`gpt-6-luna-global`); anything else marks the run `wrong_model` and stops it (tested with a stand-in model). |
| Budget per ticket, shared by every agent | 40 model requests, 80 tool calls, 400,000 tokens | PydanticAI `UsageLimits` on one shared usage counter. Delegated runs draw from the same budget. |
| Time | 300 s per ticket, 90 s per model call, 60 s per tool | `asyncio.wait_for`, model timeout, tool timeout. |
| Delegation | At most 4 hand-offs; no agent twice in a chain; same ticket only | `delegate` refuses and tells the agent why (tested: 5 of 5 refusal cases). |
| One tool call at a time | `parallel_tool_calls = False` | Stops parallel hand-offs from duplicating work (seen in P5 testing). |
| Visibility | Tokens, model requests, and tool calls per agent run | `output/audit_trail.json`, plus a one-line cost summary per ticket. |
| Runs | One team run at a time; at most 6 runs per 10 minutes | Checked in `POST /api/tickets/{id}/run` *before* any agent starts (409 if busy, 429 over the limit). |
| Fresh responses | `x-portkey-cache-force-refresh: true` | A Portkey cache hit returned tool-call IDs Azure rejects, which broke a rerun (P7). Fresh responses also mean the audit shows real, current model output. |

Measured so far: one ticket (102) cost 18 model requests and 42,817 tokens
in total, about 11% of the per-ticket token budget.

### Data

| Risk | Guardrail |
|---|---|
| Damaging the original data | The MCP server refuses to open `campus_customs.db`. All work goes to `campus_customs_new.db`, and a reset copies the original back. |
| Made-up facts | Every number comes from a tool. Missing records return an error that lists the valid options; prompts tell agents to report "unknown" rather than estimate. |
| A shop path around MCP | The backend has no database access (checked: no `sqlite` or `.db` references in `backend/`). |

## 5. Audit trail

`output/audit_trail.json` is append-only. It is never wiped by the code. A
reset of the database does not touch it.

- **Every agent appends its own `agent_run` entry** the moment its loop
  ends, whether it succeeded, errored, hit a limit, or was cut off by the
  ticket timeout. A crash mid-ticket still leaves a record of every agent
  that ran.
- Each entry records:
  - `run_id`, `parent_run_id`, and `chain` (who asked whom)
  - the task it was given
  - every tool call with its arguments, a shortened result, and a status
    of ok / error / refused
  - the model name on every response, model requests, tokens in and out,
    duration, status, and its final output
- After the Boss finishes, a **`ticket_run` summary** is appended. It has
  the Boss's decision, totals, and the `run_id`s of its agent entries.
- Every human action from the dashboard (approve or reject a payment,
  approve a decision, reset) appends a **`human_action`** entry with who
  did it and the result (e.g. balance before and after).
- Writes are atomic: a temp file, then a rename. A lock serializes
  concurrent writes. If the file is ever unreadable, it is moved aside, not
  overwritten.
- Tested without spending tokens: a scripted stand-in model drove Boss →
  Facilities through the real loop and MCP server. Each agent appended its
  own entry, a second run appended (3 → 6 entries), and a corrupt file was
  moved aside.
- The P5 live test of ticket 102 ran on a throwaway database copy, so its
  log was kept out of this file. P7's route tests on the working copy
  are in it: two failed runs (the bugs in section 6) and two ok runs of
  ticket 102, plus a payment approval, a decision approval, and two
  resets. The database was reset afterward; the audit was kept.

## 6. Backend routes (FastAPI)

`backend/main.py`. Start from `backend/` with
`../.venv/bin/uvicorn main:app --reload --port 8000` (MCP server running
first). Every route reads and writes through the MCP server. The backend
has no database access of its own.

| Method and URL | What it does | MCP tool(s) |
|---|---|---|
| `GET /api/health` | Backend is up, which model is fixed (`gpt-6-luna`), MCP URL, shop date | `get_board` |
| `GET /api/tickets` | All three tickets with status (**open** / **resolved**), the team's records for each (payment and reprint requests, holds, drafts, decisions), cash, payments made, open/resolved counts, and each ticket's latest run | `get_board` |
| `GET /api/tickets/{ticket_id}` | One ticket with its linked invoice or lease and its pending records | `get_ticket` |
| `POST /api/tickets/{ticket_id}/run` | Start the agent team on the ticket (Boss first). Returns `202` at once; the run continues in the background. Refused if the ticket isn't open, a run is already going (`409`), or over 6 runs per 10 minutes (`429`). | `get_ticket`, then the agents' tools |
| `GET /api/runs` | Latest run per ticket: running / ok / error, duration, totals (requests, tokens, tool calls, delegations), the Boss's decision | none (in memory) |
| `GET /api/events?since={seq}` | Recent events, oldest first, for keeping the board current: run started/finished, agent started/finished (tokens, recommendation), each tool call and result, each delegation, approvals, resets. Poll with the last `seq` you saw. | none (in memory; the audit file is the permanent record) |
| `GET /api/cash` | Checking balance from `cash_accounts`, payments waiting for approval, cash after them, open invoices, upcoming rent | `get_cash_and_bills` |
| `POST /api/payments/{payment_request_id}/approve` | Human clicks Approve: **executes** the payment. Body `{"approved_by": "name"}`. Writes `payments`, lowers cash, marks the invoice paid or moves rent's next due date forward a month. | `approve_payment` |
| `POST /api/payments/{payment_request_id}/reject` | Human rejects a payment request; no money moves. Body `{"rejected_by": "name", "reason": "…"}` | `reject_payment` |
| `POST /api/decisions/{decision_id}/approve` | Human approves the Boss's decision: ticket → **resolved**, held stock leaves the shelf, drafts → approved (never sent). Refused while payments are still waiting. | `approve_decision` |
| `POST /api/reset` | Reset the working database to the original for a fresh run. Body `{"confirm": true}`. Refused during a run. Keeps the audit trail. | `reset_database` |

Errors: a tool's refusal comes back as `409` with the tool's own message
(e.g. "Cash can't go below $0"), and a missing record as `404`. If the MCP
server isn't running, every route returns `503`.

### Tested (P7, working copy, then reset)

| Check | Result |
|---|---|
| Read routes | Tickets 101/102/103 open, 3 open / 0 resolved, checking $3,400, no pending payments |
| Bad requests | Unknown payment, decision, or ticket → 404; blank approver → 422; reset without confirm → 409 |
| One run at a time | A second run while 102 was running → 409 |
| Run ticket 102 via the API | ok, 87 s, 5 agent runs, 18 model requests, 39,128 + 3,946 tokens; payment request #1 (rent $2,400) pending, cash after pending $1,000; landlord draft; decision `pay` |
| Approve the decision first | Refused: "Ticket 102 still has payment requests waiting: [1]" |
| Approve the payment | Cash $3,400 → **$1,000**; `payments` row with `approved_by = Christopher`, paid 2026-08-31; lease next due 2026-09-02 → 2026-10-02 |
| Approve it again | Refused: already paid |
| Approve the decision | Ticket 102 → **resolved** (1 resolved, 2 open); draft → approved, not sent |
| Audit | Every agent run, ticket summary, and human action appended |
| Reset | All 9 original tables match the original row for row, and the 5 work tables are gone |

### Bugs the route tests found (fixed)

1. **The live-event hook crashed a run.** It read a field this PydanticAI
   version doesn't have. Fixed, and the hook now swallows its own errors,
   so the board's feed can never stop an agent.
2. **A Portkey cache hit broke the rerun.** The rerun's first request was
   identical, so Portkey served it from cache, with tool-call IDs that Azure
   rejects. Fixed by forcing fresh responses. Without this, every rerun
   after a reset would have failed (the P9 workflow).
3. **Accounting wouldn't propose rent while invoice 501 was unpaid.** It
   read "pay overdue things first" as a block, and 501 belongs to ticket
   101. Its prompt now says "first" means first in line: count unpaid
   overdue bills as spoken for, then propose this bill if cash still covers
   it.
