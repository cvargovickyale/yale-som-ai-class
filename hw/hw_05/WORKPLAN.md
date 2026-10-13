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

Only P1 and P11 are confirmed. P2–P10 are **inferred from the output files**
(order and names are guesses). Replace each row with the real title as we
reach it.

| P# | Problem (confirmed / *guess*) | What we do | Main files |
|---|---|---|---|
| P1 | Vibe coder prompts | Sets up the prompt-log convention. Kickoff is **not** logged. | `AI_prompts.md` |
| P2 | *Data / setup* | Move data into `hw5/data/`, make the working copy, reset script, venv, check `gpt-6-luna` through Portkey with one cheap call. **First log entry.** | `data/`, `requirements.txt`, `.env.example`, `.gitignore` |
| P3 | *MCP server* | Tools for each table; enforce the shop rules in code; smoke-test with no LLM. | `mcp_server/server.py`, `mcp_server/README.md`, `.mcp.json`, `output/mcp_smoke.json` |
| P4 | *Desk / ticket board* | Show the three open tickets. | `output/desk_tickets.html` |
| P5 | *Agents + prompts* | Five agents on `gpt-6-luna`, each with its own prompt and tool subset. | `backend/main.py`, `models.py`, `prompts/*.md` |
| P6 | *Delegation / full connectivity* | Any agent can hand work to any other; depth and loop limits. | `backend/main.py` |
| P7 | *React dashboard* | Watch agents work live; approval queue. | `frontend/`, `output/design.md` |
| P8 | *Human approval for payments* | Payment only after a human clicks approve; cash floor enforced by the tool. | `mcp_server/`, `main.py`, `frontend/` |
| P9 | *Full three-ticket run* | Reset → resolve 101, 102, 103 end to end. | `output/resolved_tickets.json`, `output/resolved_board.html` |
| P10 | *Audit trail + harness* | Append-only trail from real message history (HW4 v2 pattern); final harness. | `output/audit_trail.json`, `output/harness.md` |
| P11 | Push to public GitHub | Confirm repo name, publish, grader-test a fresh clone, write URL. | repo, `output/github_url.txt` |

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

1. **Working location.** Build in `hw/hw_05/hw5/`. The DB currently sits at
   `hw/hw_05/data/` → move it to `hw/hw_05/hw5/data/` in P2.
2. **Committing the DBs.** The workspace `.gitignore` already ignores
   `*.db-journal`. Add `-wal`/`-shm` too. Which state of
   `campus_customs_new.db` gets committed: freshly reset, or after the P9
   run? (Probably after the run, so graders see the result. Decide at P9.)
3. **Publish script.** Copy `hw/hw_04/publish_hw4.sh` but **invert the DB
   check**: require both `.db` files to be present, and still refuse `.env`,
   `.venv`, and `node_modules`. Confirm the public repo name with Christopher
   before creating it (suggestion: `campus-customs-hw5`).
4. **MCP transport.** The README order ("start MCP server" as its own step)
   suggests a separately running HTTP server (streamable HTTP) that the
   backend connects to, rather than stdio. Decide at P3.
5. **Model.** Only `gpt-6-luna`, for every agent, with no fallback. It's new
   (not on the HW3/HW4 roster), so verify with one call first. Make sure
   `gpt-5.6-luna` appears nowhere, because a different model in code or logs
   costs points.
6. **Approval mechanism.** Where do pending approvals live? There's no
   approvals table, and `payments.approved_by` is filled at pay time. The
   agent must not be able to call `pay` and approve its own payment.
   Decide at P8.
7. **Is a reprint order a cash payment now or a new invoice?** This decides
   whether ticket 103 fits under the $160. Decide when the ticket is worked.
8. **Visual style.** Gateway 2000 (workspace default) vs. whatever the
   assignment asks for. Decide at P7.

## Reuse from HW4 (frozen; copy patterns, don't edit)

- Contract-first outputs; code states facts, the model picks.
- Prompts re-read on every run; `.venv/bin/python -m uvicorn` in launch.json.
- Audit trail v2 (`capture_run_messages`, masking, atomic writes).
- `UsageLimits`, timeouts, round-trip/token cost log. Multi-agent is where
  these matter most.
- Playwright screenshots via scratchpad `playwright-core` + system Chrome.
- Publish script (inverted DB rule, see decision 3).
