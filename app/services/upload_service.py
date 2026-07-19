import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models.user import User
from app.models.wardrobe import WardrobeItem
from app.services.storage_service import StorageBackend
from app.services.image_processing import generate_thumbnail
from app.utils.file_utils import (
    validate_file_size, 
    validate_image_and_get_ext, 
    is_allowed_extension
)
from app.utils.exceptions import (
    EmptyFileError,
    UnsupportedFileTypeError,
    InvalidImageError,
    FileTooLargeError,
    UserNotFoundError
)

class UploadService:
    """Service layer coordinating file validation, storage, and database persistence."""

    def __init__(self, db: AsyncSession, storage: StorageBackend):
        self.db = db
        self.storage = storage

    async def _verify_user_exists(self, user_id: int) -> User:
        """Verifies if the user exists in the database. Returns User if found."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError()
        return user

    async def _validate_uploaded_file(
        self, 
        file_bytes: bytes, 
        original_filename: str, 
        content_length: int | None
    ) -> str:
        """
        Validates size, extension, and content of uploaded files.
        Returns the verified file extension.
        """
        # 1. Check if empty
        if not file_bytes or len(file_bytes) == 0:
            raise EmptyFileError()

        # 2. Validate file size
        if not validate_file_size(content_length, file_bytes):
            raise FileTooLargeError()

        # 3. Check client extension
        _, ext = os.path.splitext(original_filename.lower())
        if not ext or ext not in settings.ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(ext or "unknown")

        # 4. Perform deep Pillow validation of content and get true extension
        is_valid_img, true_ext = validate_image_and_get_ext(file_bytes)
        if not is_valid_img or not true_ext:
            raise InvalidImageError()

        return true_ext

    async def upload_profile_image(
        self, 
        user_id: int, 
        file_bytes: bytes, 
        original_filename: str, 
        content_length: int | None
    ) -> dict:
        """
        Processes and stores a user's profile image.
        Overwrites any existing profile image and deletes the old file from disk.
        """
        # Verify user
        user = await self._verify_user_exists(user_id)

        # Validate file
        true_ext = await self._validate_uploaded_file(file_bytes, original_filename, content_length)

        # Generate unique filename
        filename = f"{uuid.uuid4().hex}{true_ext}"
        destination_path = f"profiles/{user_id}/{filename}"

        # Delete old profile image if it exists
        if user.profile_image:
            await self.storage.delete(user.profile_image)

        # Save new image to storage
        saved_relative_path = await self.storage.save(file_bytes, destination_path)

        # Update database record
        user.profile_image = saved_relative_path
        await self.db.commit()

        # Return response format matching schema
        return {
            "success": True,
            "message": "Profile image uploaded successfully",
            "image_url": f"/uploads/{saved_relative_path}",
            "filename": filename
        }

    async def upload_wardrobe_item(
        self,
        user_id: int,
        category: str,
        file_bytes: bytes,
        original_filename: str,
        content_length: int | None,
        brand: str | None = None,
        notes: str | None = None
    ) -> WardrobeItem:
        """
        Processes, stores, and classifies a wardrobe item.
        Also generates a thumbnail for the item.
        """
        # Verify user
        await self._verify_user_exists(user_id)

        # Normalize category
        normalized_category = category.lower().strip()

        # Validate file
        true_ext = await self._validate_uploaded_file(file_bytes, original_filename, content_length)

        # Generate unique filename and path
        item_uuid = uuid.uuid4().hex
        filename = f"{item_uuid}{true_ext}"
        destination_path = f"wardrobe/{user_id}/{normalized_category}/{filename}"

        # Save main image to storage
        saved_relative_path = await self.storage.save(file_bytes, destination_path)

        # Generate thumbnail path and execute generation
        abs_main_path = str((settings.UPLOAD_DIR / saved_relative_path).resolve())
        thumbnail_filename = f"{item_uuid}{true_ext}"
        thumbnail_dest_path = str((settings.UPLOAD_DIR / "thumbnails" / str(user_id) / thumbnail_filename).resolve())
        
        # Generate thumbnail (Pillow resize)
        await generate_thumbnail(abs_main_path, thumbnail_dest_path)

        # Insert WardrobeItem into database
        item = WardrobeItem(
            user_id=user_id,
            category=normalized_category,
            image_path=saved_relative_path,
            brand=brand,
            notes=notes
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)

        return item
