# Campus Customs — HW4

A customer website for Campus Customs (Yale Bulldog Blue): browse products,
open a single-item page with live per-size stock, and chat with a shopping
assistant. React + Vite + TypeScript frontend, Python FastAPI backend.

> Status: P7. Website, product API, accounts, and a PydanticAI chat agent
> (via Portkey) with database tools for product search, product info, and
> live stock by size. Asking the chat for a type of item ("show me hoodies")
> filters the Products page to the matching cards. Logged-in customers' chats
> are saved and reload when they return; the agent knows who's chatting and
> what page they're on ("do you have this in blue?").
> Products can be browsed by category tab, and each product opens as a popup
> over the page you clicked from.

Seed test account: `test@campuscustoms.yale.edu` / `password`.

Note: on first start the backend adds one nullable column
(`chat_messages.results_label`) to the local database if it's missing.

## 1. Place the data pack (not in git)

Unzip `data.zip` so this folder looks like:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/          # product images referenced by the catalogue
```

## 2. Run the backend (terminal 1)

Needs Python 3.11+ and a Portkey API key in `hw4/.env`. Without a key the
site still runs; only the chat reports that it's offline.

```bash
cd hw4
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your PORTKEY_API_KEY
cd backend
uvicorn main:app --reload --port 8000
```

API runs at http://127.0.0.1:8000 (interactive docs at `/docs`).

## 3. Run the frontend (terminal 2)

```bash
cd hw4/frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite forwards `/api` and `/images` requests to
the backend on port 8000, so start the backend first. (If the backend runs
on another port, start the frontend with
`HW4_BACKEND=http://127.0.0.1:<port> npm run dev`.)

## Project layout

```
hw4/
├── backend/
│   ├── main.py        # FastAPI app: products, images, accounts, chat route
│   ├── agent.py       # PydanticAI agent: Portkey model + prompt + tools
│   ├── tools.py       # database tools the agent can call (read-only)
│   ├── models.py      # Pydantic shapes: API contract + agent contract
│   └── prompts/
│       └── prompt.md  # agent voice, honesty and safety rules
├── frontend/          # Vite React TypeScript app
│   └── src/
│       ├── auth.tsx   # login state shared across pages
│       ├── pages/     # Home, Products, ProductDetail, About, Login, Signup
│       └── components/  # NavBar, ProductCard, ChatWidget
└── output/            # harness and assignment write-ups
```

## API

| Method | Path | Returns |
|---|---|---|
| GET | `/api/products` | All products: name, price, short description, image URL, total stock |
| GET | `/api/products/{product_id}` | One product with full description, colors, and stock per size |
| GET | `/images/{file}` | Product image (only `data/products/` is served, never the database) |
| POST | `/api/auth/signup` | Create account (first/last name, email, password + confirm) → login token + user |
| POST | `/api/auth/login` | Email + password → login token + user |
| GET | `/api/auth/me` | The logged-in user (needs `Authorization: Bearer <token>`) |
| POST | `/api/chat` | `{ "message": "...", "page_path": "/products/<id>" }` → `{ "reply": "...", "products": [ ... ], "results_label": "Hoodies" or null }` from the agent |
| GET | `/api/chat/history` | The logged-in customer's saved chat (login required) |
| POST | `/api/chat/bored` | The bulldog's idle action (wags tail, brings a ball) |

Passwords are hashed with PBKDF2-SHA256 (120,000 iterations), the same
format as the seed users. See `output/harness.md` §2 for details.

Chat search results open as `/products?q=<label>&ids=<id,id,...>`, so a
filtered view survives reloads and the Back button, and every card still
opens its single-item page.
