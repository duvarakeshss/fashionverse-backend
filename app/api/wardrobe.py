from fastapi import APIRouter, Depends, File, UploadFile, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.services.storage_service import StorageBackend, get_storage_backend
from app.services.upload_service import UploadService
from app.schemas.wardrobe import WardrobeItemResponse, WardrobeCategory
from app.config import settings
from app.utils.exceptions import FileTooLargeError

router = APIRouter(tags=["wardrobe"])

from app.services.auth_service import get_current_user_id
from fastapi import HTTPException

@router.post(
    "/wardrobe/{user_id}/upload", 
    status_code=201, 
    response_model=WardrobeItemResponse,
    summary="Upload Wardrobe Item",
    description="Validates, processes, classifies, and uploads a new wardrobe item."
)
async def upload_wardrobe_item(
    user_id: int,
    request: Request,
    file: UploadFile = File(...),
    category: WardrobeCategory = Form(...),
    brand: str | None = Form(None),
    notes: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
    current_user_id: int = Depends(get_current_user_id)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's wardrobe")

    # Early check on Content-Length header
    content_length_header = request.headers.get("content-length")
    if content_length_header is not None:
        try:
            cl = int(content_length_header)
            if cl > settings.MAX_CONTENT_LENGTH:
                raise FileTooLargeError()
        except ValueError:
            pass

    # Read the full file bytes
    file_bytes = await file.read()
    
    service = UploadService(db, storage)
    item = await service.upload_wardrobe_item(
        user_id=user_id,
        category=category,
        file_bytes=file_bytes,
        original_filename=file.filename or "item.jpg",
        content_length=len(file_bytes),
        brand=brand,
        notes=notes
    )
    
    return item
