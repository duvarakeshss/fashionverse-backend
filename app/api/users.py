from fastapi import APIRouter, Depends, File, UploadFile, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.services.storage_service import StorageBackend, get_storage_backend
from app.services.upload_service import UploadService
from app.schemas.user import ProfileImageUploadResponse
from app.config import settings
from app.utils.exceptions import FileTooLargeError

router = APIRouter()

@router.post(
    "/users/{user_id}/profile-image", 
    status_code=201, 
    response_model=ProfileImageUploadResponse,
    summary="Upload Profile Image",
    description="Validates and uploads a profile image for the user, updating their record."
)
async def upload_profile_image(
    user_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend)
):
    # TODO: replace with auth dependency
    
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
    result = await service.upload_profile_image(
        user_id=user_id,
        file_bytes=file_bytes,
        original_filename=file.filename or "profile.jpg",
        content_length=len(file_bytes)
    )
    
    return result
