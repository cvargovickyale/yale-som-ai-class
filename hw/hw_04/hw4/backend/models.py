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


class ChatResponse(BaseModel):
    """What /api/chat sends the website: the agent's reply plus the products
    it refers to. Product details are looked up from the database by
    main.py, never taken from the model's text."""

    reply: str
    products: list[ProductSummary] = []


# --------------------------------------------------------------------------
# Agent contract
# --------------------------------------------------------------------------


@dataclass
class AgentDeps:
    """Per-request context handed to the agent and its tools.

    Deliberately minimal: the agent gets the shopper's first name and a path
    to the database. Never emails, password hashes, or login tokens.
    """

    db_path: Path
    first_name: str | None = None


# --- What the agent's tools return (P6). Everything here comes straight
# --- from the database; the model only reads it.


class ProductMatch(BaseModel):
    """One search hit from find_products: enough to pick the right product."""

    product_id: str
    name: str
    garment_type: str
    price: float
    total_stock: int


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
        "in the order mentioned. Empty if no tool returned products.",
    )
