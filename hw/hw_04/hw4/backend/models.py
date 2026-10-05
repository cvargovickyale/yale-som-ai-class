"""Pydantic shapes shared by the API and (from P5) the agent.

These are the contract between backend and frontend; `frontend/src/types.ts`
mirrors them field for field.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


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


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """Chat reply plus the products it refers to (empty until P7)."""

    reply: str
    products: list[ProductSummary] = []
