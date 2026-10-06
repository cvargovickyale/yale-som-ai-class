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

Per-message lookups (P9): every read goes through ctx.deps.lookups, a record
created fresh for each chat message. A product's catalogue row (price
included) and its stock are read from the database at most once per
message; repeat requests in the same message are answered from the record.
The next message starts with an empty record, so nothing is ever reused
across messages, and every number in one reply comes from one snapshot.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
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


def _mark_read(ctx: RunContext[AgentDeps], queries: int) -> None:
    lookups = ctx.deps.lookups
    lookups.db_queries += queries
    lookups.read_at = lookups.read_at or datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_everything(ctx: RunContext[AgentDeps]) -> None:
    """Search needs every product: read catalogue + inventory once per message."""
    lookups = ctx.deps.lookups
    if lookups.complete:
        lookups.reused += 1
        return
    with closing(open_db(ctx)) as conn:
        catalogue = conn.execute("SELECT * FROM catalogue").fetchall()
        inventory = conn.execute("SELECT product_id, size, quantity FROM inventory").fetchall()
    _mark_read(ctx, 2)
    stock: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for r in inventory:
        stock[r["product_id"]].append((r["size"], r["quantity"]))
    for r in catalogue:
        # setdefault: anything already read earlier in this message wins, so
        # one reply never mixes two different readings of the same product.
        lookups.products.setdefault(r["product_id"], dict(r))
        lookups.stock.setdefault(r["product_id"], stock.get(r["product_id"], []))
    lookups.complete = True


def _products(ctx: RunContext[AgentDeps], product_ids: list[str]) -> dict[str, dict]:
    """Catalogue rows for these IDs: from this message's record, else one query."""
    lookups = ctx.deps.lookups
    missing = [pid for pid in product_ids if pid not in lookups.products]
    if missing and not lookups.complete:
        marks = ",".join("?" * len(missing))
        with closing(open_db(ctx)) as conn:
            rows = conn.execute(f"SELECT * FROM catalogue WHERE product_id IN ({marks})", missing).fetchall()
            inv = conn.execute(
                f"SELECT product_id, size, quantity FROM inventory WHERE product_id IN ({marks})", missing
            ).fetchall()
        _mark_read(ctx, 2)
        stock: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for r in inv:
            stock[r["product_id"]].append((r["size"], r["quantity"]))
        for r in rows:
            lookups.products.setdefault(r["product_id"], dict(r))
            lookups.stock.setdefault(r["product_id"], stock.get(r["product_id"], []))
    elif not missing:
        lookups.reused += 1
    unknown = [pid for pid in product_ids if pid not in lookups.products]
    if unknown:
        # Sent back to the model so it can correct itself instead of guessing.
        raise ModelRetry(f"Unknown product_id(s): {unknown}. Use find_products to get real IDs.")
    return {pid: lookups.products[pid] for pid in product_ids}


def find_products(
    ctx: RunContext[AgentDeps],
    query: str,
    max_price: float | None = None,
    in_stock_size: str | None = None,
) -> SearchResults:
    """Search the catalogue with the shopper's own words, optionally filtered.

    Use this first whenever the shopper names, describes, or browses products
    ("Yale Mom hoodie", "hoodies", "navy crewnecks under $60", "Saybrook
    gear"), to get real product_ids. Not for greetings or small talk: if no
    product is mentioned, don't call this. Each result's `price` and `total_stock`
    are live from the database: enough to answer "how much is X?" or "what
    do you have?" with no further call.

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
    _load_everything(ctx)
    lookups = ctx.deps.lookups
    rows = []
    for pid, r in lookups.products.items():
        stock = lookups.stock.get(pid, [])
        rows.append(
            {
                **r,
                "haystack": " ".join([r["name"], r["garment_type"], r["description"], r["colors"], r["search_tags"]]),
                "title": f"{r['name']} {r['garment_type']}",
                "total_stock": sum(q for _, q in stock),
                "size_stock": sum(q for s_, q in stock if s_ == size),
            }
        )

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

    Use this for a product's description or colors. Don't call it just for
    the price if find_products already returned that product in this
    message; that price is the same database value. Does NOT include stock;
    use check_stock for that.

    Args:
        product_id: An exact product_id from find_products.
    """
    row = _products(ctx, [product_id])[product_id]
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
    products = _products(ctx, ids)  # also loads their stock into this message's record
    checked_at = ctx.deps.lookups.read_at or datetime.now(timezone.utc).isoformat(timespec="seconds")

    by_product: dict[str, list[SizeStatus]] = {
        pid: [
            SizeStatus(size=size_, quantity=qty, status="in stock" if qty > 0 else "sold out")
            for size_, qty in ctx.deps.lookups.stock.get(pid, [])
        ]
        for pid in ids
    }

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
