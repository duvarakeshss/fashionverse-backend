from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.services.outfit_service import OutfitService
from app.schemas.outfit import DailyOutfitResponse

router = APIRouter()

@router.get(
    "/outfits/{user_id}/daily",
    response_model=DailyOutfitResponse,
    summary="Get Daily Outfit Recommendation",
    description="Generates a daily outfit suggestion based on the user's wardrobe items."
)
async def get_daily_outfit(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    service = OutfitService(db)
    return await service.get_daily_outfit(user_id)
