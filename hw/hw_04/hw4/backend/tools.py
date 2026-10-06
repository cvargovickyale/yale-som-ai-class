"""Tools the Campus Customs agent can call.

Every fact the agent states about products (price, stock, sizes, colors,
description) must come from a tool here, which reads the database. The model
never answers those from memory (see prompts/prompt.md, "Honesty rules").

Three tools, one question each:
  find_products     shopper's words (+ optional price/size filters) -> matching products
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

from models import AgentDeps, ProductInfo, ProductMatch, SearchResults, SizeStatus, StockReport

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
MAX_SEARCH_RESULTS = 40  # enough for a whole category (27 hoodies) on the page
MAX_STOCK_PRODUCTS = 20

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


# Garment names written several ways collapse to one search word, applied to
# both the shopper's words and the product text (P7). Without this, "tees"
# missed most t-shirts and "quarter zip" also matched every full-zip.
PHRASES = [
    (r"\b(?:quarter|1/4|1 4|1-4)[\s-]*zip\w*", "quarterzip"),
    (r"\bfull[\s-]*zip\w*", "fullzip"),
    (r"\bt[\s-]?shirts?\b|\btees?\b", "tshirt"),
    (r"\bcrew[\s-]?necks?\b", "crewneck"),
    (r"\bmock[\s-]?necks?\b", "mockneck"),
    (r"\bsweat[\s-]?shirts?\b", "sweatshirt"),
    (r"\bhoodies?\b|\bhoody\b|\bhooded\b", "hoodie"),
    (r"\blong[\s-]?sleeves?\b", "longsleeve"),
    (r"\bshort[\s-]?sleeves?\b", "shortsleeve"),
]


def _words(text: str) -> set[str]:
    """Whole words, lowercased, garment phrases unified, simple plurals trimmed."""
    text = text.lower()
    for pattern, word in PHRASES:
        text = re.sub(pattern, f" {word} ", text)
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", text)}


# Garment words must appear in the product's name or garment type, not just
# its description — otherwise "crewneck" also finds t-shirts described as
# having a "crew-neck collar".
GARMENT_WORDS = {
    "hoodie", "tshirt", "crewneck", "mockneck", "quarterzip", "fullzip", "sweatshirt",
    "jacket", "fleece", "pullover", "bomber", "longsleeve", "shortsleeve", "shirt",
    "hat", "cap", "beanie", "scarf",
}


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


def find_products(
    ctx: RunContext[AgentDeps],
    query: str,
    max_price: float | None = None,
    in_stock_size: str | None = None,
) -> SearchResults:
    """Search the catalogue with the shopper's own words, optionally filtered.

    Use this first whenever the shopper names, describes, or browses products
    ("Yale Mom hoodie", "hoodies", "navy crewnecks under $60", "Saybrook
    gear"), to get real product_ids.

    Matching: a product matches if ALL the search words appear in its name,
    garment type, description, colors, or tags. If nothing matches all words,
    products matching SOME words are returned instead and `matched_on` says
    "some words"; treat those as loose matches. Garment names are understood
    in common forms (tee/t-shirt, hoodie/hooded, quarter-zip/1-4 zip).

    Args:
        query: The shopper's words, e.g. "hoodies" or "navy crewneck".
        max_price: Only products at or below this price.
        in_stock_size: Only products with this size in stock right now
            ("medium", "M", "xl" all work).
    """
    terms = _terms(query)
    size = normalize_size(in_stock_size) if in_stock_size else None
    with closing(open_db(ctx)) as conn:
        rows = conn.execute(
            """SELECT c.product_id, c.name, c.garment_type, c.price,
                      c.name || ' ' || c.garment_type || ' ' || c.description || ' ' ||
                          c.colors || ' ' || c.search_tags AS haystack,
                      c.name || ' ' || c.garment_type AS title,
                      COALESCE(SUM(i.quantity), 0) AS total_stock,
                      COALESCE(SUM(CASE WHEN i.size = ? THEN i.quantity END), 0) AS size_stock
               FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
               GROUP BY c.product_id""",
            (size,),
        ).fetchall()

    candidates = [
        r for r in rows
        if (max_price is None or r["price"] <= max_price) and (size is None or r["size_stock"] > 0)
    ]
    if not terms:  # e.g. "anything under $40" — filters only
        scored = [(0, 0, r) for r in candidates]
        matched_on = "filters only"
    else:
        scored = []
        for r in candidates:
            hay, title, name = _words(r["haystack"]), _words(r["title"]), _words(r["name"])
            hits = sum(1 for t in terms if t in (title if t in GARMENT_WORDS else hay))
            if hits:
                scored.append((hits, sum(1 for t in terms if t in name), r))
        all_words = [x for x in scored if x[0] == len(terms)]
        if all_words:
            scored, matched_on = all_words, "all words"
        else:
            matched_on = "some words" if scored else "nothing"
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]["name"]))

    return SearchResults(
        matched_on=matched_on,
        total_found=len(scored),
        products=[
            ProductMatch(
                product_id=r["product_id"],
                name=r["name"],
                garment_type=r["garment_type"],
                price=r["price"],
                total_stock=r["total_stock"],
            )
            for _, _, r in scored[:MAX_SEARCH_RESULTS]
        ],
    )


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
    to compare (max 20). If the shopper named a size, pass it as `size`
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
