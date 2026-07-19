import os
from io import BytesIO
from PIL import Image as PILImage
from app.config import settings

def validate_file_size(content_length: int | None, file_bytes: bytes | None = None) -> bool:
    """
    Validates if the file size is within limits.
    Returns True if valid, False otherwise.
    """
    limit = settings.MAX_CONTENT_LENGTH
    
    # 1. Check Content-Length header if present
    if content_length is not None and content_length > limit:
        return False
        
    # 2. Check actual bytes length if provided
    if file_bytes is not None and len(file_bytes) > limit:
        return False
        
    return True

def validate_image_and_get_ext(file_bytes: bytes) -> tuple[bool, str | None]:
    """
    Uses Pillow to verify if the file is a valid, decodable image of type JPEG, PNG, or WEBP.
    Returns a tuple: (is_valid, normalized_extension).
    """
    try:
        # Load image into Pillow
        img = PILImage.open(BytesIO(file_bytes))
        # load() forces Pillow to actually decode the image data, ensuring it is not corrupted
        img.load()
        
        fmt = img.format
        if not fmt:
            return False, None
            
        fmt = fmt.lower()
        if fmt not in {"jpeg", "png", "webp"}:
            return False, None
            
        # Map formats to normalized extensions
        ext_map = {
            "jpeg": ".jpg",
            "png": ".png",
            "webp": ".webp"
        }
        return True, ext_map.get(fmt, f".{fmt}")
    except Exception:
        return False, None

def is_allowed_extension(filename: str) -> bool:
    """Checks if the client-provided file extension is in the allowed list."""
    _, ext = os.path.splitext(filename.lower())
    return ext in settings.ALLOWED_EXTENSIONS
