# mult_agent_hp_tokenomics — Harry Potter multi-agent + token meter starter

Chat app with a **boss agent** and **book specialist workers** (one per Harry Potter novel). Starting point for Lecture 11 tokenomics: same multi-agent desk as Lecture 10, ready for a token usage meter.

`data/harrypotter.db` is included (SQLite `books` table with per-novel text). Use chunk retrieval — do not dump whole novels into prompts. Source PDFs are not in this repo.

## Quick start

### 1. Env

Copy `.env.example` → `.env`:

```
PORTKEY_API_KEY=your_key
MODEL_NAME=gpt-6-luna
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 — Vite proxies `/api` to port 8000.

## Layout

```
mult_agent_hp_tokenomics/
  .env.example
  README.md
  data/
    harrypotter.db
  backend/
    main.py
    requirements.txt
    models.py
    retrieval.py
    agents/
    prompts/
  frontend/
```

## Lecture 11 tokenomics (added on top of the starter)

- **Pricing helper** — `backend/agents/pricing.py`: OpenAI Standard short-context prices for `gpt-6-luna` and `gpt-6-astra`, `cost_usd()` (input is billed as uncached + cache read + cache write), and a `SpendTracker` that books spend per agent (`boss`, `book-1` … `book-7`).
- **Live spend events** — every model response emits a `spend` SSE event with per-agent and total tokens and dollars. `GET /api/pricing` returns the price table and its source.
- **Budget kill-switch** — `budget_usd` on `/api/chat` and `/api/chat/stream`. Once total spend reaches it, no new model call starts, and the job ends with an `error` event that still carries usage and any specialist reports. A call already in flight can push spend slightly past the cap.
- **Prompt caching** — each agent's stable instructions (rules, persona, and a chapter map pulled from the database) come first, then a `CachePoint` (`prompt_cache_breakpoint` on the Responses API), then the per-question evidence. OpenAI only caches prefixes of about 1,024+ tokens, which is why the chapter maps are there.
- **Dashboard** — the Dumbledore org-chart dashboard from Lecture 10 with thermometer meters (total, boss, each book), a model picker, a budget box, cost per trace row, and a usage line under the answer.

Character roster: Dumbledore (boss), Ron (1), Hermione (2), Lupin (3), Fred & George (4), Luna (5), Snape (6), Neville (7).

**Caching note:** OpenAI reports every input token that isn't read from cache as a cache write (1.25× the input price), whether or not it sits after the breakpoint. The breakpoint controls what can be *read back* later. On repeat calls the stable prefix comes back at 10% of the input price, which outweighs the surcharge after the first call per agent.
