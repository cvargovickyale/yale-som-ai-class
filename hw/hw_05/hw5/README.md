# Campus Customs Multi-Agent Operations (HW5)

An agent team that runs the Campus Customs shop. Five PydanticAI agents
(Boss, Inventory, Accounting, Facilities, Customer Service) work the open
tickets on the shop's board. They get every fact through one MCP server, and
they can only *propose* payments, reprints, stock holds, and customer
messages. A human approves each of those.

```
React board (frontend/)  ──>  FastAPI backend (backend/main.py)  ──>  MCP server (mcp_server/server.py)  ──>  data/campus_customs_new.db
  watch agents, approve        5 agents on gpt-6-luna, delegation,      12 tools, shop rules enforced          working copy
                               audit trail                              in code
```

- **Model:** `gpt-6-luna` through Portkey for every agent, fixed in code.
- **Data:** `data/campus_customs.db` is the original and is never written.
  `data/campus_customs_new.db` is the working copy every tool uses.
- **Details:** `output/harness.md` (data, tools, agents, safety, audit) and
  `mcp_server/README.md` (the tools).

## 1. Setup (once)

From the `hw5/` folder:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # then put your PORTKEY_API_KEY in .env
```

## 2. Reset the database (clean run)

Copy the original over the working copy whenever you need a clean start.
This removes the team's pending records (holds, payment and reprint requests,
drafts, decisions). It does **not** touch `output/audit_trail.json`, which is
append-only.

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

Or, with the servers running: `POST /api/reset` with `{"confirm": true}`
(the board's reset button in P8).

**Reset before a full three-ticket run** (tickets 101, 102, 103), so the run
starts from the original shop state.

## 3. Start the MCP server

The backend reaches the tools over HTTP:

```bash
.venv/bin/python mcp_server/server.py --http      # http://127.0.0.1:8765/mcp
```

Claude Code uses the same server over stdio via `.mcp.json` (it starts the
server itself when a session is opened in `hw5/`).

## 4. Start the FastAPI backend

With the MCP server running, in a second terminal:

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

The API is at http://localhost:8000 (interactive docs at
http://localhost:8000/docs). Every route goes through the MCP server.

| Route | What it does |
|---|---|
| `GET /api/tickets` | All tickets, open or resolved, with the team's records for each |
| `POST /api/tickets/{id}/run` | Run the agent team on a ticket (one run at a time; max 6 per 10 minutes) |
| `GET /api/events?since=N` | Recent agent events and tool calls, to keep the board current |
| `GET /api/cash` | Checking balance and payments waiting for approval |
| `POST /api/payments/{id}/approve` | Human approval: executes the payment and lowers cash |
| `POST /api/payments/{id}/reject` | Human rejects a payment request |
| `POST /api/decisions/{id}/approve` | Human approves the Boss's decision; the ticket becomes resolved |
| `POST /api/reset` | Reset the working database to the original (`{"confirm": true}`) |

Full list: `output/harness.md`, section 6. Each agent appends its own entry
to `output/audit_trail.json` when it finishes, followed by a ticket summary;
approvals and resets are appended too.

One ticket can also be run from the command line:
`.venv/bin/python backend/main.py ticket 102`.

## 5. Start the React board

With the MCP server and backend running, in a third terminal:

```bash
cd frontend
npm install          # first time only
npm run dev          # opens http://localhost:5173 in your browser
```

The board calls the backend through Vite's `/api` proxy (default
`http://127.0.0.1:8000`; set `HW5_BACKEND` if yours is elsewhere).

1. Type your name in **Approving as** (it's recorded on every approval).
2. Pick a ticket and click **Start the team**. Watch the agents' feeds.
3. When the ticket says **needs you**, open **Review and approve**:
   approve or reject each payment (the balance counts down), then
   **Approve and close ticket**. It turns green and drops into **Done**.
4. **Reset** returns the desk to the original data for a fresh run.

Design decisions: `output/design.md`.

## What the agents can and can't do

| Agents can | Only a human can |
|---|---|
| Read tickets, stock, prices, cash, invoices, leases | Approve a payment (invoice or rent) |
| Propose a payment (Accounting) | Approve a vendor reprint order |
| Request a reprint (Inventory) | Approve a ticket's final decision |
| Hold stock for a ticket (Inventory) | Approve a message to a customer, landlord, or vendor (drafts are never sent) |
| Draft a reply to the ticket's requester (Customer Service) | |
| Record a decision for approval (Boss) | |

Rules enforced by the tools, not just the prompts:
- cash can't go below $0
- a vendor with an open unpaid invoice can't take a reprint order
- no duplicate payment, hold, or reprint requests
- a payment must be the ticket's own bill
- drafts only go to the ticket's requester and are never sent

Token spend is capped per ticket at 40 model requests, 80 tool calls, and
400,000 tokens, with time limits. Delegation goes at most 4 hand-offs deep,
and no agent can appear twice in a chain.

## Files

| Path | What it is |
|---|---|
| `mcp_server/server.py` | The MCP server: all 12 tools and the shop's rules |
| `backend/main.py` | The five agents, delegation, limits, audit trail |
| `backend/models.py` | Data shapes agents return and the audit records |
| `backend/prompts/*.md` | One prompt per agent |
| `output/harness.md` | How the system works: data, tools, agents, safety, audit |
| `output/mcp_smoke.json` | Each original tool called over MCP and checked against SQL (P4) |
| `output/audit_trail.json` | Append-only log of every agent run |
| `AI_prompts.md` | Prompts used per problem |
