"""
Wardrobe Schemas.
Pydantic schemas representing wardrobe category annotations, item responses, search, and AI queries.
"""
from datetime import datetime
from enum import Enum
from typing import Annotated
from pydantic import BaseModel, BeforeValidator

def normalize_category(v: str) -> str:
    if isinstance(v, str):
        v_lower = v.lower().strip()
        if v_lower in {"top", "bottom", "shoes", "accessories"}:
            return v_lower
    raise ValueError("category must be one of 'top', 'bottom', 'shoes', or 'accessories'")

# Annotated category type that validates case-insensitively and normalizes to lowercase
WardrobeCategory = Annotated[str, BeforeValidator(normalize_category)]

class WardrobeItemResponse(BaseModel):
    """Response schema for serialized wardrobe items. `image_url` is the fully resolved public URL."""
    id: int
    user_id: int
    category: str
    image_path: str
    image_url: str = ""   # Resolved public URL — populated by the API layer
    brand: str | None = None
    notes: str | None = None
    type: str | None = None
    gender: str | None = None
    color: str | None = None
    season: str | None = None
    usage: str | None = None
    description: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class WardrobeQueryRequest(BaseModel):
    """Request body for the AI outfit query endpoint."""
    query: str
    limit: int = 5


class WardrobeQueryItemResult(BaseModel):
    """A single matched wardrobe item returned in an AI query response, with a resolved public image URL."""
    id: int
    user_id: int
    category: str
    image_url: str          # Public Azure / local URL for the image
    brand: str | None = None
    notes: str | None = None
    type: str | None = None
    gender: str | None = None
    color: str | None = None
    season: str | None = None
    usage: str | None = None
    description: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class WardrobeQueryResponse(BaseModel):
    """Response body for the AI outfit query endpoint."""
    query: str
    recommendation: str
    matched_items: list[WardrobeQueryItemResult]
