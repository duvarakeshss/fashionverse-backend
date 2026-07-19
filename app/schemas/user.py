from pydantic import BaseModel

class ProfileImageUploadResponse(BaseModel):
    """Response schema for profile image uploads."""
    success: bool
    message: str
    image_url: str
    filename: str
