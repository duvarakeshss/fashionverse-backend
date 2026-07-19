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
        image_url = self.storage.get_url(saved_relative_path)
        return {
            "success": True,
            "message": "Profile image uploaded successfully",
            "image_url": image_url,
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

        # Generate thumbnail using temp files to ensure storage backend independence
        import anyio
        
        temp_dir = settings.UPLOAD_DIR / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_main_path = temp_dir / f"temp_{item_uuid}{true_ext}"
        temp_thumb_path = temp_dir / f"thumb_{item_uuid}{true_ext}"
        
        def write_temp():
            with open(temp_main_path, "wb") as f:
                f.write(file_bytes)
        await anyio.to_thread.run_sync(write_temp)
        
        try:
            # Generate thumbnail
            await generate_thumbnail(str(temp_main_path), str(temp_thumb_path))
            
            # Read thumbnail bytes
            def read_thumb():
                with open(temp_thumb_path, "rb") as f:
                    return f.read()
            thumbnail_bytes = await anyio.to_thread.run_sync(read_thumb)
            
            # Save thumbnail to storage backend
            thumbnail_relative_path = f"thumbnails/{user_id}/{item_uuid}{true_ext}"
            await self.storage.save(thumbnail_bytes, thumbnail_relative_path)
        finally:
            # Cleanup temp files
            def cleanup():
                if temp_main_path.exists():
                    temp_main_path.unlink()
                if temp_thumb_path.exists():
                    temp_thumb_path.unlink()
            await anyio.to_thread.run_sync(cleanup)

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
