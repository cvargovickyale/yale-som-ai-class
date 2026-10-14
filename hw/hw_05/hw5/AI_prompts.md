# Homework 5 AI Prompts

Records the prompt used for each problem, plus at most one follow-up when a
correction or clarification was needed. Each prompt is typed in my own words,
one problem at a time. Other decisions made while working a problem are
recorded in that problem's notes. Coding assistant: Claude Code.

## Problem 2 — Study the Campus Customs database

**Prompt:** P2 study the database and set up the working copy
data/campus_customs_new.db - later problems will update this. we already
looked through the db. start a new harness.md in output that lists fields and
one line on why the table matters for each agent (if it does)

**Follow-up prompt used:** none.

**Notes:**

- No LLM was used. The database was studied with direct SQL (`sqlite3`),
  opened read-only.
- Placed the data at `hw5/data/` and made the working copy
  `campus_customs_new.db` as a byte-for-byte copy of `campus_customs.db`
  (same SHA-1). Both files are committed, per the submission rules; only
  SQLite's temporary `-journal`/`-wal`/`-shm` files are gitignored.
- Started `output/harness.md`. Section 1 (Data) lists every table and field
  and says why each table matters to each agent.
- Findings that shape later problems:
  - Today is `desk.date_today` = 2026-08-31. Cash is $3,400 in checking.
    No payments yet.
  - Invoice 501 ($840, Bulldog Print Co) is 3 days overdue, so that vendor
    can't ship. Rent ($2,400) is due in 2 days. Paying both leaves $160.
  - Ticket 101 needs a tee in S (0 in stock). Ticket 103 wants 20 hoodies
    in M (8 in stock, 12 short; 12 × $22 = $264). Both reprints are apparel
    from the blocked vendor (5-day lead time).
  - There's no SKU → vendor link (only the `specialty` text), and no table
    for pending approvals or reprint orders. Those will need new tools in P5.
  - The links are clean: every ticket's SKU/size, invoice, and lease exists.

## Problem 3 — Build the MCP server

**Prompt:** P3 needs an MCP server in mcp_server/ with FastMCP that will talk
to the database. do not connect it or run it yet. all agents will use tools
in this MCP. more tools will be added but for now we need three tools with
clear names, no invented data, and only info from the db.

My suggestions are inventory, accountant, customer service. inventory is the
db pro to check and update the db. accountant notes cost and stuff. customer
service replies nicely to users/requestors

harness.md should have a new section about MCP tools with these three that
shows what table each reads, which ticket it helps with, and a sentence on
agent-ticket fit. to get a high score you need to tie the tool to the ticket
without being vague. mcp_server/README.md should explain what the MCP server
is for, the tools, and the db it references

**Follow-up prompt used:** none.

**Notes:**

- Built `mcp_server/server.py` with FastMCP 4.1.0 (checked against the
  installed package's API before writing). One tool per suggested role,
  named for what it does:
  - `check_stock` (Inventory)
  - `price_and_margin` (Accounting)
  - `get_ticket` (Customer Service)
- **Decision: all three tools are read-only for now.** Inventory will
  "update the db" once a write tool exists, but no write should happen
  before the ticket plan (P6) and the approval rules. Each tool opens the
  database read-only and is marked read-only in its MCP description.
- **No invented data:** a missing SKU, size, or ticket returns an error that
  lists the valid options, not a guessed value. Margins and days overdue
  are arithmetic on database values, and dates use `desk.date_today`, not
  the computer's clock.
- The server only uses `data/campus_customs_new.db` and refuses to open the
  original `campus_customs.db`.
- Customer Service's tool reads the facts a reply needs (the requester, the
  request, the linked invoice or lease). The friendly wording is the CS
  agent's job in P5; there's no send tool.
- Not connected or run, as asked. The only check was that it imports and
  registers three tools with the expected inputs. P4 calls each tool.
- Also added `hw5/requirements.txt` (`fastmcp`), `hw5/.env.example`
  (placeholders only; the model is fixed to `gpt-6-luna` in code, so there's
  no model setting), and `mcp_server/README.md`.

## Problem 4 — Add the MCP server to the vibe coder and test each tool

**Prompt:** P4 add the MCP server to claude code and test each tool. what does
it mean add to this project. the connection should be saved in .mcp.json at
project root - is that how you save things?

Then test each tool, evidence goes in mcp_smoke.json, including the prompt -
ok it wants me to run the test for each tool. I think I should ask the
project to call the mcp server and ask what tools are returned , how they
should be used and the tool output (that matches the new db) - let me know
when you're ready and I'll ask about each tool individually to kick off the
tests

**Follow-up prompt used:** I don't want to do that. you test them.

**Per-tool test requests.** These are the questions I planned to ask
about each tool. After my follow-up, Claude Code ran them for me; I did not
type them. Each one matches an entry in `output/mcp_smoke.json`.

| # | Tool | Test request | Arguments sent |
|---|---|---|---|
| 0 | (all) | Call the campus-customs MCP server: which tools does it return, and how should each be used? | `list_tools` |
| 1 | `check_stock` | Ticket 101: can we fill 1 white tee in size S from stock? Show the output and check it against the new db. | `sku=CC-TEE-WHITE, size=S, qty_needed=1` |
| 2 | `check_stock` | Ticket 103: can we fill 20 navy hoodies in size M? What's the shortfall, and what other sizes are on hand? | `sku=CC-HOOD-NAVY, size=M, qty_needed=20` |
| 3 | `price_and_margin` | Ticket 103: what are the cost, revenue, profit, and margin for 20 hoodies at list price, and how much cash do we have? | `sku=CC-HOOD-NAVY, qty=20, discount_pct=0` |
| 4 | `price_and_margin` | Ticket 103: what would reprinting the 12-hoodie shortfall cost? | `sku=CC-HOOD-NAVY, qty=12, discount_pct=0` |
| 5 | `get_ticket` | Ticket 101: who asked, and what record is linked to it? | `ticket_id=101` |
| 6 | `get_ticket` | Ticket 102: who asked, and when is the rent due? | `ticket_id=102` |
| 7 | `get_ticket` | Ticket 103: who asked, and is anything linked? | `ticket_id=103` |
| 8 | all three | Bad inputs (unknown SKU, size XXL, ticket 999): does each tool return an error instead of making something up? | `CC-NOPE`, `XXL`, `999` |

**Notes:**

- "Add to this project" means a project-scoped MCP server: Claude Code reads
  `.mcp.json` in the folder a session is opened in, starts the server
  itself, and its tools show up for the assistant to call. Saved as
  `hw5/.mcp.json` (stdio: `.venv/bin/python mcp_server/server.py`, relative
  paths so it works in any clone of `hw5/`).
- Checked that the config launches and connects over MCP with FastMCP's
  client (it lists the 3 tools). No tool was called in that check. Turned
  off FastMCP's startup banner.
- Claude Code only loads `.mcp.json` when a session starts in that folder.
  Rather than open a new session, Claude Code ran the tests from this
  session: it launched the server from `hw5/.mcp.json` over stdio and called
  every tool through the MCP protocol (FastMCP's client). It's the same
  server and config Claude Code uses, with no LLM involved.
- `output/mcp_smoke.json` records, for each call, the arguments, the raw
  tool output, an independent SQL query's answer, and whether they match:
  - **7 of 7 calls match the database.** Tee S: 0 on hand, short 1. Hoodie
    M: 8 on hand, short 12. 20 hoodies at list: 62.1% margin, $720 profit;
    12-hoodie reprint costs $264. Ticket 101 → invoice 501, Bulldog Print
    Co, $840, 3 days overdue. Ticket 102 → $2,400 rent due 2026-09-02, in
    2 days. Ticket 103 → nothing linked.
  - **4 of 4 bad inputs return errors, not invented data:** unknown SKU
    (twice), size XXL, ticket 999.
  - **The working database was not changed** (same SHA-1 before and after).
- The test script is kept outside the submission (`hw/hw_05/mcp_smoke_test.py`)
  so it can be rerun when P5 adds tools.

## Problem 5 — Build the agent team and grow the MCP tools

**Prompt:** p5: the agent team needs to use PydanticAI: I'm confused why this
lists agents when I thought I chose three agents before. was I supposed to
pick from a list?

now they say boss, accounting, facilities, customer service, inventory.

add prompts, models, and agent loops (explain to me what this means) so they
can talk to each other and delegate (reference the rules we talked about)

prompts go in backend/prompts/ with each agent getting its own file. data
types go in backend/models.py and agent files go in backend. they are strict
about only gpt-6-luna, make sure old refs to 5.6 are updated. I want to write
prompts for each in my own words but I need some leading questions. can you
do a popup quiz thing where I can explain what role each agent should have in
the workflows and therefore what tools they need. they say more detailed
prompts that cover many or all aspects of the agents work and scope will
score higher, help me get there

**Follow-up prompt used (my answers to the role quiz):**

- Boss tools: get_ticket, list_open_tickets, record_decision, delegate
- Inventory tools: check_stock, find_vendor, reserve_stock, request_reprint, delegate
- Accounting tools: price_and_margin, get_cash_and_bills, propose_payment, delegate
- Facilities tools: get_lease, get_ticket, delegate
- CS tools: get_ticket, save_draft_message, delegate
- Boss role: The boss should be the first to read the ticket, decide which
  tools to use to solve the problems, and interpret what comes back. like if
  accounting gives number figures on different outcomes, it gives a
  recommendation to balance those against business health and customer
  happiness.
- Boss limits: boss shouldn't make payments or send things to customers
  without approval. ticket is done when user approves.
- Inventory role: inventory knows everything about db and can answer stock by
  size, how many more people would need versus what's in stock, which vendor
  could reprint, lead time
- Inventory limits: delivery date is promised by lead days plus current day,
  can't order from blcoked vendor. other tools need to be clear that there
  aren't pending changes to the db.
- Accounting role: Accounting needs to decide lowest acceptable margin when
  offering discounts, understand the financials and flag anything that's a
  bad business decision, keep enough cash to order inventory, and pay overdue
  things first.
- Accounting limits: if cash would go below zero they can't recommend a
  transaction and must explain an alternative. and they're never approving a
  transaction, human does.
- Facilities role: asks accounting to note the payment and recommend to the
  boss, facilities deals with rent. I think this is the simplest agent.
- CS role: whoever is referenced in ticket, friendly and honest tone, every
  message must include only facts from db and nothing made up, and not
  overpromise delivery dates.
- Delegation depth: 4
- Team rules: no real emails, no ping ponging (but could we allow one back
  and forth? why or why not?),

**Notes:**

- **Five agents, not three:** the five agents were set by the scenario. In
  P3 I picked three *tools*, one for each of the roles I suggested.
- **Prompts** (`backend/prompts/*.md`): each one is built around my quiz
  answers. Claude added the structure (role, how to work, limits, delegation
  rules, what to return) and the rules from the kickoff quiz.
- **Margin floor (decision): 40% after discount.** It's written into
  `accounting.md` as the shop's floor. I said Accounting decides the lowest
  acceptable margin; 40% is the default number until I change it.
- **Models** (`backend/models.py`): agents return fixed shapes, not prose.
  Specialists return `SpecialistReport` (findings with numbers, actions
  taken, pending IDs, recommendation, blocked items, `questions_for_caller`).
  The Boss returns `BossDecision` (outcome, summary, reasoning, pending IDs,
  risks). Audit records are `AgentRunRecord` and `TicketRun`.
- **Agent loops** (`backend/main.py`, which holds all five agents to match
  the required tree): one PydanticAI run per agent. `delegate` starts the
  teammate's loop and returns its report.
- **Guardrails enforced in code:**
  - depth 4
  - no hand-off to any agent already in the chain
  - stay on the ticket
  - one tool call at a time
  - a shared budget per ticket (40 requests, 80 tool calls, 400k tokens)
  - time limits of 300 s per ticket, 90 s per model call, 60 s per tool
- **One back-and-forth (my question):** allowed, but only through the
  caller. A specialist can't hand work back up the chain (that's what loops
  forever). Instead it lists what it needs in `questions_for_caller`, and
  the caller delegates again with the answer. Each round is visible in the
  audit trail and counts against the same budget.
- **Grew the MCP tools from 3 to 12** to match my picks:
  - New read tools: `list_open_tickets`, `find_vendor`,
    `get_cash_and_bills`, `get_lease`. `check_stock` and `get_ticket` now
    also show holds and other pending work.
  - New write tools: `record_decision`, `reserve_stock`, `request_reprint`,
    `propose_payment`, `save_draft_message`. They only create *pending*
    records in five new tables in the working copy. Nothing moves money or
    stock, and nothing is sent.
- **Rules in the tools, not just the prompts:**
  - no payment without human approval (no agent has a pay tool)
  - cash can't go below $0
  - a blocked vendor (any open unpaid invoice) can't take a reprint order
  - no duplicate payments, holds, or reprints
  - drafts go only to the ticket's requester
  - a payment can only be for the ticket's own bill
- **gpt-6-luna only:** the model name is fixed in code with no override, and
  the audit checks every response's reported model (`gpt-6-luna-global`).
  Updated the old `gpt-5.6-luna` defaults in the workspace guide files
  (`CLAUDE.md`, `AGENTS.md`, `AI_HANDOFF.md`). `hw5/` never referenced 5.6.
- **Problems found while testing:**
  - `gpt-6-luna` rejects tools on Chat Completions while its reasoning is
    on, so the agents use the Responses API.
  - The first live run hit the 300-second limit after the Customer Service
    draft, with no record of which call hung. Added per-call time limits and
    logging for runs that get cut off.
  - On ticket 102 (rent), Accounting also proposed paying invoice 501, which
    belongs to ticket 101, so I added the ticket-link rule.
  - Parallel hand-offs had two agents doing the same work, so tool calls now
    run one at a time.
- **Verified:**
  - 23 of 23 rule checks on a throwaway database copy
  - 5 of 5 delegation refusals with no model calls (self, ping-pong, loop,
    wrong ticket, depth)
  - P4 tool checks still 7/7 and 4/4
  - one live run of ticket 102 on a throwaway copy: ok, 156 s, 18 model
    requests, 38,332 + 4,485 tokens, every response `gpt-6-luna-global`
  - the working copy is unchanged (same SHA-1 as the original)

## Problem 5, part 2 — Tools in MCP, audit trail, harness safety, README

**Prompt:** important second part of P5: add the agents' tools to MCP server
if you haven't already. facts come from the new db, there should be no shop
layer that bypasses MCP. all agents should append to
output/audit_trail.json . keep appending to it, don't wipe unless you're sure
you need to. harness.md needs to be updated with each tool and the table
used, as well as safety section that shows guardrails on who can approve
messages that go to customers vendors and that affect money - either business
spend or token spend limits. the README.md should be updated as well with
these changes. you may have done most of these

**Follow-up prompt used:** none.

**Notes:**

- **Already done in part 1:** all 12 agent tools live in the MCP server,
  and the backend never opens the database (checked: no `sqlite` or `.db`
  references in `backend/`). `delegate` is the only tool outside MCP. It
  passes work between agents and reads no shop data.
- **Audit trail changed: every agent now appends its own entry** to
  `output/audit_trail.json` the moment its loop ends, including errors,
  limit hits, and timeouts. Before, the whole ticket was written once at
  the end, so a crash lost every agent's record. A `ticket_run` summary
  follows the agent entries and lists their `run_id`s. The file is never
  wiped:
  - writes are atomic and locked
  - an unreadable file is moved aside, never overwritten
  - a database reset doesn't touch it
- **Tested without spending tokens:** a scripted stand-in model drove
  Boss → Facilities through the real loop and MCP server (throwaway
  database):
  - each agent appended its own entry
  - a second run appended (3 → 6 entries)
  - a corrupt file was moved aside
  - the stand-in model was flagged `wrong_model`, which proves the
    gpt-6-luna check catches any other model
- `output/audit_trail.json` starts empty (`[]`). The P5 live test ran on a
  throwaway database copy, so its log stays out of this file. Real runs
  start in P9.
- `harness.md`: section 2 lists every tool with the tables it reads or
  writes. New section 4 (Safety) covers:
  - who can propose and who approves messages to customers, the landlord,
    and vendors (there is no vendor messaging tool at all)
  - business spend: payments, reprints, discounts, stock holds, closing a
    ticket
  - token spend: fixed model, a shared per-ticket budget, time limits,
    delegation limits
  - each row says whether code or a prompt enforces it

  New section 5 describes the audit trail.
- Wrote `hw5/README.md`: setup, reset, start MCP, start the backend (CLI
  until P7's routes), the board (P8), reset before a full three-ticket run,
  and what agents can do vs. what only a human can approve.

## Problem 6 — Plan the three tickets

**Prompt:** p6 we are writing what we expect to happen in
output/desk_tickets.html that has one tab per ticket. it can simply visualize
(in the expected section, differen thtan actual section we will build later)
the main steps

101: Boss should call first: Inventory - to see that we don't have that in
stock. get inventory tool. then accounting to pay overdue invoice. suggest
payment tool then customer service to get a response to customer. draft
response tool.

102: Boss should call facilities first. rent info tool. then accounting.
suggest payment tool.

103: Boss should call inventory first. get inventory tool. and see when we
could get things in stock. accounting tool is asked to see what maximum
allowable discount would be. boss suggests override to user. customer service
drafts two approaches to either offer other sizes for a medium discount or
wait for a bigger discount on all mediums.

turn this into expected flows. we also need empty cash and reflection tabs for
later

**Follow-up prompt used:** add the routing line, yes landlord draft if you recommend, flag option B

**Notes:**

- Built `output/desk_tickets.html`, a Gateway 2000-style window with five
  tabs: Ticket 101, Ticket 102, Ticket 103, Cash, Reflection.
  - Each ticket tab has the ticket facts from the database, an **Expected
    flow** (my steps as numbered agent → tool → expected result, with real
    tool names and numbers), "Waiting for the human", "Watch for", and an
    empty **Actual** section for after the run.
  - Cash and Reflection are empty placeholders.
- Expected numbers come from SQL on the working copy and from the tools'
  arithmetic:
  - **101:** tee S 0 on hand. Invoice 501 is $840, 3 days overdue; cash
    $3,400 → $2,560.
  - **102:** $2,400 rent due 2026-09-02; cash → $160 after both payments.
  - **103:** 8 of 20 M on hand, short 12; Bulldog Print Co blocked by 501.
- **Correction:** at the 40% margin floor, the lowest hoodie price is
  $22 ÷ 0.6 = $36.67, so at most **36.8% off**. In P5 Claude told me about
  34% ($38.33), which was wrong. The 103 tab shows the margin table at 0,
  10, 20, 30, and 36.8% off.
- Things the plan surfaced for the run (in each tab's "Watch for"):
  - **102:** Facilities brings in Accounting, so the Boss shouldn't ask
    Accounting again. In the P5 test it did, costing about 4,600 tokens.
  - **102:** no landlord draft is planned, but the Boss's prompt currently
    asks for a draft on every ticket.
  - **103, Option B:** a 12-hoodie reprint costs $264, but only $160 is left
    after 101's and 102's payments, and the vendor is blocked until invoice
    501 is paid.
  - **103:** one draft per ticket, so both options go in one message.
- Checked: all five tabs switch correctly, with no script errors and no
  sideways overflow at 1280 px or 375 px. The 103 discount table overflowed
  on mobile, so it now scrolls inside its box.
- **After my follow-up:**
  - **Boss prompt:** rent goes through Facilities only, and the Boss
    doesn't ask Accounting itself. Before delegating, it checks `pending`
    and the reports it already has. Every ticket gets a draft, including a
    short acknowledgment to the landlord that never says a payment was
    made. An option that depends on spending cash may not cover must be
    listed under `risks` with the numbers.
  - **Accounting prompt:** check every option that needs a reprint against
    `cash_after_pending`, and flag a shortfall with both numbers.
  - **Plan page:** 102 now has a step 4, a landlord acknowledgment draft
    that doesn't say the rent is paid. 103's Option B is marked
    **flagged**: reprint $264 vs. $160 left, short $104, and blocked until
    invoice 501 is paid.
  - All 10 views still render with no sideways overflow.

## Problem 7 — Backend routes

**Prompt:** P7: p8 react frontend dashboard needs a backend main.py using
fastapi with routes that do these things:
show all three tickets and whether each has been resolved or is open
use ticket id and run agent team on that ticekt
keep track of recent agent events and what tools they use to keep board
current
approve a payment once the human clicks approve and change cash - execute it.
show current checking bal from cash_accounts
reset db to original when we want to try fresh run

then start backend/ with uvicorn main:app --reload --port 8000

to turn on localhost:8000. harness.md needs to list each route by url and
what does

**Follow-up prompt used:** none.

**Notes:**

- **Routes** in `backend/main.py` (FastAPI):
  - `GET /api/tickets` (open/resolved)
  - `POST /api/tickets/{id}/run` (runs the team in the background)
  - `GET /api/events` and `GET /api/runs` (live board feed)
  - `GET /api/cash` (checking balance)
  - `POST /api/payments/{id}/approve` (executes the payment) and
    `POST /api/payments/{id}/reject`
  - `POST /api/decisions/{id}/approve` (resolves the ticket)
  - `POST /api/reset`
  - `GET /api/health`, `GET /api/tickets/{id}`

  Each route is listed with its URL, what it does, and the MCP tool it uses
  in `harness.md` section 6.
- **Still no shop layer around MCP:** approving a payment, approving a
  decision, and resetting the database are MCP tools too (`approve_payment`,
  `reject_payment`, `approve_decision`, `reset_database`), plus a read-only
  `get_board`. No agent is given them, and the human tools are registered
  only in `--http` mode, so Claude Code's stdio connection can't approve a
  payment.
- **"Execute it":** approving a payment re-checks status and cash at that
  moment, writes `payments` with `approved_by`, lowers
  `cash_accounts.balance`, and marks the invoice paid (unblocking the
  vendor) or moves rent's next due date forward a month, all in one
  transaction.
- **Decision added:** a ticket becomes "resolved" only when the human
  approves the Boss's decision, and that's refused while the ticket still
  has payments waiting.
- **Token-spend guard on the run route:** one team run at a time and at
  most 6 runs per 10 minutes, checked before any agent starts.
- **Live events:** a PydanticAI event hook records every tool call, tool
  result, delegation, and agent start/finish as it happens. Approvals and
  resets also go into the audit trail as `human_action` entries.
- **Port:** a Lecture 13 backend from another session was already on port
  8000, so the test servers ran on 8010 (`.claude/launch.json`: `hw5-mcp`,
  `hw5-backend`). The README and the assignment's command still use 8000.
- **Bugs the tests found, all fixed:**
  1. The event hook used a field this PydanticAI version doesn't have, and
     it crashed a run. The hook now can't stop an agent.
  2. A Portkey cache hit on the rerun returned tool-call IDs that Azure
     rejects. Every request now forces a fresh response; without this,
     every rerun after a reset would fail.
  3. Accounting refused to propose rent while invoice 501 (ticket 101's
     bill) was unpaid. Its prompt now says "pay overdue first" means first
     in line, not a block. This is my clarification of my own P5 rule.
- **Tested on the working copy:**
  - Ticket 102 run through the API: ok, 87 s, 18 model requests,
    39,128 + 3,946 tokens, rent request pending, cash after pending $1,000.
  - Approving the decision before the payment was refused.
  - Approving the payment took cash from $3,400 to $1,000 and moved the
    lease's next due to 2026-10-02. Approving it again was refused.
  - Approving the decision resolved ticket 102.
  - Resetting brought all 9 tables back to the original, row for row.
  - The audit trail keeps every entry.
- After a reset through the API, the working copy's contents match the
  original exactly, but its SHA-1 doesn't (SQLite's backup writes its own
  file header). "Same as original" is now checked table by table.

## Problem 8 — Agent dashboard

**Prompt:** when p7 resolved, p8 will build frontend/ dashboard w react and
vite and typescript. page needs to call p7 routes. you know what board
should have, but here are tips: let you pick which ticket to start with.
show agents and their feeds, ticket status, summary of what agent did on
each ticket, have approval for payment, have prominent checking balance that
stays updated. make it spread out and a little more minimalist than the dense
views we've created before. should look calm and inviting, not overwhelming.
use popups as needed that people can click on for more info. you really can
shut down the lecture 13 stuff and use 8000, but keep with whatever you got
if it's easier. the backend needs to allow vite localhost 5173 or whatever.
board shoudl start with npm run dev to open react desk in browser so I can
try it out. design.md should contain my guidance and more on final deciisons
of dashboard look and how resolved tickets and cash shows up. focus on the
creativity and help people enjoy using it like tickets having a satisfying
closed animation that turns them green and pushes them into a done pile :)

**Follow-up prompt used:** none.

**Notes:**

- **Ports:** stopped the Lecture 13 backend (8000) and frontend (5173),
  with my OK. The HW5 backend now runs on 8000 and the board on 5173. The
  backend allows `localhost:5173` (CORS), and the board also proxies
  `/api` through Vite. `npm run dev` opens the board in the browser.
- **`frontend/`** is React 19 + Vite 8 + TypeScript, the same stack as
  HW4. It has:
  - a big live **checking balance** that counts down when a payment is
    approved
  - **On the desk** tickets with **Start the team** (pick any ticket)
  - **The team**: five agents with live feeds and a popup per agent
  - a **Review** popup with the Boss's call, risks, **Approve / Reject**
    for payments, the draft, and what each agent did
  - **Approve and close ticket**, which runs the closing animation (green
    wash → check stamp → flies → lands in a tilted **Done** pile)
  - **Reset**, **How it works**, and **Recent activity**
- **Style decision:** calm paper-and-card, not Gateway 2000, per my
  "calmer, less dense" ask. One accent (Yale blue); green only for
  done/paid; amber only for money warnings. Full reasoning in
  `output/design.md`.
- **Backend additions for the board:** `GET /api/tickets/{id}/history`
  (what each agent did, read from the audit trail since the last reset, so
  it survives a restart).
- **Model retries:** while testing, Azure intermittently rejected about 1
  in 3 gpt-6-luna calls (`401 Jwt verification fails`) and once returned a
  5xx, ending team runs. Model requests now retry up to 3 times with
  backoff, on temporary errors only and only before any reply streams, so
  nothing is ever done twice. The first version missed streamed requests
  (the live feed makes runs stream); fixed and tested with a fake provider.
- **Bugs found and fixed while testing:**
  - The feed showed duplicate events, because two overlapping polls
    fetched the same events. They're now kept once by sequence number.
  - At 375 px the single-column grid overflowed sideways.
- **An unplanned run:** Claude's layout-check script clicked the first
  ticket's main button, which was **Start the team** on 102 once 101 was
  done. That started one real run of ticket 102 (ok, 41,413 tokens). The
  run guard refused the script's next clicks. The rent request it created
  was **not** approved, and the desk was reset afterward. Later checks use
  read-only clicks only.
- **Verified live in the browser:**
  1. Ran 101: ok in 81 s; "2 need you"; the Boss suggested "waiting."
  2. Approved the $840: balance $3,400 → $2,560, with a −$840 chip.
  3. Closed the ticket: animation sequence confirmed frame by frame;
     landed in Done.
  4. Reset → $3,400, three open, empty pile, all 9 tables match the
     original.
  5. Width sweep 320–1440 px: no overflow, popup fits, Esc closes it,
     real mouse clicks work.
  6. `npm run build` is clean.

## Problem 9 — Resolve the tickets

**Prompt:** p9: reset the db to start fresh. note starting $$. then run all
three tickets until each is resolved. then output/desk_tickets.html from p6
should populate the "actual" section from this real run (PLEASE WAIT FOR ME
TO DO THIS ALONGSIDE YOU AND PLAY THE HUMAN ROLE OF APPROVER ) - which agents
worked and how they delegated and what tools used. this should be next to or
somehow comparable the expected section we wrote earlier

On cash tab that we kept - itemize the money spent on each step of each
ticket, starting with the checking balance start, then ending checking
balance. thhis shoudl be checked like an accounting balance sheet - needs to
match cash_accounts in the working database and have correct math to show
how we got there and why.

resolved_tickets.json should be an audit log of how each ticket was run and
any human approvals needed and what happened.
resolved_board.html should be a page that has with a screenshot of the react
board for each resolved ticekt 101 102 103. real runs should be appended to
audit trail and harness.md needs to cover everything like tables tools mcp
agents routes dashboard and safety

**Follow-up prompt used:** all three are done, build the outputs

**Notes:**

- **Reset and starting money:** checking **$3,400.00**, no payments, all
  9 tables matching the original (audit entry 41). The session ended once
  mid-way. The servers were restarted with the database untouched, and
  nothing had run.
- **I played the approver** on the React board and ran 101 → 102 → 103.
  The approver name recorded on every approval is "TestChristopher", what
  I typed. Claude only reset and watched; a read-only script took the
  screenshots after each ticket closed.
- **What happened** (audit entries 42–62, all gpt-6-luna-global, no retries
  needed):
  - **101:** the Boss offered Tauhid in-stock M/L/XL tees at $28. The
    planned $840 invoice payment was **not** proposed: the Boss asked
    Accounting for numbers rather than to pay, and Accounting held back
    over the unknown reprint cost. I approved the decision. $0 moved.
  - **102:** rent request 1 ($2,400) went through Facilities → Accounting.
    I approved the payment and the decision. Checking $3,400 → $1,000;
    lease next due → 2026-10-02.
  - **103:** 8 M hoodies at $36.67 (36.78% off, the 40% floor). Option B
    was flagged ($264 reprint vs. $160, short $104), but one offer was made
    instead of two options. I approved the decision. $0 moved.
  - **Totals:** 14 agent runs, 62 model requests, 160,939 tokens, 48 tool
    calls, 11 delegations (1 refused: the Boss tried to delegate to
    itself).
- **Cash reconciles:** $3,400.00 − $2,400.00 = $1,000.00 = `cash_accounts`.
  The money out agrees in `payments`, the paid `payment_requests`, and the
  audit trail. Invoice 501 ($840) is still open, which is exactly the gap
  from the planned $160.
- **Outputs:**
  - `desk_tickets.html`: each ticket's **Actual** section has an
    expected-vs-actual table (matched / different / missed / extra), the
    hand-off chain with every tool call, and results. The **Cash** tab is
    an itemized ledger by step, with reconciliation, plan vs. actual, and
    what's still owed. Reflection is left empty for P10.
  - `resolved_tickets.json`: generated by a script from the audit trail
    and database: every step, tool call, refusal, approval, and the cash
    check.
  - `resolved_board.html`: per ticket, the board right after closing plus
    the review popup, embedded. The build checks each screenshot's balance
    against the ledger.
  - `harness.md`: added the system overview (§0), the work tables, the
    board/human tools, Dashboard (§7), the real run (§8), and known
    limitations (§9).
- All pages were checked for sideways overflow at 375–1280 px.
  `resolved_tickets.json` is valid JSON.
- **After the outputs** I asked about the $840, which I hadn't seen at
  all. Because no one proposed paying invoice 501, it showed up only as a
  line in 101's risks box. Two decisions, recorded here (no new prompt
  slot):
  - **Overdue ticker:** the board now has an amber strip under the header
    listing every overdue invoice, plus "Overdue bills, not yet proposed:
    $840" in the cash card. It's frontend only; the data was already in
    `/api/cash`. Checked at 375–1440 px and with reduced motion. (The P9
    screenshots in `resolved_board.html` were taken before it existed.)
  - **Justification:** 101's write-ups now frame not spending the $840 as
    a deliberate hold to keep cash available for reprints and emergencies.
    Paying it and the rent would have left $160 with the reprint cost
    unknown, so the hold kept a $1,000 cushion. This uses Accounting's and
    the Boss's own recorded reasoning, and still states the trade-off: the
    invoice stays overdue and the vendor stays blocked.
