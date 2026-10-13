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
