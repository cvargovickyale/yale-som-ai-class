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

**Follow-up prompt used:** none.

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
