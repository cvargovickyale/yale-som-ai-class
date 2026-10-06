"""Campus Customs API — HW4.

FastAPI app that serves the product catalogue, per-size stock, and product
images from the local data pack; handles account signup/login; and exposes
the chat route, POST /api/chat, which hands the shopper's message to the
PydanticAI agent (agent.py) and returns its reply plus matching products.

Data pack (not in git) must sit at hw4/data/:
    data/campus_customs.db
    data/products/*.jpg

Run from backend/:  uvicorn main:app --reload
API docs:           http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import time
import hmac
import json
import logging
import os
import random
import re
import secrets
import sqlite3
from collections import defaultdict, deque
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import ModelHTTPError

from agent import AgentUnavailable, run_agent
from tools import clean_description
from models import (
    AgentDeps,
    AuthResponse,
    ChatHistoryMessage,
    ChatRequest,
    ChatResponse,
    LoginRequest,
    PageView,
    ProductDetail,
    ProductRef,
    ProductSummary,
    SignupRequest,
    SizeStock,
    UserOut,
)

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

log = logging.getLogger("campus_customs")
log.setLevel(logging.INFO)
if not log.handlers:  # print our own INFO lines next to uvicorn's request log
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     [campus_customs] %(message)s"))
    log.addHandler(_handler)
    log.propagate = False

app = FastAPI(title="Campus Customs API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    """Return field + message only. FastAPI's default echoes the request body,
    which would send passwords back in the error response."""
    errors = [
        {"field": ".".join(str(part) for part in e["loc"][1:]) or "body",
         "msg": e["msg"].removeprefix("Value error, ")}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


# Only the products/ folder is public — mounting data/ would expose the .db file.
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


def get_connection() -> sqlite3.Connection:
    """Read-only connection for catalogue, stock, and user lookups."""
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_write_connection() -> sqlite3.Connection:
    """Read-write connection — used only to insert new accounts."""
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=rw", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------------------------------
# Products
# --------------------------------------------------------------------------


def short_description(text: str) -> str:
    if len(text) <= SHORT_DESCRIPTION_CHARS:
        return text
    cut = text[:SHORT_DESCRIPTION_CHARS].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


def image_url(image_file_path: str) -> str:
    # catalogue stores "products/<file>.jpg"; /images serves data/products/
    return "/images/" + Path(image_file_path).name


# The catalogue has 22 inconsistent garment_type labels (P2). Shoppers see 6
# clean categories instead. Checked in this order, first match wins; this
# covers all 102 products (verified in P9).
CATEGORY_RULES = [
    ("hood", "Hoodies"),
    ("t-shirt", "T-Shirts"),
    ("quarter-zip", "Quarter-Zips"),
    ("jacket", "Jackets"),
    ("long-sleeve", "Long Sleeves"),
    ("crew", "Crewnecks"),
    ("mockneck", "Crewnecks"),
]
CATEGORIES = ["Hoodies", "Crewnecks", "T-Shirts", "Quarter-Zips", "Jackets", "Long Sleeves", "Other"]


def category_for(garment_type: str) -> str:
    gt = garment_type.lower()
    return next((name for key, name in CATEGORY_RULES if key in gt), "Other")


def category_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def to_summary(row: sqlite3.Row) -> ProductSummary:
    return ProductSummary(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        price=row["price"],
        short_description=short_description(clean_description(row["description"])),
        image_url=image_url(row["image_file_path"]),
        total_stock=row["total_stock"],
        category=category_for(row["garment_type"]),
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
        description=clean_description(row["description"]),
        colors=json.loads(row["colors"]),
        search_tags=json.loads(row["search_tags"]),
        sizes=sizes,
    )


# --------------------------------------------------------------------------
# Accounts — passwords use the same format as the seed database:
#   pbkdf2_sha256$<salt>$<hex digest>, PBKDF2-HMAC-SHA256, 120,000 iterations,
#   salt used as its UTF-8 text. (Iteration count confirmed in P4 by
#   reproducing the seed test user's stored hash.)
# --------------------------------------------------------------------------

HASH_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 120_000

JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_urlsafe(32)  # random → logins reset on restart
JWT_ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(hours=24)

bearer = HTTPBearer(auto_error=False)


def _pbkdf2(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)  # 16 hex chars, like the seed users
    return f"{HASH_ALGORITHM}${salt}${_pbkdf2(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algorithm != HASH_ALGORITHM:
        return False
    return hmac.compare_digest(_pbkdf2(password, salt), digest)


# Checked when an email isn't found, so a wrong email takes as long as a wrong
# password and response time doesn't reveal which emails have accounts.
_DUMMY_HASH = hash_password(secrets.token_hex(16))


def create_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + TOKEN_LIFETIME}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def to_user(row: sqlite3.Row) -> UserOut:
    first, last = row["first_name"], row["last_name"]
    if not first:  # older rows may only have `name`
        first, _, last = (row["name"] or "").partition(" ")
    return UserOut(id=row["id"], first_name=first, last_name=last or "", email=row["email"])


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> UserOut | None:
    """The logged-in user if a valid token was sent, else None."""
    if creds is None:
        return None
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return to_user(row) if row else None


def get_current_user(user: UserOut | None = Depends(get_optional_user)) -> UserOut:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please log in")
    return user


@app.post("/api/auth/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest):
    email = body.email.strip().lower()
    with closing(get_write_connection()) as conn:
        if conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone():
            raise HTTPException(status_code=409, detail="An account with that email already exists")
        cur = conn.execute(
            "INSERT INTO users (name, first_name, last_name, email, password_hash) VALUES (?, ?, ?, ?, ?)",
            (
                f"{body.first_name} {body.last_name}",
                body.first_name,
                body.last_name,
                email,
                hash_password(body.password),
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    user = to_user(row)
    return AuthResponse(token=create_token(user.id), user=user)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(body: LoginRequest):
    email = body.email.strip().lower()
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
    stored = row["password_hash"] if row else _DUMMY_HASH
    if not verify_password(body.password, stored) or row is None:
        # Same message either way — don't reveal whether the email exists.
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    user = to_user(row)
    return AuthResponse(token=create_token(user.id), user=user)


@app.get("/api/auth/me", response_model=UserOut)
def me(user: UserOut = Depends(get_current_user)):
    return user


# --------------------------------------------------------------------------
# Chat — the website's chat panel POSTs {"message": ..., "page_path": ...} here
# --------------------------------------------------------------------------

MAX_CHAT_PRODUCTS = 40  # a whole category, e.g. all 27 hoodies


def lookup_products(product_ids: list[str]) -> list[ProductSummary]:
    """Turn the agent's product IDs into real catalogue data.

    Names, prices, and images come from the database, never from the model's
    text. IDs that don't exist (a hallucinated ID) are silently dropped.
    """
    ids = list(dict.fromkeys(product_ids))[:MAX_CHAT_PRODUCTS]  # dedupe, keep order
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    with closing(get_connection()) as conn:
        rows = conn.execute(
            PRODUCT_QUERY + f" WHERE c.product_id IN ({marks}) GROUP BY c.product_id", ids
        ).fetchall()
    by_id = {r["product_id"]: to_summary(r) for r in rows}
    return [by_id[i] for i in ids if i in by_id]


# --- Page context: the website sends the page path; we work out what's on
# --- screen and validate every ID against the database (never trust the URL).

STATIC_PAGES = {"/": "home", "/about": "about", "/login": "login", "/signup": "signup"}
MAX_LABEL_CHARS = 60


def product_refs(product_ids: list[str]) -> list[ProductRef]:
    return [ProductRef(product_id=p.product_id, name=p.name) for p in lookup_products(product_ids)]


def build_page_view(page_path: str | None) -> PageView | None:
    if not page_path:
        return None
    url = urlsplit(page_path)
    path = url.path.rstrip("/") or "/"
    if path in STATIC_PAGES:
        return PageView(kind=STATIC_PAGES[path])
    if path == "/products":
        query = parse_qs(url.query)
        ids = [i for i in query.get("ids", [""])[0].split(",") if i]
        slug = query.get("category", [""])[0]
        if not ids and slug:
            name = next((c for c in CATEGORIES if category_slug(c) == slug), None)
            if name:
                in_category = [p for p in list_products() if p.category == name]
                return PageView(
                    kind="category",
                    results_label=name,
                    result_products=[ProductRef(product_id=p.product_id, name=p.name) for p in in_category],
                )
        if not ids:
            return PageView(kind="catalogue")
        label = re.sub(r"[^\w $&'.,()-]", "", query.get("q", [""])[0])[:MAX_LABEL_CHARS].strip()
        return PageView(kind="search_results", results_label=label or None, result_products=product_refs(ids))
    if path.startswith("/products/"):
        refs = product_refs([path.removeprefix("/products/")])
        return PageView(kind="product", product=refs[0]) if refs else PageView(kind="other")
    return PageView(kind="other")


# --- Chat history: logged-in customers only, in the chat_messages table.

HISTORY_FOR_AGENT = 20  # most recent messages sent to the model as context
HISTORY_FOR_PAGE = 50  # most recent messages shown when the chat panel reloads


def ensure_chat_schema() -> None:
    """Add a nullable results_label column to chat_messages if it's missing.

    Additive only: existing rows and columns are untouched. It lets a reloaded
    search reply keep its "View 'Hoodies' on the page" link.
    """
    with closing(get_write_connection()) as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(chat_messages)")}
        if "results_label" not in cols:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN results_label TEXT")
            conn.commit()


ensure_chat_schema()


def _saved_ids(products_json: str | None) -> list[str]:
    """product_ids from a saved products_json (also reads the seed data's format)."""
    try:
        items = json.loads(products_json or "[]")
    except json.JSONDecodeError:
        return []
    return [i["product_id"] for i in items if isinstance(i, dict) and i.get("product_id")]


def load_history(user_id: int, limit: int) -> list[dict]:
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """SELECT role, content, products_json, results_label, created_at FROM (
                   SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?
               ) ORDER BY id""",
            (user_id, limit),
        ).fetchall()
    return [
        {
            "role": r["role"],
            "content": r["content"],
            "product_ids": _saved_ids(r["products_json"]),
            "results_label": r["results_label"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def save_exchange(user_id: int, message: str, response: ChatResponse) -> None:
    """Save the shopper's message and the reply together (one transaction)."""
    products_json = json.dumps([p.model_dump() for p in response.products])
    with closing(get_write_connection()) as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, message)
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json, results_label) "
            "VALUES (?, 'assistant', ?, ?, ?)",
            (user_id, response.reply, products_json, response.results_label),
        )
        conn.commit()


@app.get("/api/chat/history", response_model=list[ChatHistoryMessage])
def chat_history(user: UserOut = Depends(get_current_user)):
    """The logged-in customer's saved chat, oldest first. Product cards are
    re-read from the database, so prices and stock are current."""
    return [
        ChatHistoryMessage(
            role=m["role"],
            content=m["content"],
            products=lookup_products(m["product_ids"]),
            results_label=m["results_label"],
            created_at=m["created_at"],
        )
        for m in load_history(user.id, HISTORY_FOR_PAGE)
    ]


# --- Rate limiting (P9): every accepted chat message costs ~6,000-9,000 AI
# --- tokens, so cap how fast anyone can spend them. Checked BEFORE the agent
# --- runs, so a blocked message costs nothing.

# (max messages, window in seconds)
RATE_LIMITS = {
    "guest": [(5, 60), (30, 24 * 3600)],  # per IP address
    "customer": [(10, 60), (200, 24 * 3600)],  # per logged-in account
    "everyone": [(60, 60)],  # whole site: caps total spend even if many IPs/accounts are used
}


class RateLimiter:
    """Sliding-window message counts per key, kept in memory.

    Resets when the server restarts and isn't shared between server
    processes. Fine for one server; a multi-server deployment would keep
    these counts in a shared store such as Redis.
    """

    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def retry_after(self, key: str, limits: list[tuple[int, int]], now: float) -> tuple[float, int] | None:
        """(seconds until allowed, window hit) if `key` is over a limit, else None."""
        q = self.hits[key]
        longest = max(window for _, window in limits)
        while q and now - q[0] >= longest:
            q.popleft()
        for max_hits, window in limits:
            recent = [t for t in q if now - t < window]
            if len(recent) >= max_hits:
                return window - (now - recent[0]), window
        return None

    def record(self, key: str, now: float) -> None:
        self.hits[key].append(now)


chat_limiter = RateLimiter()


def enforce_chat_rate_limit(request: Request, user: UserOut | None) -> None:
    now = time.monotonic()
    # Behind a reverse proxy every guest would share the proxy's address; a
    # production deployment would read the proxy's X-Forwarded-For instead.
    own_key, own_limits = (
        (f"user:{user.id}", RATE_LIMITS["customer"]) if user
        else (f"ip:{request.client.host if request.client else 'unknown'}", RATE_LIMITS["guest"])
    )
    for key, limits, whose in ((own_key, own_limits, "you"), ("everyone", RATE_LIMITS["everyone"], "everyone")):
        blocked = chat_limiter.retry_after(key, limits, now)
        if blocked:
            wait, window = blocked
            seconds = max(1, math.ceil(wait))
            if window >= 3600:
                msg = "Woof! That's the chat limit for today. Browsing and product pages still work."
            elif whose == "everyone":
                msg = f"Woof! The shop is extra busy right now. Please try again in {seconds} seconds."
            else:
                msg = f"Woof! You're chatting faster than I can fetch. Try again in {seconds} seconds."
            log.warning("Chat rate limit hit (%s, %ss window)", key, window)
            raise HTTPException(status_code=429, detail=msg, headers={"Retry-After": str(seconds)})
    chat_limiter.record(own_key, now)
    chat_limiter.record("everyone", now)


CONTENT_FILTER_REPLY = (
    "Woof… I can't help with that one. I'm here for Campus Customs gear, sizing, "
    "and the shop. What can I help you find?"
)


def _is_content_filter(exc: ModelHTTPError) -> bool:
    body = exc.body if isinstance(exc.body, dict) else {}
    return body.get("code") == "content_filter" or "content_filter" in str(exc.body)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest, user: UserOut | None = Depends(get_optional_user)):
    enforce_chat_rate_limit(request, user)  # before any AI cost
    deps = AgentDeps(
        db_path=DB_PATH,
        user_id=user.id if user else None,
        first_name=user.first_name if user else None,
        last_name=user.last_name if user else None,
        email=user.email if user else None,
        page=build_page_view(body.page_path),
    )
    history = load_history(user.id, HISTORY_FOR_AGENT) if user else []  # guests: no memory
    try:
        out, usage = await run_agent(body.message, deps, history)
        # One line per message so cost and database use are visible while the app runs.
        log.info(
            "chat %s: %d model round trips, %d input / %d output tokens, %d DB queries (%d reused from this message)",
            f"user {user.id}" if user else "guest",
            usage.requests, usage.input_tokens, usage.output_tokens,
            deps.lookups.db_queries, deps.lookups.reused,
        )
        products = lookup_products(out.product_ids)
        # Only filter the page when there's something to show.
        label = out.results_label.strip() if out.results_label and products else None
        response = ChatResponse(reply=out.reply, products=products, results_label=label)
    except AgentUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"The shopping assistant is offline: {exc}")
    except ModelHTTPError as exc:
        if not _is_content_filter(exc):
            log.exception("Agent run failed")
            raise HTTPException(status_code=502, detail="The shopping assistant hit a snag. Please try again.")
        # The AI provider's own safety filter blocked the message before the
        # model saw it (e.g. a jailbreak attempt). Answer politely in character.
        log.warning("Provider content filter blocked a chat message")
        response = ChatResponse(reply=CONTENT_FILTER_REPLY, products=[])
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="The shopping assistant took too long. Please try again.")
    except Exception:
        log.exception("Agent run failed")
        raise HTTPException(status_code=502, detail="The shopping assistant hit a snag. Please try again.")

    if user:
        save_exchange(user.id, body.message, response)
    return response


# The bulldog's idle behavior from P4: no AI call, just a random dog action
# when the chat panel sits quiet.
BORED = [
    "*wags tail*",
    "*brings you a ball* 🎾",
    "*drops a slobbery tennis ball at your feet* 🎾 Woof?",
    "*yawns, then wags tail hopefully*",
    "*nudges the ball toward you* 🎾",
]


@app.post("/api/chat/bored", response_model=ChatResponse)
def chat_bored():
    """Called by the chat panel after the shopper goes quiet for a while."""
    return ChatResponse(reply=random.choice(BORED), products=[])
