from datetime import datetime
from pydantic import BaseModel


class OutfitItemDetail(BaseModel):
    """Schema for a single wardrobe item within an outfit."""
    id: int
    category: str
    image_path: str
    brand: str | None = None
    notes: str | None = None

    class Config:
        from_attributes = True


class DailyOutfitResponse(BaseModel):
    """Response schema for the daily outfit recommendation."""
    date: str
    season: str
    top: OutfitItemDetail | None = None
    bottom: OutfitItemDetail | None = None
    shoes: OutfitItemDetail | None = None
    accessories: OutfitItemDetail | None = None
    missing_categories: list[str] = []
