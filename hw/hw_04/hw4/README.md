# Campus Customs — HW4

A customer website for Campus Customs (Yale Bulldog Blue): browse products,
open a single-item page with live per-size stock, and chat with a shopping
assistant. React + Vite + TypeScript frontend, Python FastAPI backend.

> Status: P3. Website and product API work; the chat endpoint is a stub until
> the PydanticAI agent is added. Accounts arrive in P4.

## 1. Place the data pack (not in git)

Unzip `data.zip` so this folder looks like:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/          # product images referenced by the catalogue
```

## 2. Run the backend (terminal 1)

```bash
cd hw4
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your PORTKEY_API_KEY
cd backend
uvicorn main:app --reload
```

API runs at http://127.0.0.1:8000 (interactive docs at `/docs`).

## 3. Run the frontend (terminal 2)

```bash
cd hw4/frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite forwards `/api` and `/images` requests to
the backend on port 8000, so start the backend first.

## Project layout

```
hw4/
├── backend/
│   ├── main.py        # FastAPI app: products, images, chat
│   └── models.py      # Pydantic shapes shared with the frontend
├── frontend/          # Vite React TypeScript app
│   └── src/
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
| POST | `/api/chat` | `{ "message": "..." }` → `{ "reply": "...", "products": [] }` (stub) |
