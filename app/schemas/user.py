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
    shopping_for: Optional[str] = Field(None, max_length=100, description="Who the user is shopping for")
    height: Optional[float] = Field(None, ge=30, le=300, description="Height of the user in cm")
    body_type: Optional[str] = Field(None, max_length=100, description="Body type/shape of the user")
    preferred_palettes: Optional[List[str]] = Field(default_factory=list, description="Preferred color palettes")
    weekly_occasions: Optional[List[str]] = Field(default_factory=list, description="Occasions dressed for weekly")
    climate: Optional[str] = Field(None, max_length=100, description="Climate preference of the user")
    fashion_goals: Optional[List[str]] = Field(default_factory=list, description="Fashion goals of the user")
    budget_range: Optional[str] = Field(None, max_length=100, description="Budget range preference")
    preferred_brands: Optional[List[str]] = Field(default_factory=list, description="Preferred brands")

class UserProfileResponse(BaseModel):
    """Response schema for user profile details."""
    id: int
    name: str
    email: str
    profile_image: Optional[str] = None
    shopping_for: Optional[str] = None
    height: Optional[float] = None
    body_type: Optional[str] = None
    preferred_palettes: Optional[List[str]] = None
    weekly_occasions: Optional[List[str]] = None
    climate: Optional[str] = None
    fashion_goals: Optional[List[str]] = None
    budget_range: Optional[str] = None
    preferred_brands: Optional[List[str]] = None

    class Config:
        from_attributes = True
