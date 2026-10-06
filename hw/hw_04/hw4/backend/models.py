"""Pydantic shapes shared by the API and the agent.

API shapes are the contract between backend and frontend;
`frontend/src/types.ts` mirrors them field for field. Agent shapes
(`AgentDeps`, `AgentReply`) are the contract between `main.py` and the
PydanticAI agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Password = Annotated[str, Field(min_length=8, max_length=128)]


class SizeStock(BaseModel):
    size: str
    quantity: int


class ProductSummary(BaseModel):
    """What a product card on the Products page needs."""

    product_id: str
    name: str
    garment_type: str
    price: float
    short_description: str
    image_url: str
    total_stock: int
    category: str  # one of main.CATEGORIES, e.g. "Hoodies" (P9 category tabs)


class ProductDetail(ProductSummary):
    """Everything the single-item page shows."""

    description: str
    colors: list[str]
    search_tags: list[str]
    sizes: list[SizeStock]


class SignupRequest(BaseModel):
    first_name: Name
    last_name: Name
    email: EmailStr
    password: Password
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self) -> SignupRequest:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    """What the frontend may know about a user — never the password hash."""

    id: int
    first_name: str
    last_name: str
    email: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # The page the shopper is on when they send the message, e.g.
    # "/products/yale-mom-hoodie" or "/products?q=Hoodies&ids=a,b,c".
    # Untrusted input: main.py parses and validates it against the database.
    page_path: str | None = Field(default=None, max_length=3000)


class ChatResponse(BaseModel):
    """What /api/chat sends the website (the chat API contract).

    - `reply`: the agent's message for the chat panel.
    - `products`: product cards the reply is about, in the agent's order.
      Every field is looked up from the database by main.py, never taken
      from the model's text.
    - `results_label`: set when the shopper was browsing/searching (e.g.
      "Hoodies"). The website then filters the Products page to exactly
      `products` under that heading. Null means "answer only": the cards
      stay in the chat panel and the page doesn't change.
    """

    reply: str
    products: list[ProductSummary] = []
    results_label: str | None = None


class ChatHistoryMessage(BaseModel):
    """One saved message, as /api/chat/history returns it to the website."""

    role: Literal["user", "assistant"]
    content: str
    products: list[ProductSummary] = []
    results_label: str | None = None
    created_at: str


# --------------------------------------------------------------------------
# Agent contract
# --------------------------------------------------------------------------


class ProductRef(BaseModel):
    product_id: str
    name: str


class PageView(BaseModel):
    """What the shopper is looking at, built and validated by main.py from
    the page path the website sends (never trusted as-is)."""

    kind: Literal["home", "catalogue", "category", "search_results", "product", "about", "login", "signup", "other"]
    product: ProductRef | None = None  # kind == "product"
    results_label: str | None = None  # kind == "search_results" or "category" (the category name)
    result_products: list[ProductRef] = []  # kind == "search_results" or "category" (validated IDs only)


@dataclass
class MessageLookups:
    """What this message's tools have already read from the database.

    A fresh, empty one is created for every chat message (inside AgentDeps),
    so a value read here is reused only within the same message and never
    carries over to the next one. Guarantees each product's catalogue row
    (price included) and stock are read from the database at most once per
    message.
    """

    products: dict[str, dict] = field(default_factory=dict)  # product_id -> catalogue row
    stock: dict[str, list[tuple[str, int]]] = field(default_factory=dict)  # product_id -> [(size, qty)]
    complete: bool = False  # True once the whole catalogue + inventory has been read
    read_at: str | None = None  # when this message first read the database (UTC)
    db_queries: int = 0  # how many database queries this message's tools ran
    reused: int = 0  # tool requests answered from this record with no new query


@dataclass
class AgentDeps:
    """Per-message context handed to the agent and its tools ("deps").

    Built fresh by main.py for every message. The dynamic instructions in
    agent.py turn the customer and page fields into text for the model;
    tools read `db_path`. Never contains passwords, hashes, or login tokens.
    """

    db_path: Path
    # The logged-in customer (all None for a guest)
    user_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    # What's on the shopper's screen right now
    page: PageView | None = None
    # Per-message lookup record (new and empty for every message)
    lookups: MessageLookups = field(default_factory=MessageLookups)


# --- What the agent's tools return (P6). Everything here comes straight
# --- from the database; the model only reads it.


class ProductMatch(BaseModel):
    """One search hit from find_products: enough to pick the right product."""

    product_id: str
    name: str
    garment_type: str
    price: float
    total_stock: int


class SearchResults(BaseModel):
    """find_products: the matches plus how they were matched."""

    matched_on: Literal["all words", "some words", "filters only", "nothing"] = Field(
        description="'some words' means no product matched every word; treat results as loose."
    )
    total_found: int = Field(description="How many products matched (products is capped at 40).")
    products: list[ProductMatch]


class ProductInfo(BaseModel):
    """get_product_info: the catalogue facts for one product (no stock)."""

    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    price: float


class SizeStatus(BaseModel):
    size: str
    quantity: int
    status: Literal["in stock", "sold out"]


class StockReport(BaseModel):
    """check_stock: live stock for one product, read from the inventory table."""

    product_id: str
    name: str
    checked_at: str = Field(description="When the database was read (UTC). Stock can change after this.")
    requested_size: str | None = Field(
        default=None, description="The size asked about, normalized (e.g. 'medium' -> 'M'), if any."
    )
    requested_size_status: Literal["in stock", "sold out", "not offered"] | None = None
    sizes: list[SizeStatus] = Field(description="Every size this product comes in, XS to XXL.")
    in_stock_sizes: list[str]
    sold_out_sizes: list[str]


class AgentReply(BaseModel):
    """The agent's structured answer (PydanticAI `output_type`)."""

    reply: str = Field(description="The message shown to the shopper. Plain text, short.")
    product_ids: list[str] = Field(
        default_factory=list,
        description="Catalogue product_ids from tool results that the reply is about, "
        "in the order to display them. Empty if no tool returned products.",
    )
    results_label: str | None = Field(
        default=None,
        description="Short heading like 'Hoodies' or 'Saybrook gear in Large' when the shopper "
        "is browsing or searching and product_ids should be shown on the page as search "
        "results. Null when answering about one or two specific products.",
    )


# --------------------------------------------------------------------------
# Audit trail (P12): one AuditEntry per chat message, appended to
# output/audit_trail.json and never overwritten. Built by agent.py from the
# agent's actual message history, not from the model describing itself.
# --------------------------------------------------------------------------

StopReason = Literal[
    "final_result",  # the agent returned its structured answer (normal)
    "usage_limit",  # hit the per-message request / tool-call limit
    "timeout",  # took longer than the per-message time limit
    "content_filter",  # the AI provider's safety filter blocked the message
    "model_error",  # any other error from the model or a tool
    "agent_unavailable",  # no API key configured, so the agent never ran
    "rate_limited",  # refused before any AI call (too many messages)
]


class AuditStep(BaseModel):
    """One tool call inside the agent loop."""

    round_trip: int = Field(description="Which model request (1, 2, …) asked for this tool.")
    tool: str
    called_at: str = Field(description="UTC time the model's request for the tool arrived.")
    duration_ms: int | None = Field(default=None, description="Tool run time, from request to result.")
    args: dict = Field(description="Arguments, shortened: long lists show the first few + a count.")
    result: str = Field(description="Short human-readable summary of what the tool returned.")
    outcome: Literal["ok", "retry"] = Field(
        description="'retry' = the tool rejected the call (e.g. an unknown product ID) and asked the model to fix it."
    )


class AuditEntry(BaseModel):
    """One chat message's complete run, successful or not."""

    run_id: str = Field(description="Short unique ID for matching this entry to the server log.")
    started_at: str
    duration_ms: int
    who: str = Field(description="'guest' or 'user:<id>'. Never a name or email.")
    page: str = Field(description="What was on screen, e.g. 'product:yale-mom-hoodie'.")
    message: str = Field(description="The shopper's message, first 200 characters, sensitive details masked.")
    model: str
    steps: list[AuditStep] = Field(default_factory=list)
    stop_reason: StopReason
    finish_reason: str | None = Field(default=None, description="The provider's own reason on the last model response.")
    model_round_trips: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    db_queries: int = Field(default=0, description="Database queries the tools ran (see MessageLookups).")
    db_reused: int = Field(default=0, description="Tool requests answered from this message's lookup record.")
    reply: str = Field(default="", description="The reply shown, first 200 characters.")
    products_returned: int = 0
    results_label: str | None = None
    error: str | None = Field(default=None, description="Short error description when stop_reason isn't final_result.")
