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
    """Response schema for serialized wardrobe items."""
    id: int
    user_id: int
    category: str
    image_path: str
    brand: str | None = None
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
