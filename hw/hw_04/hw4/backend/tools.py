"""Tools the Campus Customs agent can call.

Every fact the agent states about products (price, stock, sizes, colors,
description) must come from a tool here, which reads the database. The model
never answers those from memory (see prompts/prompt.md, "Honesty rules").

Three tools, one question each:
  find_products     shopper's words -> matching product IDs (+ price, total stock)
  get_product_info  product ID      -> description, colors, price
  check_stock       product IDs     -> live stock per size, with a clear status

All tools open the database read-only, so the agent can never change it.
The function docstrings below are what the model reads to decide when and
how to call each tool.
"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from pydantic_ai import ModelRetry, RunContext

from models import AgentDeps, ProductInfo, ProductMatch, SizeStatus, StockReport

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
SIZE_ALIASES = {
    "xs": "XS", "x-small": "XS", "xsmall": "XS", "extra small": "XS",
    "s": "S", "sm": "S", "small": "S",
    "m": "M", "med": "M", "medium": "M",
    "l": "L", "lg": "L", "large": "L",
    "xl": "XL", "x-large": "XL", "xlarge": "XL", "extra large": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "2x": "XXL",
    "double xl": "XXL", "extra extra large": "XXL",
}
MAX_SEARCH_RESULTS = 10
MAX_STOCK_PRODUCTS = 10

STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "of", "to", "do", "you",
    "have", "any", "some", "me", "show", "i", "want", "looking", "is", "are",
    "yale", "campus", "customs",  # on nearly every product, so they don't help rank
}


def open_db(ctx: RunContext[AgentDeps]) -> sqlite3.Connection:
    """Read-only connection for tools; the agent can never write to the database."""
    conn = sqlite3.connect(f"{ctx.deps.db_path.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_size(raw: str) -> str:
    """'medium' -> 'M', 'xl' -> 'XL'. Unknown sizes come back uppercased as-is."""
    key = raw.strip().lower()
    return SIZE_ALIASES.get(key, raw.strip().upper())


def _words(text: str) -> set[str]:
    """Whole words, lowercased, with simple plurals trimmed (hoodies -> hoodie)."""
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", text.lower())}


def _terms(query: str) -> list[str]:
    return sorted(_words(query) - STOPWORDS)


def _require_products(conn: sqlite3.Connection, product_ids: list[str]) -> dict[str, sqlite3.Row]:
    marks = ",".join("?" * len(product_ids))
    rows = conn.execute(f"SELECT * FROM catalogue WHERE product_id IN ({marks})", product_ids).fetchall()
    found = {r["product_id"]: r for r in rows}
    missing = [pid for pid in product_ids if pid not in found]
    if missing:
        # Sent back to the model so it can correct itself instead of guessing.
        raise ModelRetry(f"Unknown product_id(s): {missing}. Use find_products to get real IDs.")
    return found


def find_products(ctx: RunContext[AgentDeps], query: str) -> list[ProductMatch]:
    """Search the catalogue with the shopper's own words.

    Use this first whenever the shopper names or describes a product
    (e.g. "Yale Mom hoodie", "navy crewneck", "Saybrook t-shirt"), to get the
    real product_id before calling get_product_info or check_stock.

    Matches words against product name, garment type, description, colors,
    and tags. Returns up to 10 best matches with price and total units in
    stock across all sizes. An empty list means nothing matched; say so,
    don't guess.

    Args:
        query: The shopper's words describing what they want.
    """
    terms = _terms(query)
    if not terms:
        return []
    with closing(open_db(ctx)) as conn:
        rows = conn.execute(
            """SELECT c.product_id, c.name, c.garment_type, c.price,
                      lower(c.name || ' ' || c.garment_type || ' ' || c.description || ' ' ||
                            c.colors || ' ' || c.search_tags) AS haystack,
                      lower(c.name) AS lname,
                      COALESCE(SUM(i.quantity), 0) AS total_stock
               FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
               GROUP BY c.product_id"""
        ).fetchall()

    scored = []
    for r in rows:
        hay, name = _words(r["haystack"]), _words(r["lname"])
        hits = sum(1 for t in terms if t in hay)
        if hits == 0:
            continue
        name_hits = sum(1 for t in terms if t in name)
        scored.append((hits, name_hits, r))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]["name"]))
    return [
        ProductMatch(
            product_id=r["product_id"],
            name=r["name"],
            garment_type=r["garment_type"],
            price=r["price"],
            total_stock=r["total_stock"],
        )
        for _, _, r in scored[:MAX_SEARCH_RESULTS]
    ]


def get_product_info(ctx: RunContext[AgentDeps], product_id: str) -> ProductInfo:
    """Get the catalogue facts for one product: full description, colors, and price.

    Use this before describing a product or quoting its price. Does NOT include
    stock; use check_stock for that.

    Args:
        product_id: An exact product_id from find_products.
    """
    with closing(open_db(ctx)) as conn:
        row = _require_products(conn, [product_id])[product_id]
    return ProductInfo(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        price=row["price"],
    )


def check_stock(
    ctx: RunContext[AgentDeps], product_ids: list[str], size: str | None = None
) -> list[StockReport]:
    """Check live stock, size by size, for one or more products.

    Use this for ANY question about availability: "is it in stock?", "do you
    have a medium?", "which sizes are left?". Pass several product_ids at once
    to compare (max 10). If the shopper named a size, pass it as `size`
    ("medium", "M", "xl" are all fine) and read `requested_size_status`:
      - "in stock": quantity > 0 right now
      - "sold out": the product comes in that size, but none are left
      - "not offered": the product doesn't come in that size at all

    Args:
        product_ids: Exact product_ids from find_products.
        size: Optional size the shopper asked about.
    """
    ids = list(dict.fromkeys(product_ids))
    if not ids:
        raise ModelRetry("Pass at least one product_id.")
    if len(ids) > MAX_STOCK_PRODUCTS:
        raise ModelRetry(f"Check at most {MAX_STOCK_PRODUCTS} products at a time.")
    wanted = normalize_size(size) if size else None
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with closing(open_db(ctx)) as conn:
        products = _require_products(conn, ids)
        marks = ",".join("?" * len(ids))
        stock_rows = conn.execute(
            f"SELECT product_id, size, quantity FROM inventory WHERE product_id IN ({marks})", ids
        ).fetchall()

    by_product: dict[str, list[SizeStatus]] = {pid: [] for pid in ids}
    for s in stock_rows:
        by_product[s["product_id"]].append(
            SizeStatus(size=s["size"], quantity=s["quantity"], status="in stock" if s["quantity"] > 0 else "sold out")
        )

    reports = []
    for pid in ids:
        sizes = sorted(by_product[pid], key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else 99)
        status_by_size = {s.size: s.status for s in sizes}
        reports.append(
            StockReport(
                product_id=pid,
                name=products[pid]["name"],
                checked_at=checked_at,
                requested_size=wanted,
                requested_size_status=(status_by_size.get(wanted, "not offered") if wanted else None),
                sizes=sizes,
                in_stock_sizes=[s.size for s in sizes if s.status == "in stock"],
                sold_out_sizes=[s.size for s in sizes if s.status == "sold out"],
            )
        )
    return reports


# Functions the agent may call (registered in agent.py).
TOOLS = [find_products, get_product_info, check_stock]
