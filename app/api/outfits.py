from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.services.outfit_service import OutfitService
from app.schemas.outfit import DailyOutfitResponse

router = APIRouter(tags=["outfit"])

from app.services.auth_service import get_current_user_id
from fastapi import HTTPException

@router.get(
    "/outfits/{user_id}/daily",
    response_model=DailyOutfitResponse,
    summary="Get Daily Outfit Recommendation",
    description="Generates a daily outfit suggestion based on the user's wardrobe items."
)
async def get_daily_outfit(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access daily outfit recommendations for this user")
        
    service = OutfitService(db)
    return await service.get_daily_outfit(user_id)
