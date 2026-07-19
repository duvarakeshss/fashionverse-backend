import hashlib
import random
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.wardrobe import WardrobeItem
from app.schemas.outfit import OutfitItemDetail, DailyOutfitResponse
from app.utils.exceptions import UserNotFoundError


# Required categories for a complete outfit
REQUIRED_CATEGORIES = ["top", "bottom", "shoes"]
OPTIONAL_CATEGORIES = ["accessories"]
ALL_CATEGORIES = REQUIRED_CATEGORIES + OPTIONAL_CATEGORIES


def _get_current_season() -> str:
    """Determine the current season based on the server date."""
    month = date.today().month
    if month in (3, 4, 5):
        return "Spring"
    elif month in (6, 7, 8):
        return "Summer"
    elif month in (9, 10, 11):
        return "Fall"
    else:
        return "Winter"


def _date_seed(user_id: int, today: date) -> int:
    """
    Generate a deterministic seed from the user ID and today's date.
    The same user gets the same outfit all day, but a different one tomorrow.
    """
    raw = f"{user_id}:{today.isoformat()}"
    return int(hashlib.sha256(raw.encode()).hexdigest(), 16)


def _pick_one(items: list, seed: int):
    """Deterministically pick one item from a list using a seeded random."""
    if not items:
        return None
    rng = random.Random(seed)
    return rng.choice(items)


class OutfitService:
    """Service that generates daily outfit recommendations from the user's wardrobe."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_daily_outfit(self, user_id: int) -> DailyOutfitResponse:
        """
        Build a daily outfit for the given user.
        
        Picks one item per category (top, bottom, shoes, accessories) using a
        date-seeded random selection so the outfit stays consistent throughout
        the day but refreshes the next day.
        """
        # Verify the user exists
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError()

        # Fetch all wardrobe items for this user
        result = await self.db.execute(
            select(WardrobeItem).where(WardrobeItem.user_id == user_id)
        )
        all_items = result.scalars().all()

        # Group items by category
        items_by_category: dict[str, list[WardrobeItem]] = {}
        for item in all_items:
            cat = item.category.lower()
            items_by_category.setdefault(cat, []).append(item)

        # Build the outfit with date-seeded selection
        today = date.today()
        season = _get_current_season()
        base_seed = _date_seed(user_id, today)

        picks: dict[str, WardrobeItem | None] = {}
        missing: list[str] = []

        for i, category in enumerate(ALL_CATEGORIES):
            category_items = items_by_category.get(category, [])
            # Use a slightly different seed per category so picks are independent
            picked = _pick_one(category_items, base_seed + i)
            picks[category] = picked
            if picked is None and category in REQUIRED_CATEGORIES:
                missing.append(category)

        # Convert DB models to response schemas
        def to_detail(item: WardrobeItem | None) -> OutfitItemDetail | None:
            if item is None:
                return None
            return OutfitItemDetail.model_validate(item)

        return DailyOutfitResponse(
            date=today.isoformat(),
            season=season,
            top=to_detail(picks.get("top")),
            bottom=to_detail(picks.get("bottom")),
            shoes=to_detail(picks.get("shoes")),
            accessories=to_detail(picks.get("accessories")),
            missing_categories=missing,
        )
