# HW5 Workplan — Campus Customs Multi-Agent Operations

Working notes for Christopher and Claude. **Not a deliverable** — this file
sits outside `hw5/` on purpose, so the submitted tree matches the spec exactly.

Mode: Christopher leads **one problem at a time**. P2–P10 he types in his own
words (those are the logged ones); P1 and P11 are setup/submission. "P5"
means Problem 5. Finish, verify, log the prompt, then stop.

## The end state (P11): what we're building toward

**Submission:** push to a **public** GitHub repo so graders can clone it.
Christopher submits the URL on Canvas himself, and the same URL goes in
`output/github_url.txt`. No zip. Code lives in a folder named `hw5/`.

**Never in git:** the real `.env`. Ship `.env.example` with placeholders.
**Opposite of HW4:** both databases under `data/` **must** be committed
(`campus_customs.db` original + `campus_customs_new.db` working copy).

```
hw5/
├── AI_prompts.md              P1 convention → entries from P2 on
├── requirements.txt
├── .env.example               placeholders only
├── .gitignore                 .env, .venv, node_modules, *.db-journal/-wal/-shm (NOT *.db)
├── .mcp.json                  how an MCP client launches/reaches mcp_server/
├── README.md                  reset DB → start MCP → start FastAPI → start board → reset before full run
├── data/
│   ├── campus_customs.db      original, never written to
│   └── campus_customs_new.db  working copy; every tool writes here
├── mcp_server/
│   ├── server.py              all DB tools live here (no tools.py in backend)
│   └── README.md
├── frontend/                  React dashboard: ticket board, agent activity, approvals
├── backend/
│   ├── main.py                FastAPI + all five agents + delegation (no agent.py!)
│   ├── models.py              Pydantic contracts (tickets, decisions, approvals, audit)
│   └── prompts/
│       ├── boss.md
│       ├── inventory.md
│       ├── accounting.md
│       ├── facilities.md
│       └── customer_service.md
└── output/
    ├── harness.md
    ├── mcp_smoke.json         MCP server called directly, no LLM
    ├── desk_tickets.html      the open board before resolving
    ├── design.md
    ├── resolved_tickets.json  result of the full three-ticket run
    ├── resolved_board.html    the board after resolving
    ├── audit_trail.json
    └── github_url.txt
```

Note the tree differs from HW4: **no `agent.py` / `tools.py`**. Agents are
defined in `main.py`; tools are served by the MCP server. Don't add extra
backend files without deciding it together (HW4 decision 3, same answer
likely: keep it to the listed files).

## Problem map

Titles are confirmed (2026-10-12). Which output file belongs to which problem
is **inferred** from the titles (marked *likely*). Confirm against each
problem's real text when we reach it.

| P# | Problem | What we do | Main files |
|---|---|---|---|
| P1 | Vibe coder prompts | ✅ Convention set in `hw5/AI_prompts.md` (header only). Kickoff is **not** logged; entries start at P2. | `AI_prompts.md` ✅ |
| P2 | Study the Campus Customs database | ✅ Data at `hw5/data/`, working copy made (same SHA-1 as original), harness §1 Data, `hw5/.gitignore` (DBs committed; only -journal/-wal/-shm ignored). Venv and `.env.example` deferred to P3. | `data/`, `output/harness.md`, `AI_prompts.md` ✅ |
| P3 | Build the MCP server | ✅ FastMCP 4.1.0, 3 read-only tools (`check_stock`, `price_and_margin`, `get_ticket`), refuses original DB; not run. venv, requirements, .env.example added. harness §2 | `mcp_server/server.py`, `mcp_server/README.md`, `requirements.txt`, `.env.example` ✅ |
| P4 | Add the MCP server to the vibe coder and test each tool | ✅ `hw5/.mcp.json` (stdio). Claude Code called every tool over MCP from this session: 7/7 match SQL, 4/4 bad inputs error, DB unchanged. Rerun: `hw/hw_05/mcp_smoke_test.py`. | `.mcp.json`, `output/mcp_smoke.json` ✅ |
| P5 | Build the agent team and grow the MCP tools | ✅ 5 PydanticAI agents (Responses API, gpt-6-luna fixed), prompts from Christopher's quiz answers, `models.py` shapes, `delegate` with depth 4 / no-revisit / same-ticket / shared budget / timeouts. MCP 3 → 12 tools; rules in code. Ticket 102 live test on a throwaway copy: ok, 156 s, ~43k tokens. Margin floor 40% (default, his to change). **Part 2:** per-agent audit appends (tested, no tokens), harness §4 Safety + §5 Audit, `hw5/README.md`. | `backend/main.py`, `models.py`, `prompts/*.md`, `mcp_server/server.py`, harness §2–3 ✅ |
| P6 | Plan the three tickets | ✅ `output/desk_tickets.html`: tabs 101/102/103 (expected flow from Christopher's steps + empty Actual), empty Cash + Reflection. Margin floor math corrected (36.8% max off). Resolved: routing line in boss.md (rent via Facilities, check pending first); landlord ack draft yes; option B flagged (Accounting + Boss risks). | `output/desk_tickets.html` ✅ |
| P7 | Backend routes | FastAPI endpoints: tickets, run/resolve, agent activity, approvals (approve/reject), reset. | `backend/main.py`, `models.py` |
| P8 | Agent dashboard | React board: tickets, live agent activity, approval queue. | `frontend/`, *likely* `output/design.md` |
| P9 | Resolve the tickets | Reset → full three-ticket run with human approvals. | `output/resolved_tickets.json`, `output/resolved_board.html`, `output/audit_trail.json` |
| P10 | Reflection | **Christopher's voice.** Claude prepares structure only. | *likely* `output/harness.md` (or wherever the problem says) |
| P11 | Push to public GitHub | Confirm repo name, publish, grader-test a fresh clone, write the URL. | repo, `output/github_url.txt`, `README.md` final |

Open mapping questions: where `harness.md` gets written (HW4 built it up
across problems, then finished it in P12; here it may be P10 or built
throughout), and whether `audit_trail.json` starts in P5 when agents first
run. Default: start logging as soon as agents run.

## The data (original DB, read-only check 2026-10-12)

SHA-1 of the original `campus_customs.db`: `f447ca6a…109ea4c`. Re-check it before
submission to prove it was never written to.

- `desk.date_today` = **2026-08-31** (treat this as today; never the real clock)
- `cash_accounts`: one account, **checking $3,400.00**
- `payments`: **empty**
- `tickets` (all `open`):
  - **101** customer_order: Tauhid Zaman, 1× `CC-TEE-WHITE` **S**, linked invoice 501
  - **102** rent_notice: Elm City Properties, lease 1, "due in 2 days"
  - **103** price_override: Yale AI Club, 20× `CC-HOOD-NAVY` **M**, wants bulk discount
- `inventory` (10 rows): tee S = **0**, hoodie M = **8** (S 4, L 14, XL 6), mug = 0, cap OS = 40
- `pricing`: hoodie cost $22 / list $58; tee $8 / $28; cap $6 / $22; mug $3.50 / $14
- `vendors`: 1 Bulldog Print Co (apparel reprint, **5 days**), 2 Elm City Gifts
  (mugs, 3), 3 QuickShip CT (courier, 1)
- `invoices`: **501**, vendor 1, **$840**, due **2026-08-28**, `open` →
  **3 days overdue** → Bulldog Print Co is blocked from shipping
- `leases`: 1 Chapel Street shop, **$2,400/mo**, next due **2026-09-02**

The puzzle that ties the tickets together:

- Invoice + rent = $840 + $2,400 = **$3,240** → **$160** left.
- Both of the reprints the tickets need (tee S, hoodie M) come from the
  **same blocked vendor**.
- 12 hoodies short × $22 = **$264** > $160, if the reprint is paid in cash.
- Lead time: 5 days → a reprint ordered today arrives **2026-09-05** at the
  earliest.

## Decisions (resolve when we reach each problem)

1. ~~**Working location.**~~ **Done (P2):** building in `hw/hw_05/hw5/`; the DB was at
   `hw/hw_05/data/` → move it to `hw/hw_05/hw5/data/` in P2.
2. **Committing the DBs.** The workspace `.gitignore` already ignores
   `*.db-journal`. Add `-wal`/`-shm` too. Which state of
   `campus_customs_new.db` gets committed: freshly reset, or after the P9
   run? (Probably after the run, so graders see the result. Decide at P9.)
3. **Publish script.** Copy `hw/hw_04/publish_hw4.sh` but **invert the DB
   check**: require both `.db` files to be present, and still refuse `.env`,
   `.venv`, and `node_modules`. Confirm the public repo name with Christopher
   before creating it (suggestion: `campus-customs-hw5`).
4. ~~**MCP transport.**~~ **Done (P5):** one `server.py`: stdio for Claude Code (`.mcp.json`), `--http` on 8765 for the backend. The README order ("start MCP server" as its own step)
   suggests a separately running HTTP server (streamable HTTP) that the
   backend connects to, rather than stdio. Decide at P3.
5. ~~**Model.**~~ **Done (P5):** fixed in code, Responses API (Chat Completions rejects tools with reasoning on); responses report `gpt-6-luna-global`. Only `gpt-6-luna`, for every agent, with no fallback. It's new
   (not on the HW3/HW4 roster), so verify with one call first. Make sure
   `gpt-5.6-luna` appears nowhere, because a different model in code or logs
   costs points.
6. **Approval mechanism.** *(P5: agents create pending records in 5 work tables; approve/execute routes come in P7.)* Where do pending approvals live? There's no
   approvals table, and `payments.approved_by` is filled at pay time. The
   agent must not be able to call `pay` and approve its own payment.
   Decide at P8.
7. **Is a reprint order a cash payment now or a new invoice?** *(P5: `request_reprint` records est. cost, pending approval; decide what approval does in P6/P7.)* This decides
   whether ticket 103 fits under the $160. Decide when the ticket is worked.
8. **Visual style.** Gateway 2000 (workspace default) vs. whatever the
   assignment asks for. Decide at P7.

## Build requirements from the kickoff quiz (apply from P2 on)

**Enforce in code, not prompts.** Prompts explain the rules; the MCP tools and
backend enforce them.

- **Payments:** no agent gets a pay tool. Accounting can only *propose* a
  payment. The backend parks it as pending, the dashboard shows it, and only a
  human click makes the backend call MCP `pay` with `approved_by = <human>`.
- **Cash floor:** `pay` refuses if the balance would go below $0.
- **Vendor block:** a vendor with an open, overdue invoice (vs.
  `desk.date_today`) can't ship. Enforced in the tool.
- **Dates:** every "overdue" or "due in N days" check reads
  `desk.date_today`, never the system clock.
- **No real email:** Customer Service only *drafts*. There's no send tool.

**Delegation guardrails (full connectivity, but bounded):**

1. **Depth cap.** Delegation chains stop at a fixed depth (e.g. 3), and the
   result goes back to Boss.
2. **No ping-pong.** An agent can't delegate back to whoever asked it.
3. **No duplicate actions.** Tools check "already paid / already pending /
   already reserved" by invoice or ticket ID.
4. **Cost.** `UsageLimits` per run, plus a total budget for each ticket.
   Log round trips and tokens per agent. Measure before optimizing.
5. **Context.** Every hand-off carries the ticket ID and a short task
   description. The receiving agent re-reads facts from tools rather than
   trusting the note.
6. **Traceability.** The audit trail records the run ID, the parent run ID,
   from-agent → to-agent, and the model name each response reports
   (it must be `gpt-6-luna`).
7. **One decider.** Boss makes the final call on each ticket. Specialists
   recommend.

## P4 tool tests (done — kept as reference for rerunning after P5)

Claude Code loads `.mcp.json` only from the folder a session is opened in,
and only at session start. The kickoff session was opened at the workspace
root, so the P4 tool tests run in a new session opened on
`hw/hw_05/hw5/` (approve the `campus-customs` project server when asked).

`output/mcp_smoke.json` shape (one entry per tool):

```json
{
  "server": "campus-customs",
  "config": ".mcp.json (stdio: .venv/bin/python mcp_server/server.py)",
  "database": "data/campus_customs_new.db",
  "tools_listed": ["check_stock", "price_and_margin", "get_ticket"],
  "tests": [
    {
      "tool": "check_stock",
      "prompt": "<Christopher's prompt, verbatim>",
      "arguments": {},
      "output": {},
      "expected_from_sql": {},
      "matches_db": true
    }
  ]
}
```

Expected values (SQL on the working copy, 2026-10-12):

- `check_stock("CC-TEE-WHITE","S",1)` → on hand 0, shortfall 1. Other
  sizes: M 5, L 3, XL 2; total 10.
- `check_stock("CC-HOOD-NAVY","M",20)` → on hand 8, shortfall 12. Other
  sizes: S 4, L 14, XL 6; total 32.
- `price_and_margin("CC-HOOD-NAVY",20,0)` → cost 22, list 58, margin
  62.1%, revenue 1160, cost 440, profit 720, cash 3400.
- `get_ticket(101)` → invoice 501, Bulldog Print Co, $840, due 2026-08-28,
  3 days overdue, lead 5 days.
- `get_ticket(102)` → lease 1, Elm City Properties, $2,400, due 2026-09-02,
  2 days.
- `get_ticket(103)` → Yale AI Club, CC-HOOD-NAVY M ×20, nothing linked.
- Error check: an unknown SKU or ticket must return an error, not data.

Check the working copy is still identical to the original after P4 (all
tools are read-only): same SHA-1, `f447ca6a…`.

## Reuse from HW4 (frozen; copy patterns, don't edit)

- Contract-first outputs; code states facts, the model picks.
- Prompts re-read on every run; `.venv/bin/python -m uvicorn` in launch.json.
- Audit trail v2 (`capture_run_messages`, masking, atomic writes).
- `UsageLimits`, timeouts, round-trip/token cost log. Multi-agent is where
  these matter most.
- Playwright screenshots via scratchpad `playwright-core` + system Chrome.
- Publish script (inverted DB rule, see decision 3).
