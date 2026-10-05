"""Campus Customs API — HW4.

FastAPI app that serves the product catalogue, per-size stock, and product
images from the local data pack, plus a stub /api/chat endpoint that the
PydanticAI agent replaces in P5.

Data pack (not in git) must sit at hw4/data/:
    data/campus_customs.db
    data/products/*.jpg

Run from backend/:  uvicorn main:app --reload
API docs:           http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import json
from contextlib import closing
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from models import ChatRequest, ChatResponse, ProductDetail, ProductSummary, SizeStock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "campus_customs.db"
IMAGES_DIR = DATA_DIR / "products"

if not DB_PATH.exists() or not IMAGES_DIR.is_dir():
    raise RuntimeError(
        f"Data pack not found. Expected {DB_PATH} and {IMAGES_DIR}/ — "
        "unzip data.zip into hw4/data/ (see README.md)."
    )

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
SHORT_DESCRIPTION_CHARS = 90

app = FastAPI(title="Campus Customs API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Only the products/ folder is public — mounting data/ would expose the .db file.
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


def get_connection() -> sqlite3.Connection:
    """Read-only connection; catalogue and stock are never written by the site."""
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def short_description(text: str) -> str:
    if len(text) <= SHORT_DESCRIPTION_CHARS:
        return text
    cut = text[:SHORT_DESCRIPTION_CHARS].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


def image_url(image_file_path: str) -> str:
    # catalogue stores "products/<file>.jpg"; /images serves data/products/
    return "/images/" + Path(image_file_path).name


def to_summary(row: sqlite3.Row) -> ProductSummary:
    return ProductSummary(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        price=row["price"],
        short_description=short_description(row["description"]),
        image_url=image_url(row["image_file_path"]),
        total_stock=row["total_stock"],
    )


PRODUCT_QUERY = """
    SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock
    FROM catalogue c
    LEFT JOIN inventory i ON i.product_id = c.product_id
"""


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/products", response_model=list[ProductSummary])
def list_products():
    with closing(get_connection()) as conn:
        rows = conn.execute(PRODUCT_QUERY + " GROUP BY c.product_id ORDER BY c.name").fetchall()
    return [to_summary(r) for r in rows]


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: str):
    with closing(get_connection()) as conn:
        row = conn.execute(
            PRODUCT_QUERY + " WHERE c.product_id = ? GROUP BY c.product_id", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    sizes = sorted(
        (SizeStock(size=s["size"], quantity=s["quantity"]) for s in stock),
        key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else len(SIZE_ORDER),
    )
    return ProductDetail(
        **to_summary(row).model_dump(),
        description=row["description"],
        colors=json.loads(row["colors"]),
        search_tags=json.loads(row["search_tags"]),
        sizes=sizes,
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    """Stub until the PydanticAI agent lands in P5 — proves the round trip works."""
    return ChatResponse(
        reply=(
            "Thanks for reaching out to Campus Customs! Our shopping assistant "
            f'isn\'t connected yet, but the backend got your message: "{body.message}"'
        ),
        products=[],
    )
