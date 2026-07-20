"""
Outfits Recommendation API Router.
Provides endpoints for retrieving daily outfit recommendations.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.schemas.outfit import DailyOutfitResponse, OutfitItemDetail
from app.services.auth_service import get_current_user_id
from app.services.outfit_service import OutfitService
from app.services.storage_service import StorageBackend, get_storage_backend

router = APIRouter(tags=["outfit"])


@router.get(
    "/outfits/{user_id}/daily",
    response_model=DailyOutfitResponse,
    summary="Get Daily Outfit Recommendation",
    description="Generates a daily outfit suggestion based on the user's wardrobe items."
)
async def get_daily_outfit(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
    current_user_id: int = Depends(get_current_user_id)
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access daily outfit recommendations for this user"
        )

    service = OutfitService(db)
    outfit = await service.get_daily_outfit(user_id)

    # Resolve public image URLs for each outfit piece
    def resolve(detail: OutfitItemDetail | None) -> OutfitItemDetail | None:
        if detail is None:
            return None
        detail.image_url = storage.get_url(detail.image_path)
        return detail

    outfit.top = resolve(outfit.top)
    outfit.bottom = resolve(outfit.bottom)
    outfit.shoes = resolve(outfit.shoes)
    outfit.accessories = resolve(outfit.accessories)

    return outfit
