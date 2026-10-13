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
