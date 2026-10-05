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
import hmac
import json
import logging
import os
import random
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
from models import (
    AgentDeps,
    AuthResponse,
    ChatRequest,
    ChatResponse,
    LoginRequest,
    ProductDetail,
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
# Chat — the website's chat panel POSTs {"message": ...} here
# --------------------------------------------------------------------------

MAX_CHAT_PRODUCTS = 8


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


CONTENT_FILTER_REPLY = (
    "Woof… I can't help with that one. I'm here for Campus Customs gear, sizing, "
    "and the shop. What can I help you find?"
)


def _is_content_filter(exc: ModelHTTPError) -> bool:
    body = exc.body if isinstance(exc.body, dict) else {}
    return body.get("code") == "content_filter" or "content_filter" in str(exc.body)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, user: UserOut | None = Depends(get_optional_user)):
    deps = AgentDeps(db_path=DB_PATH, first_name=user.first_name if user else None)
    try:
        out = await run_agent(body.message, deps)
    except AgentUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"The shopping assistant is offline: {exc}")
    except ModelHTTPError as exc:
        if not _is_content_filter(exc):
            log.exception("Agent run failed")
            raise HTTPException(status_code=502, detail="The shopping assistant hit a snag. Please try again.")
        # The AI provider's own safety filter blocked the message before the
        # model saw it (e.g. a jailbreak attempt). Answer politely in character.
        log.warning("Provider content filter blocked a chat message")
        return ChatResponse(reply=CONTENT_FILTER_REPLY, products=[])
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="The shopping assistant took too long. Please try again.")
    except Exception:
        log.exception("Agent run failed")
        raise HTTPException(status_code=502, detail="The shopping assistant hit a snag. Please try again.")
    return ChatResponse(reply=out.reply, products=lookup_products(out.product_ids))


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
