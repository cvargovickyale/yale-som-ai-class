# mult_agent_hp — Harry Potter multi-agent class starter

Chat app with a **boss agent** and **book specialist workers** (one per Harry Potter novel). The React front end and FastAPI routes are already here. In class you build the PydanticAI backend (models, retrieval helpers, agents, prompts).

`harrypotter.db` is included at the project root (SQLite `books` table with per-novel text). Use chunk retrieval — do not dump whole novels into prompts.

## Quick start

### 1. Env

Copy `.env.example` → `.env`:

```
PORTKEY_API_KEY=your_key
MODEL_NAME=gpt-6-astra
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

## What you build

`backend/main.py` and `backend/requirements.txt` are provided. Fill in:

- `models.py`
- `retrieval.py` (chunk helpers for `harrypotter.db`)
- `agents/` (`config.py`, `boss.py`, `specialists.py`)
- `prompts/` (`boss.md`, `specialist.md`)

Use the course vibe coding prompt for details.

## Layout

```
mult_agent_hp/
  .env.example
  README.md
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
