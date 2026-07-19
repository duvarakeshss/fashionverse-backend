"""
User Profile API Router.
Provides endpoints for retrieving and updating user profile details and profile images.
"""
from fastapi import APIRouter, Depends, File, UploadFile, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.connection import get_db
from app.services.storage_service import StorageBackend, get_storage_backend
from app.services.upload_service import UploadService
from app.schemas.user import (
    ProfileImageUploadResponse,
    UserProfileUpdateRequest,
    UserProfileResponse
)
from app.config import settings
from app.models.user import User
from app.utils.exceptions import FileTooLargeError, UserNotFoundError
from app.services.auth_service import get_current_user_id

router = APIRouter(tags=["user"])

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
    storage: StorageBackend = Depends(get_storage_backend),
    current_user_id: int = Depends(get_current_user_id)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's profile")
    
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

@router.post(
    "/users/{user_id}/profile",
    response_model=UserProfileResponse,
    status_code=200,
    summary="Update User Profile",
    description="Updates the profile information of the user."
)
async def update_user_profile(
    user_id: int,
    req: UserProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's profile")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UserNotFoundError()

    # Update fields that are provided in the request
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user

@router.get(
    "/users/{user_id}/profile",
    response_model=UserProfileResponse,
    status_code=200,
    summary="Get User Profile",
    description="Retrieves the profile information of the user."
)
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's profile")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UserNotFoundError()
    return user
