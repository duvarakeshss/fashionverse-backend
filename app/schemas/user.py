from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

class ProfileImageUploadResponse(BaseModel):
    """Response schema for profile image uploads."""
    success: bool
    message: str
    image_url: str
    filename: str

class UserProfileUpdateRequest(BaseModel):
    """Schema for updating user profile details."""
    age: Optional[int] = Field(None, ge=0, le=120, description="Age of the user")
    gender: Optional[str] = Field(None, max_length=50, description="Gender of the user")
    height: Optional[float] = Field(None, ge=30, le=300, description="Height in cm")
    weight: Optional[float] = Field(None, ge=10, le=500, description="Weight in kg")
    location: Optional[str] = Field(None, max_length=100, description="City/Location of the user")
    climate_preference: Optional[str] = Field(None, max_length=100, description="Preferred climate")
    skin_tone: Optional[str] = Field(None, max_length=50, description="Skin tone classification")
    body_shape: Optional[str] = Field(None, max_length=50, description="Body shape classification")
    preferred_fit: Optional[str] = Field(None, description="Preferred clothing fit: Slim, Regular, or Oversized")
    preferred_style: Optional[List[str]] = Field(default_factory=list, description="Styles user prefers")
    favorite_colors: Optional[List[str]] = Field(default_factory=list, description="Colors user likes")
    colors_to_avoid: Optional[List[str]] = Field(default_factory=list, description="Colors user dislikes")

    @field_validator("preferred_fit")
    @classmethod
    def validate_preferred_fit(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = ["slim", "regular", "oversized"]
            if v.strip().lower() not in allowed:
                raise ValueError("preferred_fit must be one of: 'Slim', 'Regular', 'Oversized'")
            return v.strip().title()
        return v

class UserProfileResponse(BaseModel):
    """Response schema for user profile details."""
    id: int
    name: str
    email: str
    profile_image: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    location: Optional[str] = None
    climate_preference: Optional[str] = None
    skin_tone: Optional[str] = None
    body_shape: Optional[str] = None
    preferred_fit: Optional[str] = None
    preferred_style: Optional[List[str]] = None
    favorite_colors: Optional[List[str]] = None
    colors_to_avoid: Optional[List[str]] = None

    class Config:
        from_attributes = True
