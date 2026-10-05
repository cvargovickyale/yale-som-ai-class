# HW4 Workplan — Campus Customs website + chatbot

Working notes for Christopher and Claude. **Not a deliverable** — this file
sits outside `hw4/` on purpose, so the submitted tree matches the spec exactly.

Mode: Christopher leads **one problem at a time** and types each one in his
own words. "P5" means Problem 5. Finish, verify, log the prompt, then stop.

## The end state (P13): what we're building toward

**Submission:** push to a **public** GitHub repo, then Christopher submits the
repo URL on Canvas himself. No zip. Code lives in a folder named `hw4/`.

**Never in git:** the real `.env`, `campus_customs.db`, product images
(`data/products/`). Use `hw4/.gitignore`, and include `.env.example` with
placeholders only.

```
hw4/
├── AI_prompts.md            P2 → P12 (one entry per problem)
├── requirements.txt         P3 (grows in P4, P5)
├── .env.example             P3 (placeholders only)
├── .gitignore               P3 (.env, data/, *.db, .venv, node_modules)
├── README.md                P3 draft → finalized in P13 (how to run after placing data/)
├── frontend/                P3 build → P4 login UI → P7 chat panel → P9 → P10 style
├── backend/
│   ├── main.py              P3 (catalogue API + images) → P4 auth → P7 /chat → P8 memory
│   ├── agent.py             P5 → P6 tools wired in → P7 → P8
│   ├── models.py            P5 (agent output contract) → P6 → P7
│   ├── tools.py             P6 (product info + stock) → P7 (search)
│   └── prompts/prompt.md    P5 (yalebulldogblue.com research) → refined later
└── output/
    ├── harness.md           working notes from P5 on → consolidated in P12
    ├── design.md            P10 (likely; maybe started in P3)
    ├── usability.md         P9 (likely)
    ├── app_check.html       P11
    ├── app_check_images/    P11 (screenshots linked from app_check.html)
    └── audit_trail.json     logging starts once the agent runs (P5/P6) → finalized P12

data/                        LOCAL ONLY, never committed
├── campus_customs.db
└── products/                102 images; paths match catalogue.image_file_path
```

The "agent" is four files under `backend/`: `prompts/prompt.md`, `agent.py`,
`tools.py`, `models.py`.

*Assumption:* the output-file → problem mapping marked "likely" is inferred
from problem names only. Confirm against each problem's real text when we
reach it.

## Problem map

| P# | Problem | What we do | Main files touched |
|---|---|---|---|
| P1 | Vibe coder prompts | Sets up the prompt-log convention. Kickoff background is **not** logged. | `AI_prompts.md` (convention only) |
| P2 | Analyze the database | Inspect `catalogue`, `inventory`, `users`, `chat_messages`: columns, row counts, sizes, zero-stock items, password-hash format, data quirks. **First prompt-log entry.** | `AI_prompts.md`; maybe notes for `harness.md` |
| P3 | Build the Campus Customs website | Scaffold Vite React TS + FastAPI. Backend serves the product list and images from SQLite. Frontend shows a browsable product grid. Set up venv, requirements, `.gitignore`, `.env.example`, README draft. | `frontend/`, `backend/main.py`, root config files |
| P4 | Create account and login | Signup and login endpoints plus UI. Must verify the DB's existing **PBKDF2** hashes, not bcrypt like Lecture 08. Session token. | `backend/main.py` (+ helper?), `frontend/` |
| P5 | PydanticAI agent background | System prompt informed by yalebulldogblue.com research, agent wiring via Portkey, structured output model. | `prompts/prompt.md`, `agent.py`, `models.py`, `harness.md` start |
| P6 | Tools: product info and stock | DB-backed tools so price and stock answers come from SQLite, never from the model's memory. | `tools.py`, `models.py`, `agent.py` |
| P7 | Chat search that updates the page | Agent returns matching `product_id`s; frontend filters or highlights the grid. Chat panel UI plus a `/chat` endpoint. | `tools.py`, `models.py`, `main.py`, `frontend/` |
| P8 | Customer memory | Per-user chat history (the DB already has a `chat_messages` table with a `products_json` column) fed back into the agent. | `main.py`, `agent.py`, `frontend/` |
| P9 | Usability improvements | Fix friction found by actually using the site. | `frontend/`, `output/usability.md` (likely) |
| P10 | Style the website | Visual design based on yalebulldogblue.com. ⚠ May conflict with the workspace Gateway 2000 default; the assignment wins, so decide with Christopher. | `frontend/`, `output/design.md` (likely) |
| P11 | Site testing (app check) | Drive the running site, take screenshots, write an HTML report. | `output/app_check.html`, `output/app_check_images/` |
| P12 | Audit trail, safety, finish harness | Audit trail built from real message history (HW3 pattern), safety rules and limits, consolidated harness doc. | `output/audit_trail.json`, `output/harness.md`, `agent.py` |
| P13 | Push to GitHub, submit URL | Create the public repo, push `hw4/`, verify a fresh clone has no secrets, DB, or images. Christopher submits on Canvas. | README final, repo |

## Decisions (resolve when we reach each problem)

1. ~~**Working location.**~~ **Done (P2):** building in `hw/hw_04/hw4/`, data
   pack at `hw/hw_04/hw4/data/` (gitignored). The backend reads it via
   `DATA_DIR` (default `hw4/data`), and README tells graders to drop `data/`
   into `hw4/`.
2. **Public-repo mechanics (P13).** The workspace repo is private, so it
   can't be the submission. Plan: create a new public repo under the
   `cvargovickyale` account (name TBD) whose root contains `hw4/`, populated
   from the files git tracks in `hw/hw_04/hw4/`. Creating a public repo is
   publishing, so **confirm with Christopher at that step.**
3. **Extra backend files.** Lecture 08 split out `auth.py` and `db.py`. The
   expected tree lists only `main.py`, `agent.py`, `models.py`, `tools.py`.
   Either keep auth/DB helpers inside `main.py` to match exactly, or accept
   small extra files. **Done (P4):** kept everything in `main.py` (sections:
   Products / Accounts / Chat), with API shapes in `models.py`. The tree
   matches exactly.
6. ~~**`.env` location.**~~ **Done (P5):** `agent.py` loads `hw4/.env` first,
   then parent folders as a fallback (Lecture 08 pattern), so the workspace
   `.env` key is used without copying it. Graders use `hw4/.env`.
4. **Models.** Default `gpt-5.6-luna`. The assignment allows 5.6/6 series and
   hints at "a smarter model for harder agent steps." Log any upgrade
   (e.g. `terra`/`sol` for search reasoning) in `AI_prompts.md`.
5. **Styling.** yalebulldogblue.com look vs. Gateway 2000. (Decide at P10,
   but P3 layout choices affect it.)

## Known facts from a first look at the data (P2 will confirm)

- Tables: `catalogue` (102), `inventory` (612 rows = product × size),
  `users` (3, not just 1 test user), `chat_messages` (already exists).
- `colors` and `search_tags` are JSON-encoded strings, not real columns.
- Password hashes look like `pbkdf2_sha256$<salt>$<hex>`. The iteration count
  isn't in the string, so we'll need to determine it.
- `image_file_path` is relative to `data/` (e.g. `products/x.jpg`).

## Reference projects

- `lectures/lecture_08/`: React/Vite + Python backend, SQLite, auth, chat
  history. Closest overall pattern.
- `hw/hw_03/`: same Campus Customs brand. Tool design, `harness.md` final-pass
  template, and audit trail built from `result.all_messages()`.
- `lectures/lecture_07/`: contract-first `/chat` response shape.

## Local test accounts (this file is private; never put these in `hw4/`)

| Who | Email | Password | Notes |
|---|---|---|---|
| Seed test user | test@campuscustoms.yale.edu | password | From the assignment |
| Woody Pride | woody@example.com | BringTheBall1975 | Created in P4 through the Create Account page |

The P4 database backup from before the first write is in the session
scratchpad only. To reset, re-unzip `data.zip`.
