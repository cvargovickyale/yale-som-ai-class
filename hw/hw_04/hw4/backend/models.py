"""Pydantic shapes shared by the API and the agent.

API shapes are the contract between backend and frontend;
`frontend/src/types.ts` mirrors them field for field. Agent shapes
(`AgentDeps`, `AgentReply`) are the contract between `main.py` and the
PydanticAI agent.
"""

from __future__ import annotations

from dataclasses import dataclass
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

    kind: Literal["home", "catalogue", "search_results", "product", "about", "login", "signup", "other"]
    product: ProductRef | None = None  # kind == "product"
    results_label: str | None = None  # kind == "search_results"
    result_products: list[ProductRef] = []  # kind == "search_results" (validated IDs only)


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
